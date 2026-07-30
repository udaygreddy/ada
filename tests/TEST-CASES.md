# ADA validation test cases

Positive (should **pass**) and negative (should **warn** / **fail**) cases for
every document type in [`ada/validations.yaml`](../ada/validations.yaml).

Each case is a folder under `tests/cases/<descriptive-case-name>/` holding the
document(s) a client would actually drop for that scenario. **Filenames look
like real exports, never like test names**, and folder names describe the
scenario for navigation but never the verdict — so nothing in the corpus tells
you the answer. The skill has to judge from content, which is the whole point.
Expected verdicts live here and only here.

Because validation is **model-judged**, these aren't asserted by a script — the
Expect column is the verdict a correct judgment produces. Use them after a rules
change, a prompt change, or a model upgrade. (The code-enforced gates *are*
script-asserted — see [`run_gate_tests.sh`](run_gate_tests.sh).)

- **Generate:** `python3 tests/make_fixtures.py` → 42 folders, 45 files. All
  synthetic; SSNs use the SSA-invalid `000-` range, emails use `example.com`.
- **Reference date: `2026-07-20`.** Mid-late July, so per ADP's quarterly timing
  **Q2 2026 is required** and **Q1 2026 is the fallback**. Pass the same
  `--ref-date 2026-07-20` when reproducing, or the quarter expectations shift.
- **Intake facts** the cases assume:
  `payroll_frequency=biweekly`, `anchor_check_date=2026-04-10`,
  `last_check_date=2026-06-19`, `active_employee_count=4`,
  `states=[IL]`, `dd_enrolled=true`, `garnishments=false`.

## How to run one case — end to end, as a client would

Print the case's sample client message and paste it into a host with the skill
installed:

```sh
python3 tests/make_prompts.py payroll-register-prior-quarter
```

All 42 are in [`PROMPTS.md`](PROMPTS.md). They carry the company name, ADP
request, provider, drop folder and reference date — and never the expected
verdict, so you can run blind and check the Expect column afterwards.

## How to run one case — validation step only

```sh
python3 ada/scripts/validate.py --extract \
  --file tests/cases/payroll-register-prior-quarter/*.pdf \
  --expected-doc-type payroll_register \
  --expected-period "last quarter" --ref-date 2026-07-20
```

Then judge the extracted text against `common` + `doc_types.<doc_type>` checks
and compare with the expected verdict. Empty `text` (scanned) is not a free
pass — read the file natively and judge the same criteria.

To exercise a whole case folder as a drop folder (Phase A ingest), point
`enumerate.py` at `tests/cases/<descriptive-case-name>/`.

---

## common — applies to every document

| Case | Document | Scenario | Rule | Expect |
|---|---|---|---|---|
| `common-doctype-and-period-match` | `PayrollJournal_04012026-06302026.pdf` | Right type, right quarter | `matches-request` | **pass** |
| `common-wrong-document-type` | `EmployeeEarningsRecord_01012026-06192026.pdf` | YTD report submitted where a register was asked for | `matches-request` | **fail** |
| `common-truncated-pages` | `PayrollJournal_04102026.pdf` | "page 1 of 6 — remaining pages missing" | `legible-complete` | **warn** |
| `common-scanned-image` | `PayrollJournal_2026Q2.pdf` | Image-only scan → extraction empty | `legible-complete` | **read natively**, then judge; do not auto-pass |

> **The print-date trap (regression).** Every register fixture ends with
> `Report generated on 07/20/2026`, outside Q2. A correct judgment ignores it and
> reads the check dates → `common-doctype-and-period-match` **passes**. A naive
> min/max date span would call this a mismatch — the bug model judgment exists
> to avoid.

## employee_masterfile

| Case | Document | Scenario | Rule | Expect |
|---|---|---|---|---|
| `employee-masterfile-complete` | `Employee_Master_File_20260720.csv` | Full SSNs (→ `▮▮▮`), all fields, actives + terminated | all | **pass** |
| `employee-masterfile-masked-ssn` | `Master_Control_by_Date_Range_20260720.csv` | Source exported `XXX-XX-2001` | `ssn-unmasked` | **fail** + Paylocity/QBO unmask remediation |
| `employee-masterfile-missing-ssn-column` | `EmployeeDetails.csv` | No SSN column at all | `ssn-unmasked` | **fail** |
| `employee-masterfile-actives-only` | `Employee_Census_20260720.csv` | 4 actives, no terminated | `includes-terminated` | **warn** |
| `employee-masterfile-minimal-fields` | `Employee_List.csv` | Only name/SSN/status — no DOB, hire date, rate, address | `required-fields` | **warn** (name the missing columns) |

> `employee-masterfile-complete` vs `employee-masterfile-masked-ssn` is the core
> evidence distinction: `▮▮▮` means the value **was** present and ADA masked it
> (good); a literal `XXX-XX-####` means the **source export** was masked (bad).
> Verified: the complete case → 5 masks, no raw SSN; the masked-ssn case →
> `XXX-XX` survives, 0 masks.

