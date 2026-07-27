# ADA validation test cases

Positive (should **pass**) and negative (should **warn** / **fail**) cases for
every document type in [`ada/validations.yaml`](../ada/validations.yaml).

Because validation is **model-judged**, these are not asserted by a script — the
expected column is the verdict a correct judgment produces. Use them to check the
skill's judgment after a rules change, a prompt change, or a model upgrade.

- **Fixtures:** `python3 tests/make_fixtures.py` → `tests/fixtures/` (30 files).
  All data is synthetic; SSNs use SSA-invalid ranges (`000-…`), and EINs,
  routing and account numbers are invented.
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
  --file tests/fixtures/<fixture> \
  --expected-doc-type <doc_type> \
  --expected-period "last quarter" --ref-date 2026-07-20
```

Then judge the extracted text against `common` + `doc_types.<doc_type>` checks
and compare with the expected verdict below. Empty `text` (scanned) is not a
free pass — read the file natively and judge the same criteria.

---

## common — applies to every document

| # | Fixture | Scenario | Rule | Expect |
|---|---|---|---|---|
| C1 | `register_pass_q2.pdf` | Right type, right quarter | `matches-request` | **pass** |
| C2 | `common_fail_wrong_doctype.pdf` | YTD report submitted where a register was asked for | `matches-request` | **fail** |
| C3 | `common_warn_truncated.pdf` | "page 1 of 6 — remaining pages missing" | `legible-complete` | **warn** |
| C4 | `register_fail_scanned.pdf` | Image-only scan → extraction empty | `legible-complete` | **read natively**, then judge; do not auto-pass |

> **C5 — the print-date trap (regression).** `register_pass_q2.pdf` ends with
> `Report generated on 07/20/2026`, outside Q2. A correct judgment ignores it
> and reads the check dates → **pass**. A naive min/max date span would call
> this a mismatch — that's the bug model judgment exists to avoid.

## employee_masterfile

| # | Fixture | Scenario | Rule | Expect |
|---|---|---|---|---|
| M1 | `masterfile_pass.csv` | Full SSNs (→ `▮▮▮`), all fields, actives + terminated | all | **pass** |
| M2 | `masterfile_fail_masked_ssn.csv` | Source exported `XXX-XX-2001` | `ssn-unmasked` | **fail** + Paylocity/QBO unmask remediation |
| M3 | `masterfile_fail_no_ssn_column.csv` | No SSN column at all | `ssn-unmasked` | **fail** |
| M4 | `masterfile_warn_actives_only.csv` | 4 actives, no terminated | `includes-terminated` | **warn** |
| M5 | `masterfile_warn_missing_fields.csv` | Only name/SSN/status — no DOB, hire date, rate, address | `required-fields` | **warn** (name the missing columns) |

> M1 vs M2 is the core evidence distinction: `▮▮▮` means the value **was**
> present and ADA masked it (good); a literal `XXX-XX-####` means the **source
> export** was masked (bad). Verified: M1 → 5 masks, no raw SSN; M2 → `XXX-XX`
> survives, 0 masks.

## payroll_register

| # | Fixture | Scenario | Rule | Expect |
|---|---|---|---|---|
| R1 | `register_pass_q2.pdf` | All 6 Q2 check dates | `covers-required-quarter` | **pass** |
| R2 | `register_fail_q1.pdf` | Q1 dates only, Q2 required | `covers-required-quarter` | **fail** |
| R3 | `register_pass_single_day.pdf` | One check date, single-day export | `single-day-exports` | **pass** |
| R4 | `register_warn_combined_range.pdf` | 04/01–06/30 combined multi-payroll range | `single-day-exports` | **warn** |
| R5 | `register_fail_scanned.pdf` | Image-only scan | `legible-complete` | read natively; **fail** if unreadable |

## ytd_balances

| # | Fixture | Scenario | Rule | Expect |
|---|---|---|---|---|
| Y1 | `ytd_pass.pdf` | 01/01/2026 → 06/19/2026 (= `last_check_date`) | `range-jan1-to-last-check` | **pass** |
| Y2 | `ytd_fail_quarter_only.pdf` | 04/01 → 06/19 — quarter, not YTD | `range-jan1-to-last-check` | **fail** |
| Y3 | `ytd_fail_stale.pdf` | 01/01 → 03/20 — stale end date | `range-jan1-to-last-check` | **fail** |

## w2

| # | Fixture | Scenario | Rule | Expect |
|---|---|---|---|---|
| W1 | `w2_pass_2025.pdf` | Prior year (2025) relative to 2026 | `prior-year` | **pass** |
| W2 | `w2_fail_wrong_year.pdf` | 2023 W-2 | `prior-year` | **fail** |

## tax_return

