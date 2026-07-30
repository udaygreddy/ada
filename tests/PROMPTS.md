# Sample prompts — one per validation test case

Copy-paste inputs for driving each case through the skill in Claude,
Copilot, or any host with `adp-discovery` installed. Each reads like a
message a real client would send and carries what Phase 0/A need:
company name, the ADP request, the payroll provider, the drop folder,
and the reference date.

**Prompts never state the expected verdict** — same reason filenames and
folder names don't. Look up what should happen in
[`TEST-CASES.md`](TEST-CASES.md) *after* you see the skill's answer.

The corpus assumes **today is 2026-07-20** (Q2 2026 required, Q1 fallback),
so each prompt states the date. Change it and the expected quarters shift.

Regenerate with `python3 tests/make_prompts.py`, or print one case:

```sh
python3 tests/make_prompts.py payroll-register-prior-quarter
```

Paths below are absolute for this checkout; the helper above resolves them
for wherever you cloned it.

---

## `bank-proof-quickbooks-generated`

_account summary from QuickBooks_

```text
We're Acme Manufacturing LLC, moving to ADP.

ADP needs bank account proof for direct deposit. I printed our account details.

File: /Users/udayg/Documents/projects/ADA/tests/cases/bank-proof-quickbooks-generated
Today is 2026-07-20. Will this work?
```

## `bank-proof-redacted-numbers`

_voided check with hidden numbers_

```text
Acme Manufacturing LLC here, onboarding with ADP.

ADP asked for a voided check for the payroll account.

Uploaded: /Users/udayg/Documents/projects/ADA/tests/cases/bank-proof-redacted-numbers
Today is 2026-07-20.
```

## `bank-proof-voided-check`

_bank-issued voided check_

```text
Acme Manufacturing LLC, setting up payroll with ADP.

ADP asked for a voided check or bank statement for our payroll account.

Here: /Users/udayg/Documents/projects/ADA/tests/cases/bank-proof-voided-check
Today is 2026-07-20.
```

## `common-doctype-and-period-match`

_register requested, register supplied_

```text
We're moving payroll from Paychex to ADP. Company name is Acme Manufacturing LLC.

ADP's request says: "Payroll journal for last quarter."

I exported it here: /Users/udayg/Documents/projects/ADA/tests/cases/common-doctype-and-period-match
Today's date is 2026-07-20. Can you check it's what they asked for before I send it?
```

## `common-scanned-image`

_register requested, image-only scan_

```text
We're Acme Manufacturing LLC, moving from Paychex to ADP.

ADP asked for last quarter's payroll journal. Ours came through as a scan —
file is at /Users/udayg/Documents/projects/ADA/tests/cases/common-scanned-image

Today is 2026-07-20. Can you confirm it's usable?
```

## `common-truncated-pages`

_register requested, partial export_

```text
Acme Manufacturing LLC here, switching payroll from Paychex to ADP.

ADP wants the payroll journal for last quarter.

Export is in /Users/udayg/Documents/projects/ADA/tests/cases/common-truncated-pages
Today is 2026-07-20. Please check it before I upload.
```

## `common-wrong-document-type`

_register requested, YTD supplied_

```text
Switching from Paychex to ADP. We're Acme Manufacturing LLC.

ADP asked for: "Payroll journal for last quarter."

Here's what I pulled: /Users/udayg/Documents/projects/ADA/tests/cases/common-wrong-document-type
Today is 2026-07-20. Does this cover it?
```

## `coverage-941-standalone`

_941 with no state filing_

```text
Acme Manufacturing LLC in Illinois, switching to ADP.

ADP asked for last quarter's tax filings.

Here's my folder: /Users/udayg/Documents/projects/ADA/tests/cases/coverage-941-standalone
Today is 2026-07-20. Is this everything they need before I send it?
```

## `coverage-missing-dd-routing`

_no routing info for direct deposit_

```text
We're Acme Manufacturing LLC, moving from Paychex to ADP.

ADP asked for employee data and payroll registers for last quarter. All our
employees are on direct deposit.

Folder: /Users/udayg/Documents/projects/ADA/tests/cases/coverage-missing-dd-routing
Today is 2026-07-20. Is this everything they need before I send it?
```

