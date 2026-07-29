#!/usr/bin/env python3
"""
make_prompts.py — sample client messages for each validation test case.

Every test case needs an input that reads like something a real client would
type into Claude/Copilot with the skill installed. These prompts carry exactly
what Phase 0 and Phase A need — company name, the ADP request, the payroll
provider, the drop folder, and the reference date — and nothing else.

Deliberately answer-free: a prompt never says whether the document is good or
bad. That's the same principle as the realistic filenames and neutral folder
names — the skill has to judge from content. Expected verdicts live in
TEST-CASES.md.

Usage:
  python3 tests/make_prompts.py                 # write tests/PROMPTS.md
  python3 tests/make_prompts.py <case-name>     # print one prompt, paths resolved
  python3 tests/make_prompts.py --list          # list case names
"""
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CASES_DIR = os.path.join(REPO, "tests", "cases")

# The corpus is built around this date — Q2 2026 required, Q1 2026 fallback.
REF = "2026-07-20"

# Shared client context. Individual prompts add only what their case needs.
CO = "Acme Manufacturing LLC"

# case -> (one-line purpose for the doc, prompt body).
# {folder} is replaced with the absolute case-folder path.
PROMPTS = {
  # ---------- common ----------
  "common-doctype-and-period-match": ("register requested, register supplied", """\
We're moving payroll from Paychex to ADP. Company name is {co}.

ADP's request says: "Payroll journal for last quarter."

I exported it here: {folder}
Today's date is {ref}. Can you check it's what they asked for before I send it?"""),

  "common-wrong-document-type": ("register requested, YTD supplied", """\
Switching from Paychex to ADP. We're {co}.

ADP asked for: "Payroll journal for last quarter."

Here's what I pulled: {folder}
Today is {ref}. Does this cover it?"""),

  "common-truncated-pages": ("register requested, partial export", """\
{co} here, switching payroll from Paychex to ADP.

ADP wants the payroll journal for last quarter.

Export is in {folder}
Today is {ref}. Please check it before I upload."""),

  "common-scanned-image": ("register requested, image-only scan", """\
We're {co}, moving from Paychex to ADP.

ADP asked for last quarter's payroll journal. Ours came through as a scan —
file is at {folder}

Today is {ref}. Can you confirm it's usable?"""),

  # ---------- employee_masterfile ----------
  "employee-masterfile-complete": ("full masterfile", """\
{co}, switching from Paychex to ADP.

ADP's list includes: "Employee master file — names, SSNs, DOB, hire dates, pay rates."

File is here: {folder}
Today is {ref}. We have 4 active employees plus one who left this year."""),

  "employee-masterfile-masked-ssn": ("Paylocity export, SSNs masked at source", """\
We're {co}, moving payroll from Paylocity to ADP.

ADP asked for the employee master file with full SSNs.

I ran Master Control by Date Range — it's in {folder}
Today is {ref}. Is this what they need?"""),

  "employee-masterfile-missing-ssn-column": ("QuickBooks export, no SSN field", """\
{co} here. Switching to ADP; our payroll data is in QuickBooks.

ADP wants the employee details with SSNs and dates of birth.

Export: {folder}
Today is {ref}."""),

  "employee-masterfile-actives-only": ("census, actives only", """\
We're {co}, leaving Paychex for ADP.

ADP asked for an employee census covering everyone we've paid this year.

Here it is: {folder}
Today is {ref}. We have 4 active employees, and one person left in March."""),

  "employee-masterfile-minimal-fields": ("bare employee list", """\
{co}, switching from Paychex to ADP.

ADP requested the employee master file — they listed name, SSN, date of birth,
hire date, pay rate and home address.

What I could export is in {folder}
Today is {ref}."""),

  # ---------- payroll_register ----------
  "payroll-register-full-quarter": ("full-quarter register", """\
{co} moving from Paychex to ADP.

ADP asked for: "Payroll registers for last quarter."

Export: {folder}
Today is {ref}. We run biweekly, most recent check date was 06/19/2026."""),

  "payroll-register-prior-quarter": ("register from the wrong quarter", """\
We're {co}, switching from Paychex to ADP.

ADP wants the payroll register for last quarter.

I pulled this: {folder}
Today is {ref}. Biweekly payroll, last check date 06/19/2026."""),

  "payroll-register-single-check-date": ("single check-date export", """\
{co}, moving from Paylocity to ADP.

ADP asked for payroll registers by check date. Paylocity makes you export one
per date — here's the first: {folder}

Today is {ref}. Biweekly, first check of the quarter was 04/10/2026."""),

  "payroll-register-combined-range": ("combined multi-payroll range", """\
We're {co}, leaving Paylocity for ADP.

ADP asked for payroll registers for last quarter, by check date.

I exported it as one file: {folder}
Today is {ref}. Biweekly payroll."""),

  "payroll-register-scanned-image": ("register as a scan", """\
{co} here, switching from Paychex to ADP.

ADP needs last quarter's payroll register. This is what we have: {folder}

Today is {ref}."""),

  # ---------- ytd_balances ----------
  "ytd-balances-full-year": ("YTD Jan 1 → last check", """\
{co}, moving from Paychex to ADP mid-year.

ADP asked for year-to-date payroll totals through our most recent payroll.

File: {folder}
Today is {ref}. Our last check date was 06/19/2026."""),

  "ytd-balances-quarter-only": ("quarter range where YTD was asked", """\
We're {co}, switching to ADP from Paychex.

ADP wants our YTD payroll totals for the year so far.

Here's the export: {folder}
Today is {ref}. Last payroll was 06/19/2026."""),

  "ytd-balances-stale-end-date": ("YTD ending too early", """\
{co} switching from Paychex to ADP.

ADP asked for year-to-date totals through our latest payroll.

Export: {folder}
Today is {ref}. Most recent check date was 06/19/2026."""),

  # ---------- w2 ----------
  "w2-prior-year": ("prior-year W-2", """\
We're {co}, moving to ADP.

ADP asked for prior-year W-2s.

Sample here: {folder}
Today is {ref}."""),

  "w2-two-years-old": ("older W-2", """\
{co} here, switching payroll to ADP.

ADP requested prior-year W-2s for our employees.

This is what I found: {folder}
Today is {ref}."""),

  # ---------- tax_return ----------
  "tax-return-941-q2": ("941 for the required quarter", """\
{co}, switching from Paychex to ADP.

ADP asked for our most recent quarterly federal tax return (941).

File: {folder}
Today is {ref}. We're based in Illinois."""),

  "tax-return-941-in-progress-quarter": ("941 for an unfinished quarter", """\
We're {co}, moving to ADP from Paychex.

ADP wants the most recent 941.

Here's what I grabbed: {folder}
Today is {ref}. Illinois."""),

  "tax-return-941-prior-year-quarter": ("941 from a year ago", """\
{co} switching to ADP.

ADP asked for the most recent quarterly 941 filing.

File: {folder}
Today is {ref}. We're in Illinois."""),

  "tax-return-state-sui-q2": ("state SUI filing", """\
{co}, moving from Paychex to ADP.

ADP asked for state unemployment (SUI) filings to go with our 941.

Illinois filing: {folder}
Today is {ref}."""),

  "tax-return-941-standalone": ("941 with no state filing alongside", """\
We're {co} in Illinois, switching to ADP.

ADP asked for our quarterly tax filings.

I've uploaded what I have: {folder}
Today is {ref}. Is this everything they need before I send it?"""),

  # ---------- tax_deposit ----------
  "tax-deposit-full-quarter": ("deposits covering the quarter", """\
{co}, moving from Paylocity to ADP.

ADP asked for proof of tax deposits for last quarter.

File: {folder}
Today is {ref}. Biweekly payroll, last check 06/19/2026."""),

  "tax-deposit-prior-quarter": ("deposits from the wrong quarter", """\
We're {co}, switching from Paylocity to ADP.

ADP wants proof of our tax deposits for last quarter.

Here it is: {folder}
Today is {ref}. Biweekly; our Q2 registers are already approved."""),

  # ---------- bank_proof ----------
  "bank-proof-voided-check": ("bank-issued voided check", """\
{co}, setting up payroll with ADP.

ADP asked for a voided check or bank statement for our payroll account.

Here: {folder}
Today is {ref}."""),

  "bank-proof-quickbooks-generated": ("account summary from QuickBooks", """\
We're {co}, moving to ADP.

ADP needs bank account proof for direct deposit. I printed our account details.

File: {folder}
Today is {ref}. Will this work?"""),

  "bank-proof-redacted-numbers": ("voided check with hidden numbers", """\
{co} here, onboarding with ADP.

ADP asked for a voided check for the payroll account.

Uploaded: {folder}
Today is {ref}."""),

  # ---------- time_off_accruals ----------
  "time-off-accruals-current": ("current PTO balances", """\
{co}, moving from Paychex to ADP.

ADP asked for current PTO/time-off balances so they can carry them over.

Export: {folder}
Today is {ref}."""),

  "time-off-accruals-stale-asof": ("older PTO balances", """\
We're {co}, switching to ADP.

ADP wants our employees' current time-off balances.

Here's the report: {folder}
Today is {ref}."""),

  # ---------- tax_setup ----------
  "tax-setup-ids-visible": ("tax setup with account numbers", """\
{co}, switching from Paychex to ADP.

ADP asked for our tax setup — federal EIN plus state withholding and SUI
account numbers and rates.

File: {folder}
Today is {ref}. We're in Illinois."""),

  "tax-setup-ids-on-file": ("tax setup with hidden account numbers", """\
We're {co} in Illinois, moving to ADP.

ADP requested our company tax setup with the account numbers and rates.

Export: {folder}
Today is {ref}."""),

  # ---------- coverage (Phase B.5) ----------
  "coverage-register-full-quarter": ("registers covering every check date", """\
{co}, switching from Paychex to ADP.

ADP asked for payroll registers for every check date last quarter.

Everything I've got is in {folder}
Today is {ref}. Biweekly, first check of the quarter 04/10/2026, last 06/19/2026.
Is this everything they need before I send it?"""),

  "coverage-register-single-date": ("only one check date collected", """\
We're {co}, moving from Paylocity to ADP.

ADP wants payroll registers for each check date last quarter.

So far I've exported: {folder}
Today is {ref}. Biweekly, first check 04/10/2026, last 06/19/2026.
Is this everything they need before I send it?"""),

  "coverage-941-standalone": ("941 with no state filing", """\
{co} in Illinois, switching to ADP.

ADP asked for last quarter's tax filings.

Here's my folder: {folder}
Today is {ref}. Is this everything they need before I send it?"""),

  "coverage-missing-dd-routing": ("no routing info for direct deposit", """\
We're {co}, moving from Paychex to ADP.

ADP asked for employee data and payroll registers for last quarter. All our
employees are on direct deposit.

Folder: {folder}
Today is {ref}. Is this everything they need before I send it?"""),

  "coverage-missing-garnishment-order": ("garnishment in play, no court order", """\
{co}, switching from Paychex to ADP.

ADP asked for employee records and last quarter's payroll registers. One of our
employees has a child-support garnishment.

Folder: {folder}
Today is {ref}. Is this everything they need before I send it?"""),

  "coverage-missing-ia-ben": ("Iowa filings, BEN not shown", """\
We're {co}, based in Iowa, switching to ADP.

ADP asked for last quarter's federal and state tax filings.

Folder: {folder}
Today is {ref}. Is this everything they need before I send it?"""),
}


