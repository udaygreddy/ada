#!/usr/bin/env python3
"""
make_fixtures.py — generate the ADA validation test corpus.

One folder per test case (`tests/cases/<descriptive-case-name>/`), each holding
the document(s) a client would actually drop for that scenario. Filenames look
like real payroll/accounting exports — NOT like test case names.

That is deliberate. If a fixture were called `register_fail_q1.pdf`, the model
could "judge" it from the filename without reading a thing. Realistic names
force the judgment to come from content, which is what we're actually testing.
The folder name describes the scenario for human navigation (e.g.
`payroll-register-prior-quarter`) but never states the verdict — no
pass/fail/warn/good/bad in any folder name. Expected verdicts live only in
TEST-CASES.md.

All data is SYNTHETIC. SSNs use the 000- range the SSA never issues; EINs,
account and routing numbers are invented; emails use example.com.

Usage:
  python3 tests/make_fixtures.py [--out tests/cases]
"""
import argparse
import os
import shutil
import zlib

# Reference date the corpus is built around: 2026-07-20 (mid-late July).
# Per ADP's quarterly timing that makes Q2 2026 the required quarter and Q1 2026
# the acceptable fallback — so Q2 documents pass the quarter checks and
# Q1-only documents fail them.
Q2_CHECK_DATES = ["04/10/2026", "04/24/2026", "05/08/2026", "05/22/2026",
                  "06/05/2026", "06/19/2026"]
Q1_CHECK_DATES = ["01/09/2026", "01/23/2026", "02/06/2026", "02/20/2026",
                  "03/06/2026", "03/20/2026"]


PAGE_W, PAGE_H = 612, 792          # US Letter, in points
MARGIN_X, TOP_Y, LINE_H = 50, 742, 14
MAX_LINES = int((TOP_Y - 50) / LINE_H)


def _assemble(objs):
    """Assemble numbered objects into a structurally valid PDF.

    Real viewers (Preview, Adobe, Chrome) need more than the objects: a cross-
    reference table with exact byte offsets, a trailer naming the catalog, and
    a startxref pointer. Without them the file opens in nothing — even though a
    stream-scanning extractor can still read it.
    """
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, body in enumerate(objs, start=1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % i + body + b"\nendobj\n"
    xref_at = len(out)
    out += b"xref\n0 %d\n" % (len(objs) + 1)
    out += b"0000000000 65535 f \n"
    for off in offsets:
        out += b"%010d 00000 n \n" % off
    out += (b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n"
            % (len(objs) + 1, xref_at))
    return bytes(out)


def _content_obj(stream, compress):
    data = zlib.compress(stream) if compress else stream
    filt = b"/Filter /FlateDecode " if compress else b""
    return (b"<< " + filt + b"/Length " + str(len(data)).encode() + b" >>\n"
            b"stream\n" + data + b"\nendstream")


def _esc(s):
    return s.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")


def pdf(lines, compress=True):
    """One-page PDF with real, positioned text — opens in any PDF viewer."""
    if len(lines) > MAX_LINES:
        raise ValueError("%d lines overflows one page (max %d)"
                         % (len(lines), MAX_LINES))
    ops = ["BT", "/F1 10 Tf", "%d %d Td" % (MARGIN_X, TOP_Y)]
    for n, line in enumerate(lines):
        if n:
            ops.append("0 -%d Td" % LINE_H)
        ops.append("(%s) Tj" % _esc(line))
    ops.append("ET")
    cs = "\n".join(ops).encode("latin-1", "replace")
    return _assemble([
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 %d %d] /Contents 4 0 R "
        b"/Resources << /Font << /F1 5 0 R >> >> >>" % (PAGE_W, PAGE_H),
        _content_obj(cs, compress),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ])


def scanned_pdf():
    """Valid page carrying no text operators — stands in for an image-only scan.

    Opens and renders (a grey block, like a scan) but yields zero extractable
    text, which is the condition the scanned-document cases exercise.
    """
    cs = (b"q 0.93 g %d %d %d %d re f Q"
          % (MARGIN_X, 60, PAGE_W - 2 * MARGIN_X, PAGE_H - 120))
    return _assemble([
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 %d %d] /Contents 4 0 R "
        b"/Resources << >> >>" % (PAGE_W, PAGE_H),
        _content_obj(cs, True),
    ])


EMPLOYEES = [
    ("Avery Nolan",  "000-11-2001", "1988-03-14", "2021-06-01", "68000.00", "avery@example.com"),
    ("Blair Ozanne", "000-11-2002", "1992-11-02", "2022-01-18", "54500.00", "blair@example.com"),
    ("Casey Pruitt", "000-11-2003", "1979-07-27", "2019-09-09", "81250.00", "casey@example.com"),
    ("Devon Quill",  "000-11-2004", "1995-02-05", "2023-04-24", "47000.00", "devon@example.com"),
]
TERMINATED = [
    ("Emery Ruiz",   "000-11-2005", "1990-08-30", "2020-02-10", "59000.00", "emery@example.com"),
]

