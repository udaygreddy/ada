# Connector: paylocity-export (guided export ingest)

Paylocity is one of the supported payroll providers. Like Paychex, ADA collects
Paylocity data by **guiding the operator to export reports**, then ingesting the
dropped files through the loose-file pipeline (`enumerate.py` → `pii_scan.py` →
classify → review → `package.py`).

The navigation below is the **verified ADP onboarding click-path for Paylocity**
(source: ADP's Paylocity onboarding guide). Present it one report at a time,
waiting for confirmation before the next. Use the exact menu/button labels in
**bold**; if the operator's screen differs, ask what they see and help find the
closest match.

## Before downloads — three intake questions

1. **Direct deposit:** "Will everyone be enrolled in Direct Deposit?"
2. **PTO:** "Are PTO balances tracked in Paylocity?" If no, ask whether they
   track PTO manually and want it transferred — if so, have them upload the
   tracker.
3. **Garnishments:** "Any employees with garnishments (e.g., child support)?"
   If yes, have them upload the garnishment court order(s).

Then have them create a save folder (the drop folder ADA will ingest), log into
Paylocity, and confirm "ready to get started."

## Report-by-report navigation (Paylocity)

Most reports live under **Reports & Analytics**. For quarter selection, see
*Quarterly timing* in `connectors/paychex_export.md` (same rules apply).

### 1. Quarterly Filings → `4a.tax_returns` (+ `3b.tax_setup` tax IDs)
- **Reports & Analytics** → **Quarterly & Year End**.
- Download the applicable **Quarterly Filing** for the request date.

### 2. Payroll Register Summary → `3c.payroll_register`
- **Reports & Analytics** → **Reporting** → search **Payroll Register Summary**.
- **Payroll Filters** → **Current Quarter**; **Employee Status** & **Employee
  Type** → **All**; export. Repeat for **Prior Quarter**.
- **PXP (per check date):** Payroll Filters → **Process Date Range**; run each
  required check date as a **single-day range** (start = end = check date),
  export each. Repeat for every check date in the quarter through the last.

### 3. Payroll Register Summary with YTD → `3c.ytd_balances`
- **Reports & Analytics** → **Reporting** → search **Payroll Register Summary**.
- **Current Quarter** under Payroll Filters; all Employee Status/Type selected;
  export. Repeat for **Prior Quarter**.

### 4. Master Control by Date Range → `3a.employee_masterfile`
- Search **Master Control by Date Range Report**.
- Select **Current Year to Date**.
- On export, ensure **Hide Social Security Numbers is UNCHECKED** (select
  **Show**), then run.

### 5. Statement of Filings and Deposits → `4a.tax_deposits`
- Search **Statement of Filings and Deposits**.
- Select the applicable **Year and Quarter** (per *Quarterly timing*); run and
  download the PDF.

### 6. Payroll Summary → `3c.payroll_summary`
- Search **Payroll Summary**.
- Select **Process Date Range**, enter the payroll process dates, export.

### 7. Labor Distribution Report → `3c.payroll_summary` (labor/GL allocation)
- Search **Labor Distribution**.
- Select **Current Quarter**; all Employee Status/Type selected; export.

## Ingest steps

1. `python3 "$ADA_HOME/scripts/ledger.py" authorize --ledger ./.ada/ledger.jsonl --connector paylocity-export --scope <drop folder>`
2. `python3 "$ADA_HOME/scripts/enumerate.py" <drop folder> --connector paylocity-export --out ./.ada/candidates.jsonl`
3. `python3 "$ADA_HOME/scripts/pii_scan.py" --candidates ./.ada/candidates.jsonl --update`
4. Classify each candidate against the ids above (filename-first). Then proceed
   to REVIEW (PROCEDURE Phase B).

## Notes

- Most Paylocity artifacts are **high-sensitivity** (register summaries, YTD,
  Master Control with SSNs). Expect the PII confirmation gate to fire often.
- The **per-check-date rule** (each check date = one single-day report) applies
  to the PXP register exports — same as Paychex.
- Bank proof (voided check / bank statement) is an operator **upload**, not a
  Paylocity report → `2.bank_proof`.
