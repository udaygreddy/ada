# ADA validation test cases

Positive (should **pass**) and negative (should **warn** / **fail**) cases for
every document type in [`ada/validations.yaml`](../ada/validations.yaml).

Each case is a folder under `tests/cases/<CASE-ID>/` holding the document(s) a
client would actually drop for that scenario. **Filenames look like real exports,
never like test names**, and the folder is just the case id — so nothing in the
corpus reveals the answer. The skill has to judge from content, which is the
whole point. Expected verdicts live here and only here.

Because validation is **model-judged**, these aren't asserted by a script — the
Expect column is the verdict a correct judgment produces. Use them after a rules
change, a prompt change, or a model upgrade. (The code-enforced gates *are*
script-asserted — see [`run_gate_tests.sh`](run_gate_tests.sh).)

- **Generate:** `python3 tests/make_fixtures.py` → 39 folders, 42 files. All
  synthetic; SSNs use the SSA-invalid `000-` range, emails use `example.com`.
- **Reference date: `2026-07-20`.** Mid-late July, so per ADP's quarterly timing
  **Q2 2026 is required** and **Q1 2026 is the fallback**. Pass the same
  `--ref-date 2026-07-20` when reproducing, or the quarter expectations shift.
- **Intake facts** the cases assume:
  `payroll_frequency=biweekly`, `anchor_check_date=2026-04-10`,
  `last_check_date=2026-06-19`, `active_employee_count=4`,
  `states=[IL]`, `dd_enrolled=true`, `garnishments=false`.

## How to run one case

```sh
python3 ada/scripts/validate.py --extract \
  --file tests/cases/R2/*.pdf \
  --expected-doc-type payroll_register \
  --expected-period "last quarter" --ref-date 2026-07-20
```

Then judge the extracted text against `common` + `doc_types.<doc_type>` checks
and compare with the expected verdict. Empty `text` (scanned) is not a free
pass — read the file natively and judge the same criteria.

To exercise a whole case folder as a drop folder (Phase A ingest), point
`enumerate.py` at `tests/cases/<CASE-ID>/`.

---

## common — applies to every document

| Case | Document | Scenario | Rule | Expect |
|---|---|---|---|---|
| `C1` | `PayrollJournal_04012026-06302026.pdf` | Right type, right quarter | `matches-request` | **pass** |
| `C2` | `EmployeeEarningsRecord_01012026-06192026.pdf` | YTD report submitted where a register was asked for | `matches-request` | **fail** |
| `C3` | `PayrollJournal_04102026.pdf` | "page 1 of 6 — remaining pages missing" | `legible-complete` | **warn** |
| `C4` | `PayrollJournal_2026Q2.pdf` | Image-only scan → extraction empty | `legible-complete` | **read natively**, then judge; do not auto-pass |

> **C5 — the print-date trap (regression).** Every register fixture ends with
> `Report generated on 07/20/2026`, outside Q2. A correct judgment ignores it and
> reads the check dates → C1 **passes**. A naive min/max date span would call
> this a mismatch — the bug model judgment exists to avoid.

## employee_masterfile

| Case | Document | Scenario | Rule | Expect |
|---|---|---|---|---|
| `M1` | `Employee_Master_File_20260720.csv` | Full SSNs (→ `▮▮▮`), all fields, actives + terminated | all | **pass** |
| `M2` | `Master_Control_by_Date_Range_20260720.csv` | Source exported `XXX-XX-2001` | `ssn-unmasked` | **fail** + Paylocity/QBO unmask remediation |
| `M3` | `EmployeeDetails.csv` | No SSN column at all | `ssn-unmasked` | **fail** |
| `M4` | `Employee_Census_20260720.csv` | 4 actives, no terminated | `includes-terminated` | **warn** |
| `M5` | `Employee_List.csv` | Only name/SSN/status — no DOB, hire date, rate, address | `required-fields` | **warn** (name the missing columns) |

> M1 vs M2 is the core evidence distinction: `▮▮▮` means the value **was**
> present and ADA masked it (good); a literal `XXX-XX-####` means the **source
> export** was masked (bad). Verified: M1 → 5 masks, no raw SSN; M2 → `XXX-XX`
> survives, 0 masks.

## payroll_register

| Case | Document | Scenario | Rule | Expect |
|---|---|---|---|---|
| `R1` | `PayrollJournal_04012026-06302026.pdf` | All 6 Q2 check dates | `covers-required-quarter` | **pass** |
| `R2` | `PayrollJournal_01012026-03312026.pdf` | Q1 dates only, Q2 required | `covers-required-quarter` | **fail** |
| `R3` | `Payroll_Register_Summary_PXP_05082026.pdf` | One check date, single-day export | `single-day-exports` | **pass** |
| `R4` | `Payroll_Register_Summary_ProcessDateRange.pdf` | 04/01–06/30 combined multi-payroll range | `single-day-exports` | **warn** |
| `R5` | `Payroll_Journal_2026Q2.pdf` | Image-only scan | `legible-complete` | read natively; **fail** if unreadable |

## ytd_balances