def render(case):
    folder = os.path.join(CASES_DIR, case)
    purpose, body = PROMPTS[case]
    return body.format(co=CO, ref=REF, folder=folder)


def write_doc():
    out = [
        "# Sample prompts — one per validation test case",
        "",
        "Copy-paste inputs for driving each case through the skill in Claude,",
        "Copilot, or any host with `adp-discovery` installed. Each reads like a",
        "message a real client would send and carries what Phase 0/A need:",
        "company name, the ADP request, the payroll provider, the drop folder,",
        "and the reference date.",
        "",
        "**Prompts never state the expected verdict** — same reason filenames and",
        "folder names don't. Look up what should happen in",
        "[`TEST-CASES.md`](TEST-CASES.md) *after* you see the skill's answer.",
        "",
        "The corpus assumes **today is 2026-07-20** (Q2 2026 required, Q1 fallback),",
        "so each prompt states the date. Change it and the expected quarters shift.",
        "",
        "Regenerate with `python3 tests/make_prompts.py`, or print one case:",
        "",
        "```sh",
        "python3 tests/make_prompts.py payroll-register-prior-quarter",
        "```",
        "",
        "Paths below are absolute for this checkout; the helper above resolves them",
        "for wherever you cloned it.",
        "",
        "---",
        "",
    ]
    for case in sorted(PROMPTS):
        purpose, _ = PROMPTS[case]
        out += ["## `%s`" % case, "", "_%s_" % purpose, "", "```text",
                render(case), "```", ""]
    path = os.path.join(REPO, "tests", "PROMPTS.md")
    with open(path, "w") as f:
        f.write("\n".join(out))
    return path, len(PROMPTS)


def main():
    args = sys.argv[1:]
    if args and args[0] == "--list":
        for c in sorted(PROMPTS):
            print(c)
        return
    if args:
        case = args[0]
        if case not in PROMPTS:
            sys.exit("unknown case: %s (try --list)" % case)
        print(render(case))
        return
    path, n = write_doc()
    missing = sorted(set(os.listdir(CASES_DIR)) - set(PROMPTS))
    extra = sorted(set(PROMPTS) - set(os.listdir(CASES_DIR)))
    print("wrote %s (%d prompts)" % (path, n))
    if missing:
        print("  WARNING: case folders with no prompt: %s" % ", ".join(missing))
    if extra:
        print("  WARNING: prompts with no case folder: %s" % ", ".join(extra))


if __name__ == "__main__":
    main()
