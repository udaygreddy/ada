#!/usr/bin/env python3
"""
make_fixtures.py — generate the ADA validation test corpus.

Creates one PASS and one or more FAIL fixtures per document type, matching the
rule ids in ada/validations.yaml. Fixtures are real files (PDF via the same
stdlib construction validate.py must parse, plus CSV) so the whole pipeline —
extraction, masking, model judgment — can be exercised end to end.

All data is SYNTHETIC. SSNs use the 000-/666- ranges the SSA never issues;
EINs, account and routing numbers are invented. Nothing here is real PII.

Usage:
  python3 tests/make_fixtures.py [--out tests/fixtures]
"""
import argparse
import os
import zlib

# Reference date the corpus is built around: 2026-07-20 (mid-late July).
# Per the ADP guide that window makes Q2 2026 the required quarter and
# Q1 2026 the acceptable fallback — so "Q2" fixtures pass and "Q1-only"
# fixtures fail the required-quarter checks.
REF_DATE = "2026-07-20"
Q2_CHECK_DATES = ["04/10/2026", "04/24/2026", "05/08/2026", "05/22/2026",
                  "06/05/2026", "06/19/2026"]
Q1_CHECK_DATES = ["01/09/2026", "01/23/2026", "02/06/2026", "02/20/2026",
                  "03/06/2026", "03/20/2026"]


def pdf(lines, compress=True):
    """Build a minimal one-page PDF whose text lives in a content stream."""
    body = " ".join("(%s) Tj" % l.replace("(", "").replace(")", "") for l in lines)
    cs = ("BT /F1 10 Tf " + body + " ET").encode("latin-1", "replace")
    stream = zlib.compress(cs) if compress else cs
    filt = b"/Filter /FlateDecode " if compress else b""
    return (b"%PDF-1.4\n"
            b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n"
            b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n"
            b"3 0 obj << /Type /Page /Parent 2 0 R /Contents 4 0 R "
            b"/Resources << /Font << /F1 5 0 R >> >> >> endobj\n"
            b"4 0 obj << " + filt + b"/Length " + str(len(stream)).encode() + b" >>\n"
            b"stream\n" + stream + b"\nendstream\nendobj\n"
            b"5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n"
            b"%%EOF\n")


def scanned_pdf():
    """A PDF with no text operators — stands in for an image-only scan."""
    cs = b"q 612 0 0 792 0 0 cm /Im0 Do Q"
    stream = zlib.compress(cs)
    return (b"%PDF-1.4\n"
            b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n"
            b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n"
            b"3 0 obj << /Type /Page /Parent 2 0 R /Contents 4 0 R >> endobj\n"
            b"4 0 obj << /Filter /FlateDecode /Length " + str(len(stream)).encode() + b" >>\n"
            b"stream\n" + stream + b"\nendstream\nendobj\n%%EOF\n")


EMPLOYEES = [
    ("Avery Nolan",   "000-11-2001", "1988-03-14", "2021-06-01", "68000.00", "avery@example.com"),
    ("Blair Ozanne",  "000-11-2002", "1992-11-02", "2022-01-18", "54500.00", "blair@example.com"),
    ("Casey Pruitt",  "000-11-2003", "1979-07-27", "2019-09-09", "81250.00", "casey@example.com"),
    ("Devon Quill",   "000-11-2004", "1995-02-05", "2023-04-24", "47000.00", "devon@example.com"),
]
TERMINATED = [
    ("Emery Ruiz",    "000-11-2005", "1990-08-30", "2020-02-10", "59000.00", "emery@example.com"),
]

FIXTURES = {}


def add(name, data):
    FIXTURES[name] = data


# ---------- employee_masterfile ----------
_mf_head = "Name,SSN,DateOfBirth,HireDate,AnnualRate,HomeAddress,Email,Status\n"


def _mf_row(e, status, ssn):
    return "%s,%s,%s,%s,%s,\"120 Main St, Springfield IL\",%s,%s\n" % (
        e[0], ssn, e[2], e[3], e[4], e[5], status)


add("masterfile_pass.csv", _mf_head
    + "".join(_mf_row(e, "Active", e[1]) for e in EMPLOYEES)
    + "".join(_mf_row(e, "Terminated", e[1]) for e in TERMINATED))

add("masterfile_fail_masked_ssn.csv", _mf_head
    + "".join(_mf_row(e, "Active", "XXX-XX-" + e[1][-4:]) for e in EMPLOYEES)
    + "".join(_mf_row(e, "Terminated", "XXX-XX-" + e[1][-4:]) for e in TERMINATED))

