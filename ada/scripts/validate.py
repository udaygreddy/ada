#!/usr/bin/env python3
"""
validate.py — check a collected file against its requirement (PROCEDURE VALIDATE).

Does the file actually match what ADP asked for? Two checks today, built as a
pluggable registry so more can be added later without rework:

  period    — does the file's covered date range match the requested quarter /
              range (e.g. "last quarter")?
  doc_type  — is the file the requested document type (payroll_register vs w2 …)?

Division of labor (ADA principle): the agent EXTRACTS attributes (reads the file /
requested_text); this script RESOLVES periods deterministically and DECIDES the
verdict. For text/CSV the script extracts dates itself; for PDF/XLSX (stdlib can't
parse) the agent passes the covered dates + detected type as flags.

Usage:
  validate.py --file F [--expected-doc-type T] [--expected-period P]
              [--ref-date YYYY-MM-DD]
              [--file-period-start YYYY-MM-DD --file-period-end YYYY-MM-DD]
              [--file-doc-type T]

Emits a JSON verdict; exit code 0 unless overall status is `fail` (then 1).
Statuses: pass | warn | fail | na (not-applicable).
"""
import argparse
import datetime as dt
import json
import os
import re
import sys

TEXT_EXT = {"txt", "csv", "tsv", "json"}
_SEV = {"na": 0, "pass": 1, "warn": 2, "fail": 3}


# ---------- period resolution (deterministic) ----------

def _quarter_of(d):
    return (d.month - 1) // 3 + 1


def _quarter_range(year, q):
    start = dt.date(year, 3 * (q - 1) + 1, 1)
    end = (dt.date(year + 1, 1, 1) if q == 4
           else dt.date(year, 3 * q + 1, 1)) - dt.timedelta(days=1)
    return start, end


def resolve_period(phrase, ref_date=None):
    """Resolve a period phrase to (start, end, label) or None if unparseable."""
    if not phrase:
        return None
    ref = ref_date or dt.date.today()
    p = phrase.strip().lower()

    # explicit range: 2026-01-01..2026-03-31  or  ... to ...
    m = re.search(r"(\d{4}-\d{2}-\d{2})\s*(?:\.\.|to|-|–|—)\s*(\d{4}-\d{2}-\d{2})", p)
    if m:
        return (dt.date.fromisoformat(m.group(1)),
                dt.date.fromisoformat(m.group(2)), phrase.strip())

    # explicit quarter: Q1 2026 / q3'25 / Q2
    m = re.search(r"\bq([1-4])\b[\s'’]*(\d{4}|\d{2})?", p)
    if m:
        q = int(m.group(1))
        yr = m.group(2)
        year = ref.year if not yr else (int(yr) if len(yr) == 4 else 2000 + int(yr))
        s, e = _quarter_range(year, q)
        return s, e, f"Q{q} {year}"

    cq = _quarter_of(ref)
    if any(k in p for k in ("last quarter", "previous quarter", "prior quarter")):
        if cq == 1:
            s, e = _quarter_range(ref.year - 1, 4)
            return s, e, f"Q4 {ref.year - 1}"
        s, e = _quarter_range(ref.year, cq - 1)
        return s, e, f"Q{cq - 1} {ref.year}"
    if any(k in p for k in ("current quarter", "this quarter")):
        s, e = _quarter_range(ref.year, cq)
        return s, e, f"Q{cq} {ref.year}"
    if any(k in p for k in ("ytd", "year to date", "year-to-date")):
        return dt.date(ref.year, 1, 1), ref, f"YTD {ref.year}"
    if any(k in p for k in ("current year", "this year", "calendar year")):
        return dt.date(ref.year, 1, 1), dt.date(ref.year, 12, 31), str(ref.year)
    return None


# ---------- date extraction from text content ----------

_ISO = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
_US = re.compile(r"\b(\d{1,2})/(\d{1,2})/(\d{2,4})\b")
_QLAB = re.compile(r"\bq([1-4])[\s'’]*(\d{4}|\d{2})\b", re.I)


def _safe_date(y, m, d):
    try:
        return dt.date(y, m, d)
    except ValueError:
        return None