| # | Fixture | Scenario | Rule | Expect |
|---|---|---|---|---|
| T1 | `tax_return_pass_q2_941.pdf` | 941, Q2 2026, quarter ended | `quarter-required-and-finalized` | **pass** |
| T2 | `tax_return_fail_in_progress_q3.pdf` | Q3 2026 — quarter not ended | `quarter-required-and-finalized` | **fail** (never accept unfinalized) |
| T3 | `tax_return_fail_too_old_q3_2025.pdf` | Q3 2025 — outside required/fallback | `quarter-required-and-finalized` | **fail** |
| T4 | `tax_return_pass_q2_sui.pdf` | IL SUI filing, same quarter | `state-sui-filing` (companion) | **pass** — satisfies the companion for T1 |
| T5 | T1 approved, T4 absent | 941 with no state filing | `state-filings-companion` (coverage) | **derived requirement** for the SUI filing |

## tax_deposit

| # | Fixture | Scenario | Rule | Expect |
|---|---|---|---|---|
| D1 | `tax_deposit_pass_q2.pdf` | Deposits across all 6 Q2 check dates | `covers-quarter` | **pass** |
| D2 | `tax_deposit_warn_q1.pdf` | Q1 deposits, Q2 registers approved | `covers-quarter` / `deposits-cover-quarter` | **warn** |

## bank_proof

| # | Fixture | Scenario | Rule | Expect |
|---|---|---|---|---|
| B1 | `bank_proof_pass_voided_check.pdf` | Bank-issued voided check, routing + account present | `from-bank`, `usable` | **pass** |
| B2 | `bank_proof_fail_intuit_generated.pdf` | "QuickBooks — Intuit Inc." branding | `from-bank` | **fail** — must come from the bank |
| B3 | `bank_proof_warn_numbers_cut_off.pdf` | Routing/account shown as `****` | `usable` | **warn** — unusable, request a clean copy |

> B1 vs B3: in B1 the numbers are real and appear as `▮▮▮` (present, ADA-masked);
> in B3 the source itself shows `****` (missing). Same distinction as M1/M2.

## time_off_accruals

| # | Fixture | Scenario | Rule | Expect |
|---|---|---|---|---|
| P1 | `pto_pass.csv` | Balances as-of 2026-07-20, all fields | `asof-today` | **pass** |
| P2 | `pto_warn_stale_asof.csv` | As-of 2026-01-31 | `asof-today` | **warn** |

## tax_setup

| # | Fixture | Scenario | Rule | Expect |
|---|---|---|---|---|
| S1 | `tax_setup_pass.csv` | EIN + IL withholding/SUI accounts and rates | `ids-visible` | **pass** |
| S2 | `tax_setup_warn_ids_on_file.csv` | Account numbers literally `ON FILE` | `ids-visible` | **warn** |

## coverage — cross-document (Phase B.5)

Judged once over the approved set, not per file.

| # | Setup | Rule | Expect |
|---|---|---|---|
| V1 | Approve `register_pass_q2.pdf` only (covers all 6 Q2 dates) | `register-per-check-date` | **pass** — all 6 expected dates present |
| V2 | Approve `register_pass_single_day.pdf` only (05/08 alone) | `register-per-check-date` | **5 derived requirements** — one per missing check date |
| V3 | Approve T1 (941) without T4 (SUI) | `state-filings-companion` | **derived requirement** |
| V4 | `dd_enrolled=true`, no routing doc approved | `dd-routing-present` | **derived requirement** for DD authorizations / voided checks |
| V5 | `garnishments=true`, no court order approved | `conditional-artifacts` | **derived requirement** |
| V6 | `states=[IA]`, BEN not visible on filings | `ia-ben-visible` | **derived requirement** for BEN documentation |

**Mind which quarter you ask for.** `--expected-check-dates` returns the
**quarter containing `--ref-date`**, quarter-start through ref (never future) —
that is the *current* payroll quarter. The *filing* quarter from
`--required-quarters` is a different thing (at 2026-07-20: Q2 required, Q1
fallback). For V1/V2, whose registers are Q2, use a Q2 ref date:

```sh
python3 ada/scripts/validate.py --expected-check-dates \
  --frequency biweekly --anchor 2026-04-10 --ref-date 2026-06-30
# → 2026-04-10, 04-24, 05-08, 05-22, 06-05, 06-19   (the 6 dates the fixtures use)
```

Using `--ref-date 2026-07-20` there instead returns Q3-to-date
(`07-03, 07-17`) — correct for the helper, wrong for judging a Q2 register.

## Gate regression (code-enforced, not judged)

| # | Case | Expect |
|---|---|---|
| G1 | `ledger.py approve --validation fail` without `--override` | **refused** |
| G2 | Same with `--override` + note | approved, `override: true` recorded |
| G3 | Approved file modified after approval, then packaged | **not staged** (content hash mismatch) |
| G4 | Any ledger entry edited by hand | `ledger.py verify` **fails**; `package.py` aborts |