## payroll_register

| Case | Document | Scenario | Rule | Expect |
|---|---|---|---|---|
| `payroll-register-full-quarter` | `PayrollJournal_04012026-06302026.pdf` | All 6 Q2 check dates | `covers-required-quarter` | **pass** |
| `payroll-register-prior-quarter` | `PayrollJournal_01012026-03312026.pdf` | Q1 dates only, Q2 required | `covers-required-quarter` | **fail** |
| `payroll-register-single-check-date` | `Payroll_Register_Summary_PXP_05082026.pdf` | One check date, single-day export | `single-day-exports` | **pass** |
| `payroll-register-combined-range` | `Payroll_Register_Summary_ProcessDateRange.pdf` | 04/01–06/30 combined multi-payroll range | `single-day-exports` | **warn** |
| `payroll-register-scanned-image` | `Payroll_Journal_2026Q2.pdf` | Image-only scan | `legible-complete` | read natively; **fail** if unreadable |

## ytd_balances

| Case | Document | Scenario | Rule | Expect |
|---|---|---|---|---|
| `ytd-balances-full-year` | `EmployeeEarningsRecord_01012026-06192026.pdf` | 01/01/2026 → 06/19/2026 (= `last_check_date`) | `range-jan1-to-last-check` | **pass** |
| `ytd-balances-quarter-only` | `EmployeeEarningsRecord_04012026-06192026.pdf` | 04/01 → 06/19 — quarter, not YTD | `range-jan1-to-last-check` | **fail** |
| `ytd-balances-stale-end-date` | `EmployeeEarningsRecord_01012026-03202026.pdf` | 01/01 → 03/20 — stale end date | `range-jan1-to-last-check` | **fail** |

## w2

| Case | Document | Scenario | Rule | Expect |
|---|---|---|---|---|
| `w2-prior-year` | `W2_2025_Nolan_Avery.pdf` | Prior year (2025) relative to 2026 | `prior-year` | **pass** |
| `w2-two-years-old` | `W2_2023_Nolan_Avery.pdf` | 2023 W-2 | `prior-year` | **fail** |

## tax_return

| Case | Document | Scenario | Rule | Expect |
|---|---|---|---|---|
| `tax-return-941-q2` | `Form941_2026Q2.pdf` | 941, Q2 2026, quarter ended | `quarter-required-and-finalized` | **pass** |
| `tax-return-941-in-progress-quarter` | `Form941_2026Q3.pdf` | Q3 2026 — quarter not ended | `quarter-required-and-finalized` | **fail** (never accept unfinalized) |
| `tax-return-941-prior-year-quarter` | `Form941_2025Q3.pdf` | Q3 2025 — outside required/fallback | `quarter-required-and-finalized` | **fail** |
| `tax-return-state-sui-q2` | `IL_UI-3-40_2026Q2.pdf` | IL SUI filing, same quarter | `state-sui-filing` (companion) | **pass** — satisfies the companion for `tax-return-941-q2` |
| `tax-return-941-standalone` | `Form941_2026Q2.pdf` (alone) | 941 with no state filing in the set | `state-filings-companion` (coverage) | **derived requirement** for the SUI filing |

## tax_deposit

| Case | Document | Scenario | Rule | Expect |
|---|---|---|---|---|
| `tax-deposit-full-quarter` | `Statement_of_Filings_and_Deposits_2026Q2.pdf` | Deposits across all 6 Q2 check dates | `covers-quarter` | **pass** |
| `tax-deposit-prior-quarter` | `Statement_of_Filings_and_Deposits_2026Q1.pdf` | Q1 deposits, Q2 registers approved | `covers-quarter` / `deposits-cover-quarter` | **warn** |

## bank_proof

| Case | Document | Scenario | Rule | Expect |
|---|---|---|---|---|
| `bank-proof-voided-check` | `Voided_Check_FirstSpringfieldBank.pdf` | Bank-issued voided check, routing + account present | `from-bank`, `usable` | **pass** |
| `bank-proof-quickbooks-generated` | `Direct_Deposit_Account_Summary.pdf` | "QuickBooks — Intuit Inc." branding | `from-bank` | **fail** — must come from the bank |
| `bank-proof-redacted-numbers` | `Voided_Check.pdf` | Routing/account shown as `****` | `usable` | **warn** — unusable, request a clean copy |

> `bank-proof-voided-check` vs `bank-proof-redacted-numbers`: in the former the
> numbers are real and appear as `▮▮▮` (present, ADA-masked); in the latter the
> source itself shows `****` (missing). Same distinction as the masterfile pair
> above. `bank-proof-quickbooks-generated` is the case a filename alone would
> never catch — the document is *named* like a bank doc; only the content
> reveals it was generated by QuickBooks.

