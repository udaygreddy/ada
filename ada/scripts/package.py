#!/usr/bin/env python3
"""
package.py — assemble the handoff package (PLAYBOOK §3, §5 Phase C, §6).

The enforcement point. It stages a file ONLY if the ledger holds a valid,
unrevoked approval token whose content_hash matches the file's current hash.
A file the agent "decided" to include but never got approved cannot appear in
the package. Aborts if the ledger chain is broken.

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
    approved = ledger_mod.valid_tokens(a.ledger)  # {content_hash: payload}

    run = next((e for e in _ada.read_jsonl(a.ledger) if e["action"] == "init"), None)
    run_meta = run["payload"] if run else {}

    files_root = os.path.join(a.out, "files")
    os.makedirs(files_root, exist_ok=True)

    staged = []   # (checklist_id, candidate, payload, staged_path)
    skipped_no_match = []
    for chash, payload in approved.items():
        cand = cand_by_hash.get(chash)
        cid = payload["checklist_id"]
        if not cand:
            # Approved hash with no current candidate file (moved/changed) — record.
            skipped_no_match.append(payload)
            continue
        section = tax_by_id.get(cid, {}).get("section", "Unsectioned")
        dest_dir = os.path.join(files_root, safe_section(section))
        os.makedirs(dest_dir, exist_ok=True)
        dest = os.path.join(dest_dir, cand["filename"])
        shutil.copy2(cand["source_ref"], dest)
        staged.append((cid, cand, payload, dest))

    # Build manifest items: status per in-scope taxonomy item.
    approved_ids = {cid for cid, _, _, _ in staged}
    items = []
    for t in taxonomy:
        cid = t["id"]
        item_cands = []
        for scid, cand, payload, dest in staged:
            if scid == cid:
                item_cands.append({
                    "source": cand["connector"],
                    "source_ref": cand["source_ref"],
                    "filename": cand["filename"],
                    "content_hash": cand["content_hash"],
                    "sensitivity": cand.get("sensitivity", "unknown"),
                    "decision": "included",
                    "token": payload["token"],
                    "staged_as": os.path.relpath(dest, a.out),
                })
        items.append({
            "checklist_id": cid,
            "label": t.get("label", cid),
            "section": t.get("section", ""),
            "system": t.get("system", ""),
            "status": "found" if cid in approved_ids else "missing",
            "candidates": item_cands,
        })

    gaps = [{"checklist_id": t["id"], "label": t.get("label", t["id"]),
             "system": t.get("system", ""), "source_hint": t.get("source_hint", "")}
            for t in taxonomy if t["id"] not in approved_ids]

    manifest = {
        "run": run_meta,
        "generated_at": _ada.now_iso(),
        "ledger_verified": True,
        "counts": {"in_scope": len(taxonomy), "collected": len(approved_ids),
                   "staged_files": len(staged), "gaps": len(gaps)},
        "items": items,
        "gaps": gaps,
    }
    with open(os.path.join(a.out, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    shutil.copy2(a.ledger, os.path.join(a.out, "ledger.jsonl"))
    write_gap_report(os.path.join(a.out, "gap_report.md"), manifest, staged)

    print(f"packaged {len(staged)} file(s) → {a.out}")
    print(f"  collected {len(approved_ids)}/{len(taxonomy)} in-scope items; "
          f"{len(gaps)} gap(s)")
    if skipped_no_match:
        print(f"  WARNING: {len(skipped_no_match)} approved token(s) had no "
              f"matching current file (moved or changed) — not staged")


def write_gap_report(path, manifest, staged):
    run = manifest["run"]
    c = manifest["counts"]
    lines = [
        f"# {run.get('client', 'Client')} — ADA Discovery Report",
        "",
        f"- Run: `{run.get('run_id', '?')}`  ·  Operator: {run.get('operator', '?')}"
        f"  ·  Host: {run.get('host', '?')}",
        f"- Generated: {manifest['generated_at']}",
        f"- **Collected {c['collected']} of {c['in_scope']} in-scope items** "
        f"({c['staged_files']} files staged, {c['gaps']} gaps)",
        f"- Ledger integrity: {'✅ verified' if manifest['ledger_verified'] else '❌'}",
        "",
        "## ✅ Collected",
    ]
    sensitive = [s for s in staged if s[1].get("sensitivity") == "high"]
    for cid, cand, payload, dest in staged:
        flag = " ⚠ sensitive" if cand.get("sensitivity") == "high" else ""
        lines.append(f"- **{cid}** — {cand['filename']}{flag}")
    if not staged:
        lines.append("- (none)")
    lines += ["", "## ❌ Still needed"]
    for g in manifest["gaps"]:
        hint = f" — _{g['source_hint']}_" if g.get("source_hint") else ""
        lines.append(f"- **{g['checklist_id']}** {g['label']} ({g['system']}){hint}")
    if not manifest["gaps"]:
        lines.append("- (none)")
    if sensitive:
        lines += ["", f"> ⚠ {len(sensitive)} staged file(s) are high-sensitivity "
                  f"(PII). Confirm secure handoff channel before transmitting."]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
