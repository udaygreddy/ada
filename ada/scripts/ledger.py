#!/usr/bin/env python3
"""
ledger.py — append-only, hash-chained consent ledger for ADA.

This is a HARD control (PLAYBOOK §3, §6). The agent cannot stage a document into
the handoff package unless a matching, unrevoked approval token exists here whose
content_hash equals the file's current hash. Tampering with any prior entry
breaks the chain, which `verify` detects.

Each entry:
  { seq, prev_hash, timestamp, actor, action, target, payload, entry_hash }
  entry_hash = sha256( prev_hash + canonical(body) )   # body = entry minus entry_hash

Actions:
  init               genesis entry for a run
  authorize_source   gate 1 — operator authorized a source/connector
  approve_document   gate 2 — operator approved a file; mints an approval token
  revoke             revoke a previously minted token

Usage:
  ledger.py init      --ledger L --run-id R --client C --operator O --host H
  ledger.py authorize --ledger L --connector NAME --scope SCOPE
  ledger.py approve   --ledger L --path FILE --checklist-id ID [--note N]
  ledger.py revoke    --ledger L --token TOKEN [--note N]
  ledger.py tokens    --ledger L            # list valid approval tokens
  ledger.py verify    --ledger L            # check chain integrity
"""
import argparse
import os
import secrets
import sys

import _ada


def _entries(path):
    return _ada.read_jsonl(path)


def _last_hash(entries):
    return entries[-1]["entry_hash"] if entries else _ada.GENESIS_PREV


def _append(path, action, target, payload, actor="operator"):
    entries = _entries(path)
    body = {
        "seq": len(entries),
        "prev_hash": _last_hash(entries),
        "timestamp": _ada.now_iso(),
        "actor": actor,
        "action": action,
        "target": target,
        "payload": payload,
    }
    body["entry_hash"] = _ada.sha256_str(body["prev_hash"] + _ada.canonical(body))
    _ada.append_jsonl(path, body)
    return body


def cmd_init(a):
    if os.path.exists(a.ledger) and _entries(a.ledger):
        sys.exit(f"refuse: ledger already exists and is non-empty: {a.ledger}")
    e = _append(
        a.ledger, "init", a.run_id,
        {"run_id": a.run_id, "client": a.client, "operator": a.operator, "host": a.host},
    )
    print(f"initialized run {a.run_id} (seq 0, hash {e['entry_hash'][:19]}…)")


def cmd_authorize(a):
    e = _append(a.ledger, "authorize_source", a.connector,
                {"connector": a.connector, "scope": a.scope})
    print(f"authorized source '{a.connector}' scope='{a.scope}' (seq {e['seq']})")


def cmd_approve(a):
    if not os.path.isfile(a.path):
        sys.exit(f"no such file: {a.path}")
    content_hash = _ada.sha256_file(a.path)
    token = secrets.token_hex(8)
    e = _append(a.ledger, "approve_document", a.path, {
        "checklist_id": a.checklist_id,
        "content_hash": content_hash,
        "token": token,
        "source_ref": os.path.abspath(a.path),
        "note": a.note or "",
    })
    print(f"approved {a.path}")
    print(f"  checklist_id : {a.checklist_id}")
    print(f"  content_hash : {content_hash}")
    print(f"  token        : {token}   (seq {e['seq']})")


def cmd_revoke(a):
    e = _append(a.ledger, "revoke", a.token, {"token": a.token, "note": a.note or ""})
    print(f"revoked token {a.token} (seq {e['seq']})")


def valid_tokens(path):
    """Return {content_hash: approval_payload} for unrevoked approvals."""
    approvals = {}
    revoked = set()
    for e in _entries(path):
        if e["action"] == "approve_document":
            approvals[e["payload"]["token"]] = e["payload"]
        elif e["action"] == "revoke":
            revoked.add(e["payload"]["token"])
    out = {}
    for tok, p in approvals.items():
        if tok not in revoked:
            out[p["content_hash"]] = p
    return out


def cmd_tokens(a):
    toks = valid_tokens(a.ledger)
    if not toks:
        print("(no valid approval tokens)")
        return
    for chash, p in toks.items():
        print(f"{p['token']}  {p['checklist_id']:<24}  {chash}  {p['source_ref']}")


def verify(path):
    prev = _ada.GENESIS_PREV
    for i, e in enumerate(_entries(path)):
        if e.get("seq") != i:
            return False, f"seq mismatch at line {i}: got {e.get('seq')}"
        if e.get("prev_hash") != prev:
            return False, f"broken chain at seq {i}: prev_hash mismatch"
        body = {k: e[k] for k in e if k != "entry_hash"}
        expect = _ada.sha256_str(prev + _ada.canonical(body))
        if expect != e.get("entry_hash"):
            return False, f"tampered entry at seq {i}: entry_hash mismatch"
        prev = e["entry_hash"]
    return True, "chain intact"


def cmd_verify(a):
    ok, msg = verify(a.ledger)
    print(("OK: " if ok else "FAIL: ") + msg)
    sys.exit(0 if ok else 1)


def main():
    p = argparse.ArgumentParser(description="ADA hash-chained consent ledger")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("init"); s.set_defaults(fn=cmd_init)
    s.add_argument("--ledger", required=True)
    s.add_argument("--run-id", required=True)
    s.add_argument("--client", required=True)
    s.add_argument("--operator", required=True)
    s.add_argument("--host", required=True)

    s = sub.add_parser("authorize"); s.set_defaults(fn=cmd_authorize)
    s.add_argument("--ledger", required=True)
    s.add_argument("--connector", required=True)
    s.add_argument("--scope", required=True)

    s = sub.add_parser("approve"); s.set_defaults(fn=cmd_approve)
    s.add_argument("--ledger", required=True)
    s.add_argument("--path", required=True)
    s.add_argument("--checklist-id", required=True)
    s.add_argument("--note", default="")

    s = sub.add_parser("revoke"); s.set_defaults(fn=cmd_revoke)
    s.add_argument("--ledger", required=True)
    s.add_argument("--token", required=True)
    s.add_argument("--note", default="")

    s = sub.add_parser("tokens"); s.set_defaults(fn=cmd_tokens)
    s.add_argument("--ledger", required=True)

    s = sub.add_parser("verify"); s.set_defaults(fn=cmd_verify)
    s.add_argument("--ledger", required=True)

    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