## time_off_accruals

| Case | Document | Scenario | Rule | Expect |
|---|---|---|---|---|
| `time-off-accruals-current` | `Time_Off_Balances_20260720.csv` | Balances as-of 2026-07-20, all fields | `asof-today` | **pass** |
| `time-off-accruals-stale-asof` | `Time_Off_Balances_20260131.csv` | As-of 2026-01-31 | `asof-today` | **warn** |

## tax_setup

| Case | Document | Scenario | Rule | Expect |
|---|---|---|---|---|
| `tax-setup-ids-visible` | `Company_Tax_Setup.csv` | EIN + IL withholding/SUI accounts and rates | `ids-visible` | **pass** |
| `tax-setup-ids-on-file` | `Company_Tax_Setup_Export.csv` | Account numbers literally `ON FILE` | `ids-visible` | **warn** |

## explicit constraints — stated by ADP in the request

These documents **pass every standing rule** in `validations.yaml`. They fail
only against what ADP wrote in this client's own request, captured in Phase 0 as
the requirement's `explicit_constraints`. Nothing in the file reveals the
constraint — it lives on the requirement, so the skill must carry it forward
from the email/pasted text to the validation step.

The prompt for each case quotes ADP's wording verbatim.

| Case | Document | ADP's stated criterion | Expect |
|---|---|---|---|
| `explicit-format-csv-when-pdf-required` | `Payroll_Register_Q2_2026.csv` | "PDF format only" | **fail** — content is right, format isn't. `file_format` reports `magic: text/csv` |
| `explicit-combined-when-per-date-required` | `Payroll_Register_Q2_2026_AllChecks.pdf` | "one file per check date, do not combine" | **fail** — one file spans all 6 check dates |
| `explicit-daterange-narrower-than-supplied` | `EmployeeEarningsRecord_01012026-06192026.pdf` | "covering 04/01/2026 through 06/30/2026" | **fail** — file runs 01/01–06/19, wider than asked |

> **Precedence is additive, never subtractive.** An explicit constraint can only
> tighten what's acceptable. A request saying "PDF is fine" must never be read
> as waiving `ssn-unmasked`. A good run reports the violated constraint
> *verbatim* rather than paraphrasing it.
>
> Note the last case is genuinely arguable — a wider date range may or may not
> be acceptable. The right behaviour is to flag the mismatch against ADP's
> stated range and let the operator decide, not to silently accept it.

## coverage — cross-document (Phase B.5)

Judged once over the approved set, not per file. Each folder holds the whole set.

| Case | Folder contents | Rule | Expect |
|---|---|---|---|
| `coverage-register-full-quarter` | Register covering all 6 Q2 dates | `register-per-check-date` | **pass** — all expected dates present |
| `coverage-register-single-date` | Single-day register (05/08 only) | `register-per-check-date` | **5 derived requirements** — one per missing check date |
| `coverage-941-standalone` | 941 alone, no SUI | `state-filings-companion` | **derived requirement** |
| `coverage-missing-dd-routing` | Masterfile + register, no routing doc (`dd_enrolled=true`) | `dd-routing-present` | **derived requirement** for DD authorizations / voided checks |
| `coverage-missing-garnishment-order` | Register + masterfile, no court order (`garnishments=true`) | `conditional-artifacts` | **derived requirement** |
| `coverage-missing-ia-ben` | 941 + IA quarterly report, no BEN visible (`states=[IA]`) | `ia-ben-visible` | **derived requirement** for BEN documentation |

**Mind which quarter you ask for.** `--expected-check-dates` returns the
**quarter containing `--ref-date`**, quarter-start through ref (never future) —
the *current* payroll quarter. The *filing* quarter from `--required-quarters`
is a different thing (at 2026-07-20: Q2 required, Q1 fallback). For
`coverage-register-full-quarter` / `coverage-register-single-date`, whose
registers are Q2, use a Q2 ref date:

```sh
python3 ada/scripts/validate.py --expected-check-dates \
  --frequency biweekly --anchor 2026-04-10 --ref-date 2026-06-30
# → 2026-04-10, 04-24, 05-08, 05-22, 06-05, 06-19   (the 6 dates the fixtures use)
```

Using `--ref-date 2026-07-20` there instead returns Q3-to-date
(`07-03, 07-17`) — correct for the helper, wrong for judging a Q2 register.

## Gate regression (code-enforced, not judged)

Run with [`run_gate_tests.sh`](run_gate_tests.sh) — all five assert automatically.

| # | Case | Expect |
|---|---|---|
| G1 | `ledger.py approve --validation fail` without `--override` | **refused** |
| G2 | Same with `--override` + note | approved, `override: true` recorded |
| G3 | Approved file modified after approval, then packaged | **not staged** (content hash mismatch) |
| G4 | Any ledger entry edited by hand | `ledger.py verify` **fails**; `package.py` aborts |