MF_HEAD = "Name,SSN,DateOfBirth,HireDate,AnnualRate,HomeAddress,Email,Status\n"


def mf_row(e, status, ssn=None):
    return "%s,%s,%s,%s,%s,\"120 Main St, Springfield IL\",%s,%s\n" % (
        e[0], ssn or e[1], e[2], e[3], e[4], e[5], status)


def masterfile(ssn_fmt=None, include_terminated=True):
    def s(e):
        return ssn_fmt(e) if ssn_fmt else e[1]
    out = MF_HEAD + "".join(mf_row(e, "Active", s(e)) for e in EMPLOYEES)
    if include_terminated:
        out += "".join(mf_row(e, "Terminated", s(e)) for e in TERMINATED)
    return out


def register(dates, title="Payroll Journal", print_date="07/20/2026"):
    lines = ["%s - Acme Manufacturing LLC" % title, "EIN 00-1234567"]
    for d in dates:
        lines.append("Check Date: %s" % d)
        for e in EMPLOYEES:
            lines.append("  %s  %s  Gross 2,615.38  Net 1,942.771" % (e[0], e[1]))
        lines.append("  Period Total  Gross 10,461.52")
    if print_date:                       # print-date trap: outside the quarter
        lines.append("Report generated on %s" % print_date)
    return pdf(lines)


def earnings_record(start, end, label="Year to Date", ytd=True):
    lines = ["Employee Earnings Record - %s" % label,
             "Range: %s through %s" % (start, end),
             "Acme Manufacturing LLC"]
    for e in EMPLOYEES:
        pre = "YTD " if ytd else ""
        lines.append("  %s  %s  %sGross 15,692.28  %sFed WH 2,041.00"
                     % (e[0], e[1], pre, pre))
    return pdf(lines)


def form_941(year, quarter, months, ended, note=None):
    lines = ["Form 941 for %d: Employer's QUARTERLY Federal Tax Return" % year,
             "Report for this quarter: %d (%s)" % (quarter, months),
             "EIN 00-1234567  Acme Manufacturing LLC",
             ended]
    if note:
        lines.append(note)
    lines += ["5a Taxable social security wages  62,769.12",
              "12 Total taxes after adjustments  14,204.88"]
    return pdf(lines)


def deposits(year, quarter, dates):
    return pdf(["Statement of Filings and Deposits",
                "Year %d  Quarter %d" % (year, quarter)]
               + ["Deposit  %s  Federal 941  3,551.22  Status: Paid" % d for d in dates])


def pto(asof, accrued, used, balance):
    return ("Employee,PolicyName,AccruedHours,UsedHours,BalanceHours,AsOfDate\n"
            + "".join("%s,Vacation,%s,%s,%s,%s\n" % (e[0], accrued, used, balance, asof)
                      for e in EMPLOYEES))


