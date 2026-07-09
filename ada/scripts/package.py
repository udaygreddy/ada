#!/usr/bin/env python3
"""
package.py — assemble the handoff package (PROCEDURE.md Phase C).

The enforcement point. It stages a file ONLY if the ledger holds a valid,
unrevoked approval token whose content_hash matches the file's current hash.
A file the agent "decided" to include but never got approved cannot appear in
the package. Aborts if the ledger chain is broken.

Reporting denominator:
  - If the ledger has per-client requirements (PROCEDURE Phase 0, from email /
    Salesforce Case), the report measures collected-vs-REQUESTED, and each unmet
    requirement is annotated with the taxonomy's source hint (HOW/WHERE).
  - Otherwise it falls back to measuring against the full taxonomy.

Outputs into STAGING_DIR:
  files/<section>/<filename>   approved files, organized by checklist section
  manifest.json                full run manifest
  gap_report.md                human-readable summary
  ledger.jsonl                 copy of the consent ledger

Usage:
  package.py --ledger L --candidates C --taxonomy T --out STAGING_DIR
"""
import argparse
import json
import os
import re
import shutil
import sys

import _ada
import ledger as ledger_mod


def safe_section(section):
    s = re.sub(r"[^A-Za-z0-9]+", "_", section).strip("_")
    return s or "Unsectioned"


