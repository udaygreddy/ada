#!/usr/bin/env python3
"""
pii_scan.py — local sensitivity flagging (PLAYBOOK §3, §7).

Runs as CODE, not via the LLM: document content is read here and matched with
regex, so PII never has to be sent to the model to decide sensitivity. For
text-extractable files (.txt/.csv/.tsv/.json) it scans content; for binary
formats (.pdf/.xlsx/.docx) — which stdlib can't parse — it falls back to
filename heuristics. It records only match COUNTS, never the matched values.

Sensitivity:
  high   — PII found in content, or a high-risk filename (W-2, paystub,
           payroll register/journal, YTD, census, SSN)
  medium — tax-form / bank-related filenames
  low    — everything else

Usage:
  pii_scan.py --candidates FILE [--update]    # annotate a candidates jsonl
  pii_scan.py PATH [PATH ...]                  # ad-hoc, prints findings
"""
import argparse
import os
import re
import sys

import _ada

TEXT_EXT = {"txt", "csv", "tsv", "json"}

PATTERNS = {
    "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "ein": re.compile(r"\b\d{2}-\d{7}\b"),
    "bank_acct": re.compile(r"\b\d{8,17}\b"),
    "routing": re.compile(r"\b\d{9}\b"),
}

HIGH_NAME = re.compile(
    r"(w-?2|w-?4|paystub|pay[\s_-]?stub|payroll[\s_-]?(register|journal)"
    r"|ytd|census|ssn|social[\s_-]?security)", re.I)
MEDIUM_NAME = re.compile(r"(941|940|sui|sit|tax|deposit|bank|voided|routing)", re.I)


def scan_content(path):
    findings = {}
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()
    except OSError:
        return findings
    for name, rx in PATTERNS.items():
        c = len(rx.findall(text))
        if c:
            findings[name] = c
    return findings


def classify(path, ext):
    findings = {}
    if ext in TEXT_EXT and os.path.isfile(path):
        findings = scan_content(path)
    base = os.path.basename(path)
    if findings or HIGH_NAME.search(base):
        sens = "high"
    elif MEDIUM_NAME.search(base):
        sens = "medium"
    else:
        sens = "low"
    # findings carries COUNTS only — never the matched values.
    return sens, findings


def main():
    p = argparse.ArgumentParser(description="ADA local PII / sensitivity scan")
    p.add_argument("paths", nargs="*")
    p.add_argument("--candidates", default="")
    p.add_argument("--update", action="store_true",
                   help="rewrite the candidates file with sensitivity + findings")
    a = p.parse_args()

    if a.candidates:
        cands = _ada.read_jsonl(a.candidates)
        for c in cands:
            sens, findings = classify(c["source_ref"], c.get("ext", ""))
            c["sensitivity"] = sens
            c["pii_findings"] = findings
        if a.update:
            with open(a.candidates, "w", encoding="utf-8") as f:
                for c in cands:
                    f.write(_ada.canonical(c) + "\n")
            highs = sum(1 for c in cands if c["sensitivity"] == "high")
            sys.stderr.write(
                f"scanned {len(cands)} candidate(s): {highs} high-sensitivity\n")
        else:
            for c in cands:
                print(f"{c['sensitivity']:<6} {c['filename']}  {c.get('pii_findings', {})}")
        return

    for path in a.paths:
        ext = os.path.splitext(path)[1].lower().lstrip(".")
        sens, findings = classify(path, ext)
        print(f"{sens:<6} {path}  {findings}")


if __name__ == "__main__":
    main()