# Each case: folder id -> {realistic filename: bytes/str}.
# Expected verdicts live in TEST-CASES.md, never here.
CASES = {
    # ---- common checks ----
    "common-doctype-and-period-match": {"PayrollJournal_04012026-06302026.pdf": register(Q2_CHECK_DATES)},
    "common-wrong-document-type": {"EmployeeEarningsRecord_01012026-06192026.pdf":
           earnings_record("01/01/2026", "06/19/2026")},
    "common-truncated-pages": {"PayrollJournal_04102026.pdf": pdf([
        "Payroll Journal - Acme Manufacturing LLC",
        "Check Date: 04/10/2026",
        "  Avery Nolan  000-11-2001  Gross 2,615.38",
        "--- page 1 of 6 --- REMAINING PAGES MISSING ---"])},
    "common-scanned-image": {"PayrollJournal_2026Q2.pdf": scanned_pdf()},

    # ---- employee_masterfile ----
    "employee-masterfile-complete": {"Employee_Master_File_20260720.csv": masterfile()},
    "employee-masterfile-masked-ssn": {"Master_Control_by_Date_Range_20260720.csv":
           masterfile(ssn_fmt=lambda e: "XXX-XX-" + e[1][-4:])},
    "employee-masterfile-missing-ssn-column": {"EmployeeDetails.csv":
           "Name,DateOfBirth,HireDate,AnnualRate,Status\n"
           + "".join("%s,%s,%s,%s,Active\n" % (e[0], e[2], e[3], e[4]) for e in EMPLOYEES)},
    "employee-masterfile-actives-only": {"Employee_Census_20260720.csv": masterfile(include_terminated=False)},
    "employee-masterfile-minimal-fields": {"Employee_List.csv":
           "Name,SSN,Status\n"
           + "".join("%s,%s,Active\n" % (e[0], e[1]) for e in EMPLOYEES)
           + "".join("%s,%s,Terminated\n" % (e[0], e[1]) for e in TERMINATED)},

    # ---- payroll_register ----
    "payroll-register-full-quarter": {"PayrollJournal_04012026-06302026.pdf": register(Q2_CHECK_DATES)},
    "payroll-register-prior-quarter": {"PayrollJournal_01012026-03312026.pdf": register(Q1_CHECK_DATES)},
    "payroll-register-single-check-date": {"Payroll_Register_Summary_PXP_05082026.pdf":
           register(["05/08/2026"], title="Payroll Register Summary")},
    "payroll-register-combined-range": {"Payroll_Register_Summary_ProcessDateRange.pdf": pdf([
        "Payroll Register Summary - Process Date Range",
        "Range: 04/01/2026 through 06/30/2026",
        "Combined multi-payroll export (6 payrolls in one file)",
        "Total Gross 62,769.12"])},
    "payroll-register-scanned-image": {"Payroll_Journal_2026Q2.pdf": scanned_pdf()},

    # ---- ytd_balances ----
    "ytd-balances-full-year": {"EmployeeEarningsRecord_01012026-06192026.pdf":
           earnings_record("01/01/2026", "06/19/2026")},
    "ytd-balances-quarter-only": {"EmployeeEarningsRecord_04012026-06192026.pdf":
           earnings_record("04/01/2026", "06/19/2026", label="Quarter", ytd=False)},
    "ytd-balances-stale-end-date": {"EmployeeEarningsRecord_01012026-03202026.pdf":
           earnings_record("01/01/2026", "03/20/2026")},

    # ---- w2 ----
    "w2-prior-year": {"W2_2025_Nolan_Avery.pdf": pdf([
        "2025 Form W-2 Wage and Tax Statement",
        "Employer: Acme Manufacturing LLC  EIN 00-1234567",
        "Employee: Avery Nolan  SSN 000-11-2001",
        "1 Wages, tips, other compensation  68,000.00",
        "2 Federal income tax withheld  8,432.00"])},
    "w2-two-years-old": {"W2_2023_Nolan_Avery.pdf": pdf([
        "2023 Form W-2 Wage and Tax Statement",
        "Employer: Acme Manufacturing LLC  EIN 00-1234567",
        "Employee: Avery Nolan  SSN 000-11-2001",
        "1 Wages, tips, other compensation  61,500.00"])},

    # ---- tax_return ----
    "tax-return-941-q2": {"Form941_2026Q2.pdf":
           form_941(2026, 2, "April, May, June", "Quarter ended 06/30/2026")},
    "tax-return-941-in-progress-quarter": {"Form941_2026Q3.pdf":
           form_941(2026, 3, "July, August, September",
                    "Quarter ending 09/30/2026",
                    note="IN PROGRESS - quarter not ended, not yet filed")},
    "tax-return-941-prior-year-quarter": {"Form941_2025Q3.pdf":
           form_941(2025, 3, "July, August, September", "Quarter ended 09/30/2025")},
    "tax-return-state-sui-q2": {"IL_UI-3-40_2026Q2.pdf": pdf([
        "Illinois Department of Employment Security",
        "Quarterly Contribution and Wage Report (Form UI-3/40)",
        "Quarter: 2nd Quarter 2026  Period ending 06/30/2026",
        "Account 0000-0000-0  Acme Manufacturing LLC",
        "Total wages 62,769.12  Contribution due 1,224.00"])},
    "tax-return-941-standalone": {"Form941_2026Q2.pdf":
           form_941(2026, 2, "April, May, June", "Quarter ended 06/30/2026")},

    # ---- tax_deposit ----
    "tax-deposit-full-quarter": {"Statement_of_Filings_and_Deposits_2026Q2.pdf":
           deposits(2026, 2, Q2_CHECK_DATES)},
    "tax-deposit-prior-quarter": {"Statement_of_Filings_and_Deposits_2026Q1.pdf":
           deposits(2026, 1, Q1_CHECK_DATES)},

    # ---- bank_proof ----
    "bank-proof-voided-check": {"Voided_Check_FirstSpringfieldBank.pdf": pdf([
        "FIRST SPRINGFIELD BANK",
        "ACME MANUFACTURING LLC",
        "120 Main St, Springfield IL",
        "VOID  VOID  VOID",
        "Routing 000000518   Account 00000149772",
        "Member FDIC"])},
    "bank-proof-quickbooks-generated": {"Direct_Deposit_Account_Summary.pdf": pdf([
        "QuickBooks - Intuit Inc.",
        "Direct Deposit Account Summary",
        "ACME MANUFACTURING LLC",
        "Routing 000000518   Account 00000149772",
        "Generated by QuickBooks Online - Intuit trademark"])},
    "bank-proof-redacted-numbers": {"Voided_Check.pdf": pdf([
        "FIRST SPRINGFIELD BANK",
        "ACME MANUFACTURING LLC",
        "VOID",
        "Routing ****     Account ****"])},

    # ---- time_off_accruals ----
    "time-off-accruals-current": {"Time_Off_Balances_20260720.csv": pto("2026-07-20", "80.00", "24.00", "56.00")},
    "time-off-accruals-stale-asof": {"Time_Off_Balances_20260131.csv": pto("2026-01-31", "40.00", "8.00", "32.00")},

    # ---- tax_setup ----
    "tax-setup-ids-visible": {"Company_Tax_Setup.csv":
           "Jurisdiction,AccountNumber,Rate,EffectiveDate\n"
           "Federal EIN,00-1234567,,2019-09-09\n"
           "IL Withholding,00000-0000-0,4.95%,2019-09-09\n"
           "IL SUI,0000-0000-0,3.125%,2026-01-01\n"},
    "tax-setup-ids-on-file": {"Company_Tax_Setup_Export.csv":
           "Jurisdiction,AccountNumber,Rate,EffectiveDate\n"
           "Federal EIN,ON FILE,,2019-09-09\n"
           "IL Withholding,ON FILE,4.95%,2019-09-09\n"
           "IL SUI,ON FILE,3.125%,2026-01-01\n"},

    # ---- explicit constraints stated in the ADP request ----
    # Fine by the standing rules in validations.yaml; they violate only what ADP
    # wrote in this client's request. Nothing in the file betrays that — the
    # constraint lives on the requirement, not in the document.
    "explicit-format-csv-when-pdf-required": {
        "Payroll_Register_Q2_2026.csv":
            "employee,check_date,gross,net\n"
            + "".join("%s,%s,2615.38,1942.77\n" % (e[0], d)
                      for d in Q2_CHECK_DATES for e in EMPLOYEES)},
    "explicit-combined-when-per-date-required": {
        "Payroll_Register_Q2_2026_AllChecks.pdf": register(
            Q2_CHECK_DATES, title="Payroll Register Summary - All Check Dates")},
    "explicit-daterange-narrower-than-supplied": {
        "EmployeeEarningsRecord_01012026-06192026.pdf":
            earnings_record("01/01/2026", "06/19/2026")},

    # ---- coverage (cross-document; folder = the whole approved set) ----
    "coverage-register-full-quarter": {"PayrollJournal_04012026-06302026.pdf": register(Q2_CHECK_DATES)},
    "coverage-register-single-date": {"Payroll_Register_Summary_PXP_05082026.pdf":
           register(["05/08/2026"], title="Payroll Register Summary")},
    "coverage-941-standalone": {"Form941_2026Q2.pdf":
           form_941(2026, 2, "April, May, June", "Quarter ended 06/30/2026")},
    "coverage-missing-dd-routing": {"Employee_Master_File_20260720.csv": masterfile(),
           "PayrollJournal_04012026-06302026.pdf": register(Q2_CHECK_DATES)},
    "coverage-missing-garnishment-order": {"PayrollJournal_04012026-06302026.pdf": register(Q2_CHECK_DATES),
           "Employee_Master_File_20260720.csv": masterfile()},
    "coverage-missing-ia-ben": {"Form941_2026Q2.pdf":
           form_941(2026, 2, "April, May, June", "Quarter ended 06/30/2026"),
           "IA_65-5300_2026Q2.pdf": pdf([
               "Iowa Workforce Development",
               "Employer's Contribution and Payroll Report",
               "Quarter: 2nd Quarter 2026  Period ending 06/30/2026",
               "Account 000000-0  Acme Manufacturing LLC",
               "Total wages 62,769.12"])},
}


def main():
    ap = argparse.ArgumentParser(description="Generate ADA validation test cases")
    ap.add_argument("--out", default=os.path.join(os.path.dirname(__file__), "cases"))
    ap.add_argument("--clean", action="store_true",
                    help="remove existing case folders first")
    a = ap.parse_args()

    if a.clean and os.path.isdir(a.out):
        shutil.rmtree(a.out)
    files = 0
    for case, docs in sorted(CASES.items()):
        d = os.path.join(a.out, case)
        os.makedirs(d, exist_ok=True)
        for name, data in docs.items():
            blob = data.encode("utf-8") if isinstance(data, str) else data
            with open(os.path.join(d, name), "wb") as f:
                f.write(blob)
            files += 1
    print("wrote %d files across %d case folders in %s" % (files, len(CASES), a.out))


if __name__ == "__main__":
    main()