add("masterfile_fail_no_ssn_column.csv",
    "Name,DateOfBirth,HireDate,AnnualRate,Status\n"
    + "".join("%s,%s,%s,%s,Active\n" % (e[0], e[2], e[3], e[4]) for e in EMPLOYEES))

add("masterfile_warn_actives_only.csv", _mf_head
    + "".join(_mf_row(e, "Active", e[1]) for e in EMPLOYEES))

add("masterfile_warn_missing_fields.csv",
    "Name,SSN,Status\n"
    + "".join("%s,%s,Active\n" % (e[0], e[1]) for e in EMPLOYEES)
    + "".join("%s,%s,Terminated\n" % (e[0], e[1]) for e in TERMINATED))


# ---------- payroll_register ----------
def _register(dates, title="Payroll Journal"):
    lines = ["%s - Acme Manufacturing LLC" % title, "EIN 00-1234567"]
    for d in dates:
        lines.append("Check Date: %s" % d)
        for e in EMPLOYEES:
            lines.append("  %s  %s  Gross 2,615.38  Net 1,942.771" % (e[0], e[1]))
        lines.append("  Period Total  Gross 10,461.52")
    lines.append("Report generated on 07/20/2026")   # print-date trap
    return pdf(lines)


add("register_pass_q2.pdf", _register(Q2_CHECK_DATES))
add("register_fail_q1.pdf", _register(Q1_CHECK_DATES))
add("register_pass_single_day.pdf", _register(["05/08/2026"]))
add("register_warn_combined_range.pdf", pdf([
    "Payroll Register Summary - Process Date Range",
    "Range: 04/01/2026 through 06/30/2026",
    "Combined multi-payroll export (6 payrolls in one file)",
    "Total Gross 62,769.12",
]))
add("register_fail_scanned.pdf", scanned_pdf())


# ---------- ytd_balances ----------
add("ytd_pass.pdf", pdf([
    "Employee Earnings Record - Year to Date",
    "Range: 01/01/2026 through 06/19/2026",
    "Acme Manufacturing LLC",
] + ["  %s  %s  YTD Gross 15,692.28  YTD Fed WH 2,041.00" % (e[0], e[1])
     for e in EMPLOYEES]))

add("ytd_fail_quarter_only.pdf", pdf([
    "Employee Earnings Record",
    "Range: 04/01/2026 through 06/19/2026",
] + ["  %s  Gross 7,846.14" % e[0] for e in EMPLOYEES]))

add("ytd_fail_stale.pdf", pdf([
    "Employee Earnings Record - Year to Date",
    "Range: 01/01/2026 through 03/20/2026",
] + ["  %s  YTD Gross 7,846.14" % e[0] for e in EMPLOYEES]))


# ---------- w2 ----------
add("w2_pass_2025.pdf", pdf([
    "2025 Form W-2 Wage and Tax Statement",
    "Employer: Acme Manufacturing LLC  EIN 00-1234567",
    "Employee: Avery Nolan  SSN 000-11-2001",
    "1 Wages, tips, other compensation  68,000.00",
    "2 Federal income tax withheld  8,432.00",
]))

add("w2_fail_wrong_year.pdf", pdf([
    "2023 Form W-2 Wage and Tax Statement",
    "Employer: Acme Manufacturing LLC  EIN 00-1234567",
    "Employee: Avery Nolan  SSN 000-11-2001",
    "1 Wages, tips, other compensation  61,500.00",
]))


# ---------- tax_return ----------
add("tax_return_pass_q2_941.pdf", pdf([
    "Form 941 for 2026: Employer's QUARTERLY Federal Tax Return",
    "Report for this quarter: 2 (April, May, June)",
    "EIN 00-1234567  Acme Manufacturing LLC",
    "Quarter ended 06/30/2026",
    "5a Taxable social security wages  62,769.12",
    "12 Total taxes after adjustments  14,204.88",
]))

add("tax_return_fail_in_progress_q3.pdf", pdf([
    "Form 941 for 2026: Employer's QUARTERLY Federal Tax Return",
    "Report for this quarter: 3 (July, August, September)",
    "EIN 00-1234567  Acme Manufacturing LLC",
    "Quarter ending 09/30/2026 - IN PROGRESS, not yet filed",
]))