def main():
    p = argparse.ArgumentParser(description="Assemble ADA handoff package")
    p.add_argument("--ledger", required=True)
    p.add_argument("--candidates", required=True)
    p.add_argument("--taxonomy", required=True)
    p.add_argument("--out", required=True)
    a = p.parse_args()

    ok, msg = ledger_mod.verify(a.ledger)
    if not ok:
        sys.exit(f"ABORT: ledger integrity check failed — {msg}")

    taxonomy = _ada.load_taxonomy(a.taxonomy)
    tax_by_id = {t["id"]: t for t in taxonomy}
    candidates = _ada.read_jsonl(a.candidates)
    cand_by_hash = {c["content_hash"]: c for c in candidates}
    approved = ledger_mod.valid_tokens(a.ledger)          # {content_hash: payload}
    reqs = ledger_mod.requirements(a.ledger)              # [] if none recorded

    run = next((e for e in _ada.read_jsonl(a.ledger) if e["action"] == "init"), None)
    run_meta = run["payload"] if run else {}

    files_root = os.path.join(a.out, "files")
    os.makedirs(files_root, exist_ok=True)

    # Stage approved files (the hard gate).
    staged = []          # (checklist_key, candidate, payload, staged_path)
    skipped_no_match = []
    staged_by_key = {}
    for chash, payload in approved.items():
        cand = cand_by_hash.get(chash)
        key = payload["checklist_id"]   # a taxonomy id OR a requirement req_id
        if not cand:
            skipped_no_match.append(payload)
            continue
        section = tax_by_id.get(key, {}).get("section", "Client-Specific")
        dest_dir = os.path.join(files_root, safe_section(section))
        os.makedirs(dest_dir, exist_ok=True)
        dest = os.path.join(dest_dir, cand["filename"])
        shutil.copy2(cand["source_ref"], dest)
        entry = {
            "source": cand["connector"],
            "source_ref": cand["source_ref"],
            "filename": cand["filename"],
            "content_hash": cand["content_hash"],
            "sensitivity": cand.get("sensitivity", "unknown"),
            "decision": "included",
            "token": payload["token"],
            "validation": payload.get("validation"),
            "staged_as": os.path.relpath(dest, a.out),
        }
        staged.append((key, cand, payload, dest))
        staged_by_key.setdefault(key, []).append(entry)

    approved_keys = set(staged_by_key)

    if reqs:
        manifest = build_requirements_manifest(
            reqs, tax_by_id, taxonomy, approved_keys, staged_by_key, run_meta)
    else:
        manifest = build_taxonomy_manifest(
            taxonomy, approved_keys, staged_by_key, run_meta)

    manifest["counts"]["validation"] = validation_tally(staged)

    with open(os.path.join(a.out, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    shutil.copy2(a.ledger, os.path.join(a.out, "ledger.jsonl"))
    write_gap_report(os.path.join(a.out, "gap_report.md"), manifest, staged)

    c = manifest["counts"]
    v = c["validation"]
    print(f"packaged {len(staged)} file(s) → {a.out}")
    print(f"  mode: {manifest['mode']}  ·  collected {c['collected']}/"
          f"{c['requested' if reqs else 'in_scope']}  ·  {c['gaps']} gap(s)")
    print(f"  validation: {v['validated']} ok · {v['warn']} warn · "
          f"{v['fail_override']} override · {v['unvalidated']} not validated")
    if skipped_no_match:
        print(f"  WARNING: {len(skipped_no_match)} approved token(s) had no "
              f"matching current file (moved or changed) — not staged")


def build_requirements_manifest(reqs, tax_by_id, taxonomy, approved_keys,
                                staged_by_key, run_meta):
    items = []
    gaps = []
    for r in reqs:
        tid = r.get("mapped_taxonomy_id") or ""
        key = tid or r["req_id"]            # approvals reference taxonomy id or req_id
        tx = tax_by_id.get(tid, {})
        found = key in approved_keys
        item = {
            "req_id": r["req_id"],
            "requested_text": r.get("requested_text", ""),
            "kind": r.get("kind", "collect"),
            "source_kind": r.get("source_kind", ""),
            "source_ref": r.get("source_ref", ""),
            "mapped_taxonomy_id": tid,
            "system": tx.get("system", ""),
            "method": tx.get("method", ""),
            "source_hint": tx.get("source_hint", ""),
            "sensitivity": tx.get("sensitivity", "unknown"),
            "status": "found" if found else "missing",
            "staged": staged_by_key.get(key, []),
        }
        items.append(item)
        if not found:
            gaps.append(item)

    requested_tax_ids = {r.get("mapped_taxonomy_id") for r in reqs if r.get("mapped_taxonomy_id")}
    not_requested = [{"checklist_id": t["id"], "label": t.get("label", t["id"]),
                      "system": t.get("system", "")}
                     for t in taxonomy if t["id"] not in requested_tax_ids]

    return {
        "mode": "requirements",
        "run": run_meta,
        "generated_at": _ada.now_iso(),
        "ledger_verified": True,
        "counts": {"requested": len(reqs), "collected": len(reqs) - len(gaps),
                   "gaps": len(gaps), "not_requested": len(not_requested)},
        "requirements": items,
        "gaps": gaps,
        "taxonomy_not_requested": not_requested,
    }


def build_taxonomy_manifest(taxonomy, approved_keys, staged_by_key, run_meta):
    items = []
    for t in taxonomy:
        cid = t["id"]
        items.append({
            "checklist_id": cid, "label": t.get("label", cid),
            "section": t.get("section", ""), "system": t.get("system", ""),
            "status": "found" if cid in approved_keys else "missing",
            "staged": staged_by_key.get(cid, []),
        })
    gaps = [{"checklist_id": t["id"], "label": t.get("label", t["id"]),
             "system": t.get("system", ""), "source_hint": t.get("source_hint", "")}
            for t in taxonomy if t["id"] not in approved_keys]
    return {
        "mode": "taxonomy",
        "run": run_meta,
        "generated_at": _ada.now_iso(),
        "ledger_verified": True,
        "counts": {"in_scope": len(taxonomy), "collected": len(approved_keys),
                   "gaps": len(gaps)},
        "items": items,
        "gaps": gaps,
    }


def write_gap_report(path, manifest, staged):
    run = manifest["run"]
    c = manifest["counts"]
    requested_mode = manifest["mode"] == "requirements"
    denom = c["requested"] if requested_mode else c["in_scope"]
    headline = ("Collected {0} of {1} requested items".format(c["collected"], denom)
                if requested_mode else
                "Collected {0} of {1} in-scope items".format(c["collected"], denom))
    lines = [
        f"# {run.get('client', 'Client')} — ADA Discovery Report",
        "",
        f"- Run: `{run.get('run_id', '?')}`  ·  Operator: {run.get('operator', '?')}"
        f"  ·  Host: {run.get('host', '?')}",
        f"- Generated: {manifest['generated_at']}",
        f"- **{headline}** ({c['gaps']} gaps)",
        f"- Ledger integrity: {'✅ verified' if manifest['ledger_verified'] else '❌'}",
        "",
        "## ✅ Collected",
    ]
    for key, cand, payload, dest in staged:
        flag = " ⚠ sensitive" if cand.get("sensitivity") == "high" else ""
        lines.append(f"- **{key}** — {cand['filename']}{flag}{_val_badge(payload.get('validation'))}")
    if not staged:
        lines.append("- (none)")

    lines += ["", "## ❌ Still needed"]
    if requested_mode:
        for g in manifest["gaps"]:
            where = g.get("source_hint") or g.get("system") or "source TBD"
            lines.append(
                f"- **{g['req_id']}** {g['requested_text']} "
                f"({g['kind']}) — _{where}_")
    else:
        for g in manifest["gaps"]:
            hint = f" — _{g['source_hint']}_" if g.get("source_hint") else ""
            lines.append(f"- **{g['checklist_id']}** {g['label']} ({g['system']}){hint}")
    if not manifest["gaps"]:
        lines.append("- (none)")

    if requested_mode and manifest.get("taxonomy_not_requested"):
        lines += ["", "## ℹ️ In master catalog but not requested by ADP"]
        for x in manifest["taxonomy_not_requested"]:
            lines.append(f"- {x['checklist_id']} {x['label']} ({x['system']})")

    v = c.get("validation")
    if v:
        lines += ["", f"**Validation:** {v['validated']} validated · {v['warn']} "
                  f"warning · {v['fail_override']} override · {v['unvalidated']} "
                  f"not validated."]
        if v["fail_override"]:
            lines.append("> ❌ Some files were approved over a FAILED validation "
                         "(override) — review the ledger before transmitting.")

    sensitive = [s for s in staged if s[1].get("sensitivity") == "high"]
    if sensitive:
        lines += ["", f"> ⚠ {len(sensitive)} staged file(s) are high-sensitivity "
                  f"(PII). Confirm secure handoff channel before transmitting."]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def _val_badge(v):
    if not v:
        return "  ·  ⬜ not validated"
    s = v.get("status")
    if s == "pass":
        return "  ·  ✅ validated"
    if s == "warn":
        return "  ·  ⚠ validation warning"
    if s == "fail":
        return "  ·  ❌ validation FAILED (override)"
    return "  ·  ⬜ n/a"


def validation_tally(staged):
    t = {"validated": 0, "warn": 0, "fail_override": 0, "unvalidated": 0}
    for _key, _cand, payload, _dest in staged:
        v = payload.get("validation")
        s = v.get("status") if v else None
        if s == "pass":
            t["validated"] += 1
        elif s == "warn":
            t["warn"] += 1
        elif s == "fail":
            t["fail_override"] += 1
        else:
            t["unvalidated"] += 1
    return t


if __name__ == "__main__":
    main()