| Case | Document | Scenario | Rule | Expect |
|---|---|---|---|---|
| `Y1` | `EmployeeEarningsRecord_01012026-06192026.pdf` | 01/01/2026 → 06/19/2026 (= `last_check_date`) | `range-jan1-to-last-check` | **pass** |
| `Y2` | `EmployeeEarningsRecord_04012026-06192026.pdf` | 04/01 → 06/19 — quarter, not YTD | `range-jan1-to-last-check` | **fail** |
| `Y3` | `EmployeeEarningsRecord_01012026-03202026.pdf` | 01/01 → 03/20 — stale end date | `range-jan1-to-last-check` | **fail** |

## w2

| Case | Document | Scenario | Rule | Expect |
|---|---|---|---|---|
| `W1` | `W2_2025_Nolan_Avery.pdf` | Prior year (2025) relative to 2026 | `prior-year` | **pass** |
| `W2` | `W2_2023_Nolan_Avery.pdf` | 2023 W-2 | `prior-year` | **fail** |

## tax_return

| Case | Document | Scenario | Rule | Expect |
|---|---|---|---|---|
| `T1` | `Form941_2026Q2.pdf` | 941, Q2 2026, quarter ended | `quarter-required-and-finalized` | **pass** |
| `T2` | `Form941_2026Q3.pdf` | Q3 2026 — quarter not ended | `quarter-required-and-finalized` | **fail** (never accept unfinalized) |
| `T3` | `Form941_2025Q3.pdf` | Q3 2025 — outside required/fallback | `quarter-required-and-finalized` | **fail** |
| `T4` | `IL_UI-3-40_2026Q2.pdf` | IL SUI filing, same quarter | `state-sui-filing` (companion) | **pass** — satisfies the companion for T1 |
| `T5` | `Form941_2026Q2.pdf` (alone) | 941 with no state filing in the set | `state-filings-companion` (coverage) | **derived requirement** for the SUI filing |

## tax_deposit

| Case | Document | Scenario | Rule | Expect |
|---|---|---|---|---|
| `D1` | `Statement_of_Filings_and_Deposits_2026Q2.pdf` | Deposits across all 6 Q2 check dates | `covers-quarter` | **pass** |
| `D2` | `Statement_of_Filings_and_Deposits_2026Q1.pdf` | Q1 deposits, Q2 registers approved | `covers-quarter` / `deposits-cover-quarter` | **warn** |

## bank_proof

| Case | Document | Scenario | Rule | Expect |
|---|---|---|---|---|
| `B1` | `Voided_Check_FirstSpringfieldBank.pdf` | Bank-issued voided check, routing + account present | `from-bank`, `usable` | **pass** |
| `B2` | `Direct_Deposit_Account_Summary.pdf` | "QuickBooks — Intuit Inc." branding | `from-bank` | **fail** — must come from the bank |
| `B3` | `Voided_Check.pdf` | Routing/account shown as `****` | `usable` | **warn** — unusable, request a clean copy |

> B1 vs B3: in B1 the numbers are real and appear as `▮▮▮` (present, ADA-masked);
> in B3 the source itself shows `****` (missing). Same distinction as M1/M2.
> B2 is the case a filename alone would never catch — the document is *named*
> like a bank doc; only the content reveals it was generated by QuickBooks.

## time_off_accruals

| Case | Document | Scenario | Rule | Expect |
|---|---|---|---|---|
| `P1` | `Time_Off_Balances_20260720.csv` | Balances as-of 2026-07-20, all fields | `asof-today` | **pass** |
| `P2` | `Time_Off_Balances_20260131.csv` | As-of 2026-01-31 | `asof-today` | **warn** |

## tax_setup

| Case | Document | Scenario | Rule | Expect |
|---|---|---|---|---|
| `S1` | `Company_Tax_Setup.csv` | EIN + IL withholding/SUI accounts and rates | `ids-visible` | **pass** |
| `S2` | `Company_Tax_Setup_Export.csv` | Account numbers literally `ON FILE` | `ids-visible` | **warn** |

## coverage — cross-document (Phase B.5)

Judged once over the approved set, not per file. Each folder holds the whole set.

| Case | Folder contents | Rule | Expect |
|---|---|---|---|
| `V1` | Register covering all 6 Q2 dates | `register-per-check-date` | **pass** — all expected dates present |
| `V2` | Single-day register (05/08 only) | `register-per-check-date` | **5 derived requirements** — one per missing check date |
| `V3` | 941 alone, no SUI | `state-filings-companion` | **derived requirement** |
| `V4` | Masterfile + register, no routing doc (`dd_enrolled=true`) | `dd-routing-present` | **derived requirement** for DD authorizations / voided checks |
| `V5` | Register + masterfile, no court order (`garnishments=true`) | `conditional-artifacts` | **derived requirement** |
| `V6` | 941 + IA quarterly report, no BEN visible (`states=[IA]`) | `ia-ben-visible` | **derived requirement** for BEN documentation |

**Mind which quarter you ask for.** `--expected-check-dates` returns the
**quarter containing `--ref-date`**, quarter-start through ref (never future) —
the *current* payroll quarter. The *filing* quarter from `--required-quarters`
is a different thing (at 2026-07-20: Q2 required, Q1 fallback). For V1/V2, whose
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
