#!/usr/bin/env python3
"""
requirements.py — record the per-client requirement list (the WHAT for this
client), derived from an ADP request source: the request email (today) or, in
future, a Salesforce Case via MCP (PROCEDURE Phase 0).

The requirement list comes from the source. The taxonomy is only consulted
afterward, via `mapped_taxonomy_id`, to learn HOW/WHERE to collect each one.

The authoritative store is the ledger (each requirement traces to its source).
This script appends via `ledger.record_requirement` and mirrors to a convenience
cache (`.ada/requirements.jsonl`) for listing. Extraction itself (reading the
email/case and deciding what was requested) is the agent's judgment; this script
only records the result deterministically.

Usage:
  requirements.py add --ledger L [--reqs R] --req-id ID --text "..." \
      [--source-kind email|salesforce-case|manual] [--source-ref REF] \
      [--source-from FROM] [--source-date D] [--taxonomy-id TID] \
      [--kind collect|complete]
  requirements.py list --ledger L          # list requirements from the ledger
"""
import argparse

import _ada
import ledger as ledger_mod


def cmd_add(a):
    e = ledger_mod.record_requirement(
        a.ledger, a.req_id, a.text, a.source_kind, a.source_ref,
        a.source_from, a.source_date, a.taxonomy_id, a.kind,
        a.expected_doc_type, a.expected_period)
    rec = e["payload"]
    rec["ledger_seq"] = e["seq"]
    if a.reqs:
        _ada.append_jsonl(a.reqs, rec)
    print(f"added requirement {a.req_id} -> {a.taxonomy_id or '(ad-hoc)'}  "
          f"[{a.kind}]  via {a.source_kind}  (seq {e['seq']})")


def cmd_list(a):
    reqs = ledger_mod.requirements(a.ledger)
    if not reqs:
        print("(no requirements recorded)")
        return
    for r in reqs:
        tid = r.get("mapped_taxonomy_id") or "(ad-hoc)"
        print(f"{r['req_id']:<10} {r['kind']:<8} {tid:<24} "
              f"{r['requested_text']}  <- {r.get('source_kind', '?')}:"
              f"{r.get('source_from', '?')}")


def main():
    p = argparse.ArgumentParser(description="ADA per-client requirements")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("add"); s.set_defaults(fn=cmd_add)
    s.add_argument("--ledger", required=True)
    s.add_argument("--reqs", default="", help="convenience cache jsonl (optional)")
    s.add_argument("--req-id", required=True)
    s.add_argument("--text", required=True)
    s.add_argument("--source-kind", default="email",
                   choices=["email", "salesforce-case", "manual"])
    s.add_argument("--source-ref", default="")
    s.add_argument("--source-from", default="")
    s.add_argument("--source-date", default="")
    s.add_argument("--taxonomy-id", default="")
    s.add_argument("--kind", default="collect", choices=["collect", "complete"])
    s.add_argument("--expected-doc-type", default="",
                   help="canonical doc_type from the mapped taxonomy item")
    s.add_argument("--expected-period", default="",
                   help='period phrase from requested_text, e.g. "last quarter"')

    s = sub.add_parser("list"); s.set_defaults(fn=cmd_list)
    s.add_argument("--ledger", required=True)

    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