add("tax_return_fail_too_old_q3_2025.pdf", pdf([
    "Form 941 for 2025: Employer's QUARTERLY Federal Tax Return",
    "Report for this quarter: 3 (July, August, September)",
    "EIN 00-1234567  Quarter ended 09/30/2025",
]))

add("tax_return_pass_q2_sui.pdf", pdf([
    "Illinois Department of Employment Security",
    "Quarterly Contribution and Wage Report (SUI)",
    "Quarter: 2nd Quarter 2026  Period ending 06/30/2026",
    "Account 0000-0000-0  Acme Manufacturing LLC",
    "Total wages 62,769.12  Contribution due 1,224.00",
]))


# ---------- tax_deposit ----------
add("tax_deposit_pass_q2.pdf", pdf([
    "Statement of Filings and Deposits",
    "Year 2026  Quarter 2",
] + ["Deposit  %s  Federal 941  3,551.22  Status: Paid" % d for d in Q2_CHECK_DATES]))

add("tax_deposit_warn_q1.pdf", pdf([
    "Statement of Filings and Deposits",
    "Year 2026  Quarter 1",
] + ["Deposit  %s  Federal 941  3,551.22  Status: Paid" % d for d in Q1_CHECK_DATES]))


# ---------- bank_proof ----------
add("bank_proof_pass_voided_check.pdf", pdf([
    "FIRST SPRINGFIELD BANK",
    "ACME MANUFACTURING LLC",
    "120 Main St, Springfield IL",
    "VOID  VOID  VOID",
    "Routing 000000518   Account 00000149772",
    "Member FDIC",
]))

add("bank_proof_fail_intuit_generated.pdf", pdf([
    "QuickBooks - Intuit Inc.",
    "Direct Deposit Account Summary",
    "ACME MANUFACTURING LLC",
    "Routing 000000518   Account 00000149772",
    "Generated by QuickBooks Online - Intuit trademark",
]))

add("bank_proof_warn_numbers_cut_off.pdf", pdf([
    "FIRST SPRINGFIELD BANK",
    "ACME MANUFACTURING LLC",
    "VOID",
    "Routing ****     Account ****",
]))


# ---------- time_off_accruals ----------
add("pto_pass.csv",
    "Employee,PolicyName,AccruedHours,UsedHours,BalanceHours,AsOfDate\n"
    + "".join("%s,Vacation,80.00,24.00,56.00,2026-07-20\n" % e[0] for e in EMPLOYEES))

add("pto_warn_stale_asof.csv",
    "Employee,PolicyName,AccruedHours,UsedHours,BalanceHours,AsOfDate\n"
    + "".join("%s,Vacation,40.00,8.00,32.00,2026-01-31\n" % e[0] for e in EMPLOYEES))


# ---------- tax_setup ----------
add("tax_setup_pass.csv",
    "Jurisdiction,AccountNumber,Rate,EffectiveDate\n"
    "Federal EIN,00-1234567,,2019-09-09\n"
    "IL Withholding,00000-0000-0,4.95%,2019-09-09\n"
    "IL SUI,0000-0000-0,3.125%,2026-01-01\n")

add("tax_setup_warn_ids_on_file.csv",
    "Jurisdiction,AccountNumber,Rate,EffectiveDate\n"
    "Federal EIN,ON FILE,,2019-09-09\n"
    "IL Withholding,ON FILE,4.95%,2019-09-09\n"
    "IL SUI,ON FILE,3.125%,2026-01-01\n")


# ---------- common checks ----------
add("common_fail_wrong_doctype.pdf", pdf([
    "Employee Earnings Record - Year to Date",
    "Range: 01/01/2026 through 06/19/2026",
    "(submitted where a payroll register was requested)",
] + ["  %s  YTD Gross 15,692.28" % e[0] for e in EMPLOYEES]))

add("common_warn_truncated.pdf", pdf([
    "Payroll Journal - Acme Manufacturing LLC",
    "Check Date: 04/10/2026",
    "  Avery Nolan  Gross 2,615.38",
    "--- page 1 of 6 --- REMAINING PAGES MISSING ---",
]))


def main():
    ap = argparse.ArgumentParser(description="Generate ADA validation fixtures")
    ap.add_argument("--out", default=os.path.join(os.path.dirname(__file__), "fixtures"))
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    for name, data in sorted(FIXTURES.items()):
        blob = data.encode("utf-8") if isinstance(data, str) else data
        with open(os.path.join(a.out, name), "wb") as f:
            f.write(blob)
    print("wrote %d fixtures to %s" % (len(FIXTURES), a.out))


if __name__ == "__main__":
    main()