def extract_dates_from_text(path):
    """Return sorted list of dates found in a text/CSV file (quarter labels
    expand to their start+end). Empty if none/unreadable."""
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()
    except OSError:
        return []
    found = []
    for y, m, d in _ISO.findall(text):
        dd = _safe_date(int(y), int(m), int(d))
        if dd:
            found.append(dd)
    for a, b, y in _US.findall(text):
        yr = int(y) if len(y) == 4 else 2000 + int(y)
        dd = _safe_date(yr, int(a), int(b))   # US M/D/Y
        if dd:
            found.append(dd)
    for q, y in _QLAB.findall(text):
        yr = int(y) if len(y) == 4 else 2000 + int(y)
        s, e = _quarter_range(yr, int(q))
        found += [s, e]
    return sorted(found)


# ---------- checks (registry) ----------

def check_period(expected, actual):
    exp = expected.get("period_range")   # (start, end, label) or None
    if not exp:
        return {"check": "period", "status": "na", "reason": "no expected period"}
    start, end, label = exp
    span = actual.get("file_span")       # (min, max) or None
    if not span:
        return {"check": "period", "status": "fail",
                "reason": f"expected {label}; no dates found in file"}
    fmin, fmax = span
    within = start <= fmin and fmax <= end
    overlaps = fmin <= end and start <= fmax
    fspan = f"{fmin.isoformat()}..{fmax.isoformat()}"
    if within:
        return {"check": "period", "status": "pass",
                "reason": f"file {fspan} within {label}"}
    if overlaps:
        return {"check": "period", "status": "warn",
                "reason": f"file {fspan} partially overlaps {label}"}
    return {"check": "period", "status": "fail",
            "reason": f"file {fspan} outside {label}"}


def check_doc_type(expected, actual):
    exp = (expected.get("doc_type") or "").strip().lower()
    if not exp:
        return {"check": "doc_type", "status": "na", "reason": "no expected type"}
    act = (actual.get("doc_type") or "").strip().lower()
    if not act:
        return {"check": "doc_type", "status": "warn",
                "reason": f"expected {exp}; file type not determined"}
    if act == exp:
        return {"check": "doc_type", "status": "pass", "reason": f"type {exp}"}
    return {"check": "doc_type", "status": "fail",
            "reason": f"expected {exp}, file looks like {act}"}


CHECKS = [check_period, check_doc_type]   # add future checks here


def validate(expected, actual):
    results = [c(expected, actual) for c in CHECKS]
    applicable = [r for r in results if r["status"] != "na"]
    overall = "na" if not applicable else max(
        (r["status"] for r in applicable), key=lambda s: _SEV[s])
    summary = "; ".join(r["reason"] for r in applicable) or "no checks applicable"
    return {"status": overall, "summary": summary, "checks": results,
            "expected": {"doc_type": expected.get("doc_type") or None,
                         "period": expected.get("period_label")},
            "resolved_period": (expected["period_range"][0].isoformat() + ".." +
                                expected["period_range"][1].isoformat())
                               if expected.get("period_range") else None}


def main():
    p = argparse.ArgumentParser(description="Validate a collected file vs its requirement")
    p.add_argument("--file", required=True)
    p.add_argument("--expected-doc-type", default="")
    p.add_argument("--expected-period", default="")
    p.add_argument("--ref-date", default="")
    p.add_argument("--file-period-start", default="")
    p.add_argument("--file-period-end", default="")
    p.add_argument("--file-doc-type", default="",
                   help="agent-detected type (required for PDF/XLSX)")
    a = p.parse_args()

    ref = dt.date.fromisoformat(a.ref_date) if a.ref_date else dt.date.today()
    period_range = resolve_period(a.expected_period, ref)
    expected = {"doc_type": a.expected_doc_type,
                "period_range": period_range,
                "period_label": (period_range[2] if period_range
                                 else (a.expected_period or None))}

    # file span: agent-supplied wins; else extract from text content.
    span = None
    if a.file_period_start and a.file_period_end:
        span = (dt.date.fromisoformat(a.file_period_start),
                dt.date.fromisoformat(a.file_period_end))
    else:
        ext = os.path.splitext(a.file)[1].lower().lstrip(".")
        if ext in TEXT_EXT and os.path.isfile(a.file):
            ds = extract_dates_from_text(a.file)
            if ds:
                span = (ds[0], ds[-1])
    actual = {"file_span": span, "doc_type": a.file_doc_type}

    verdict = validate(expected, actual)
    print(json.dumps(verdict, indent=2))
    sys.exit(1 if verdict["status"] == "fail" else 0)


if __name__ == "__main__":
    main()