## `coverage-missing-garnishment-order`

_garnishment in play, no court order_

```text
Acme Manufacturing LLC, switching from Paychex to ADP.

ADP asked for employee records and last quarter's payroll registers. One of our
employees has a child-support garnishment.

Folder: /Users/udayg/Documents/projects/ADA/tests/cases/coverage-missing-garnishment-order
Today is 2026-07-20. Is this everything they need before I send it?
```

## `coverage-missing-ia-ben`

_Iowa filings, BEN not shown_

```text
We're Acme Manufacturing LLC, based in Iowa, switching to ADP.

ADP asked for last quarter's federal and state tax filings.

Folder: /Users/udayg/Documents/projects/ADA/tests/cases/coverage-missing-ia-ben
Today is 2026-07-20. Is this everything they need before I send it?
```

## `coverage-register-full-quarter`

_registers covering every check date_

```text
Acme Manufacturing LLC, switching from Paychex to ADP.

ADP asked for payroll registers for every check date last quarter.

Everything I've got is in /Users/udayg/Documents/projects/ADA/tests/cases/coverage-register-full-quarter
Today is 2026-07-20. Biweekly, first check of the quarter 04/10/2026, last 06/19/2026.
Is this everything they need before I send it?
```

## `coverage-register-single-date`

_only one check date collected_

```text
We're Acme Manufacturing LLC, moving from Paylocity to ADP.

ADP wants payroll registers for each check date last quarter.

So far I've exported: /Users/udayg/Documents/projects/ADA/tests/cases/coverage-register-single-date
Today is 2026-07-20. Biweekly, first check 04/10/2026, last 06/19/2026.
Is this everything they need before I send it?
```

## `employee-masterfile-actives-only`

_census, actives only_

```text
We're Acme Manufacturing LLC, leaving Paychex for ADP.

ADP asked for an employee census covering everyone we've paid this year.

Here it is: /Users/udayg/Documents/projects/ADA/tests/cases/employee-masterfile-actives-only
Today is 2026-07-20. We have 4 active employees, and one person left in March.
```

## `employee-masterfile-complete`

_full masterfile_

```text
Acme Manufacturing LLC, switching from Paychex to ADP.

ADP's list includes: "Employee master file — names, SSNs, DOB, hire dates, pay rates."

File is here: /Users/udayg/Documents/projects/ADA/tests/cases/employee-masterfile-complete
Today is 2026-07-20. We have 4 active employees plus one who left this year.
```

## `employee-masterfile-masked-ssn`

_Paylocity export, SSNs masked at source_

```text
We're Acme Manufacturing LLC, moving payroll from Paylocity to ADP.

ADP asked for the employee master file with full SSNs.

I ran Master Control by Date Range — it's in /Users/udayg/Documents/projects/ADA/tests/cases/employee-masterfile-masked-ssn
Today is 2026-07-20. Is this what they need?
```

## `employee-masterfile-minimal-fields`

_bare employee list_

```text
Acme Manufacturing LLC, switching from Paychex to ADP.

ADP requested the employee master file — they listed name, SSN, date of birth,
hire date, pay rate and home address.

What I could export is in /Users/udayg/Documents/projects/ADA/tests/cases/employee-masterfile-minimal-fields
Today is 2026-07-20.
```

## `employee-masterfile-missing-ssn-column`

_QuickBooks export, no SSN field_

```text
Acme Manufacturing LLC here. Switching to ADP; our payroll data is in QuickBooks.

ADP wants the employee details with SSNs and dates of birth.

Export: /Users/udayg/Documents/projects/ADA/tests/cases/employee-masterfile-missing-ssn-column
Today is 2026-07-20.
```

## `explicit-combined-when-per-date-required`

_ADP said one file per check date; client combined_

```text
We're Acme Manufacturing LLC, moving from Paylocity to ADP.

ADP wrote:
  "Payroll registers for last quarter — one file per check date, please do
   not combine them into a single report."

My export is here: /Users/udayg/Documents/projects/ADA/tests/cases/explicit-combined-when-per-date-required
Today is 2026-07-20. Biweekly, first check 04/10/2026, last 06/19/2026.
```

## `explicit-daterange-narrower-than-supplied`

_ADP gave an explicit range; file is wider_

```text
Acme Manufacturing LLC here, switching from Paychex to ADP.

ADP's request states:
  "Employee earnings record covering 04/01/2026 through 06/30/2026."

File: /Users/udayg/Documents/projects/ADA/tests/cases/explicit-daterange-narrower-than-supplied
Today is 2026-07-20. Last payroll was 06/19/2026.
```

## `explicit-format-csv-when-pdf-required`

_ADP said PDF; client sent CSV_

```text
Acme Manufacturing LLC, switching from Paychex to ADP.

ADP's email says, word for word:
  "Payroll registers for last quarter. PDF format only, please — our
   intake system can't read spreadsheets."

Here's my export: /Users/udayg/Documents/projects/ADA/tests/cases/explicit-format-csv-when-pdf-required
Today is 2026-07-20. Biweekly payroll, last check 06/19/2026.
```

## `payroll-register-combined-range`

_combined multi-payroll range_

```text
We're Acme Manufacturing LLC, leaving Paylocity for ADP.

ADP asked for payroll registers for last quarter, by check date.

I exported it as one file: /Users/udayg/Documents/projects/ADA/tests/cases/payroll-register-combined-range
Today is 2026-07-20. Biweekly payroll.
```

## `payroll-register-full-quarter`

_full-quarter register_

```text
Acme Manufacturing LLC moving from Paychex to ADP.

ADP asked for: "Payroll registers for last quarter."

Export: /Users/udayg/Documents/projects/ADA/tests/cases/payroll-register-full-quarter
Today is 2026-07-20. We run biweekly, most recent check date was 06/19/2026.
```

## `payroll-register-prior-quarter`

_register from the wrong quarter_

```text
We're Acme Manufacturing LLC, switching from Paychex to ADP.

ADP wants the payroll register for last quarter.

I pulled this: /Users/udayg/Documents/projects/ADA/tests/cases/payroll-register-prior-quarter
Today is 2026-07-20. Biweekly payroll, last check date 06/19/2026.
```

## `payroll-register-scanned-image`

_register as a scan_

```text
Acme Manufacturing LLC here, switching from Paychex to ADP.

ADP needs last quarter's payroll register. This is what we have: /Users/udayg/Documents/projects/ADA/tests/cases/payroll-register-scanned-image

Today is 2026-07-20.
```

## `payroll-register-single-check-date`

_single check-date export_

```text
Acme Manufacturing LLC, moving from Paylocity to ADP.

ADP asked for payroll registers by check date. Paylocity makes you export one
per date — here's the first: /Users/udayg/Documents/projects/ADA/tests/cases/payroll-register-single-check-date

Today is 2026-07-20. Biweekly, first check of the quarter was 04/10/2026.
```

## `tax-deposit-full-quarter`

_deposits covering the quarter_

```text
Acme Manufacturing LLC, moving from Paylocity to ADP.

ADP asked for proof of tax deposits for last quarter.

File: /Users/udayg/Documents/projects/ADA/tests/cases/tax-deposit-full-quarter
Today is 2026-07-20. Biweekly payroll, last check 06/19/2026.
```

## `tax-deposit-prior-quarter`

_deposits from the wrong quarter_

```text
We're Acme Manufacturing LLC, switching from Paylocity to ADP.

ADP wants proof of our tax deposits for last quarter.

Here it is: /Users/udayg/Documents/projects/ADA/tests/cases/tax-deposit-prior-quarter
Today is 2026-07-20. Biweekly; our Q2 registers are already approved.
```

## `tax-return-941-in-progress-quarter`

_941 for an unfinished quarter_

```text
We're Acme Manufacturing LLC, moving to ADP from Paychex.

ADP wants the most recent 941.

Here's what I grabbed: /Users/udayg/Documents/projects/ADA/tests/cases/tax-return-941-in-progress-quarter
Today is 2026-07-20. Illinois.
```

## `tax-return-941-prior-year-quarter`

_941 from a year ago_

```text
Acme Manufacturing LLC switching to ADP.

ADP asked for the most recent quarterly 941 filing.

File: /Users/udayg/Documents/projects/ADA/tests/cases/tax-return-941-prior-year-quarter
Today is 2026-07-20. We're in Illinois.
```

## `tax-return-941-q2`

_941 for the required quarter_

```text
Acme Manufacturing LLC, switching from Paychex to ADP.

ADP asked for our most recent quarterly federal tax return (941).

File: /Users/udayg/Documents/projects/ADA/tests/cases/tax-return-941-q2
Today is 2026-07-20. We're based in Illinois.
```

## `tax-return-941-standalone`

_941 with no state filing alongside_

```text
We're Acme Manufacturing LLC in Illinois, switching to ADP.

ADP asked for our quarterly tax filings.

I've uploaded what I have: /Users/udayg/Documents/projects/ADA/tests/cases/tax-return-941-standalone
Today is 2026-07-20. Is this everything they need before I send it?
```

## `tax-return-state-sui-q2`

_state SUI filing_

```text
Acme Manufacturing LLC, moving from Paychex to ADP.

ADP asked for state unemployment (SUI) filings to go with our 941.

Illinois filing: /Users/udayg/Documents/projects/ADA/tests/cases/tax-return-state-sui-q2
Today is 2026-07-20.
```

## `tax-setup-ids-on-file`

_tax setup with hidden account numbers_

```text
We're Acme Manufacturing LLC in Illinois, moving to ADP.

ADP requested our company tax setup with the account numbers and rates.

Export: /Users/udayg/Documents/projects/ADA/tests/cases/tax-setup-ids-on-file
Today is 2026-07-20.
```

## `tax-setup-ids-visible`

_tax setup with account numbers_

```text
Acme Manufacturing LLC, switching from Paychex to ADP.

ADP asked for our tax setup — federal EIN plus state withholding and SUI
account numbers and rates.

File: /Users/udayg/Documents/projects/ADA/tests/cases/tax-setup-ids-visible
Today is 2026-07-20. We're in Illinois.
```

## `time-off-accruals-current`

_current PTO balances_

```text
Acme Manufacturing LLC, moving from Paychex to ADP.

ADP asked for current PTO/time-off balances so they can carry them over.

Export: /Users/udayg/Documents/projects/ADA/tests/cases/time-off-accruals-current
Today is 2026-07-20.
```

## `time-off-accruals-stale-asof`

_older PTO balances_

```text
We're Acme Manufacturing LLC, switching to ADP.

ADP wants our employees' current time-off balances.

Here's the report: /Users/udayg/Documents/projects/ADA/tests/cases/time-off-accruals-stale-asof
Today is 2026-07-20.
```

## `w2-prior-year`

_prior-year W-2_

```text
We're Acme Manufacturing LLC, moving to ADP.

ADP asked for prior-year W-2s.

Sample here: /Users/udayg/Documents/projects/ADA/tests/cases/w2-prior-year
Today is 2026-07-20.
```

## `w2-two-years-old`

_older W-2_

```text
Acme Manufacturing LLC here, switching payroll to ADP.

ADP requested prior-year W-2s for our employees.

This is what I found: /Users/udayg/Documents/projects/ADA/tests/cases/w2-two-years-old
Today is 2026-07-20.
```

## `ytd-balances-full-year`

_YTD Jan 1 → last check_

```text
Acme Manufacturing LLC, moving from Paychex to ADP mid-year.

ADP asked for year-to-date payroll totals through our most recent payroll.

File: /Users/udayg/Documents/projects/ADA/tests/cases/ytd-balances-full-year
Today is 2026-07-20. Our last check date was 06/19/2026.
```

## `ytd-balances-quarter-only`

_quarter range where YTD was asked_

```text
We're Acme Manufacturing LLC, switching to ADP from Paychex.

ADP wants our YTD payroll totals for the year so far.

Here's the export: /Users/udayg/Documents/projects/ADA/tests/cases/ytd-balances-quarter-only
Today is 2026-07-20. Last payroll was 06/19/2026.
```

## `ytd-balances-stale-end-date`

_YTD ending too early_

```text
Acme Manufacturing LLC switching from Paychex to ADP.

ADP asked for year-to-date totals through our latest payroll.

Export: /Users/udayg/Documents/projects/ADA/tests/cases/ytd-balances-stale-end-date
Today is 2026-07-20. Most recent check date was 06/19/2026.
```
