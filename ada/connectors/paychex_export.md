# Connector: paychex-export (guided export ingest)

Paychex Flex's API is partner-gated and clients generally can't grant it, so ADA
collects Paychex data by **guiding the operator to export reports**, then
ingesting the dropped files. This reuses the loose-file pipeline
(`enumerate.py` → `pii_scan.py` → classify → review → `package.py`).

The navigation below is the **verified ADP onboarding click-path for Paychex
Flex** (source: ADP's Paychex onboarding guide). Present it to the operator one
report at a time, waiting for confirmation before moving to the next. Use the
exact menu/button labels in **bold**; if the operator's screen differs, ask what
they see and help find the closest match.

## Before downloads — two intake questions

1. **PTO:** "Are PTO balances tracked in Paychex?" If yes, include report **6
   (Time Off Accruals)** at the end. If no, ask whether they track PTO manually
   and want it transferred — if so, have them upload the manual tracker.
2. **Garnishments:** "Any employees with garnishments (e.g., child support)?"
   If yes, have them upload the garnishment court order(s).

Then have them create a folder to save downloads (the drop folder ADA will
ingest), log into Paychex Flex, and confirm "ready to get started."

## Report-by-report navigation (Paychex Flex)

### 1. Quarterly Tax Packet — most recent filing packet → `4a.tax_returns`
- Click the pie-chart icon on the dashboard labeled **Quick Reports**.
- Click **Payroll: Quarterly**.
- Check the box for the **most recent filing packet** (which quarter → see
  *Quarterly timing* below).
- Click **Download**. If a pop-up says there are multiple files, choose
  **Combine them** (not "Keep separate") to save as one PDF.
- *(This packet also carries the company tax IDs → also satisfies `3b.tax_setup`.)*

### 2. Paycheck history — Payroll Journal → `3c.payroll_register`
- Return to **Quick Reports**.
- Switch from **Sets** to **All Reports** at the top.
- Click **Payroll Journal**.
- Check the boxes for **all payrolls run in the current quarter**.
- **Download** and **Combine**.

### 3. Consolidated payroll — Employee Earnings Record (3 reports)
Click back to **All Reports** → **Employee Earnings Record**. Generate and
**download each report individually** (do not batch):
- **Report 1 — previous completed quarter → `3c.payroll_summary`:** Create Report
  (top right) → Employee dropdown **All** → apply → date range = *previous
  completed quarter* → **Run Report** → check its box → download.
- **Report 2 — current quarter to date → `3c.payroll_summary`:** Create Report →
  All → date range = *current quarter start → last payroll check date* → Run →
  download.
- **Report 3 — year-to-date → `3c.ytd_balances`:** Create Report → All → date
  range = *start of calendar year → last payroll check date* → Run → download.

### 4. Cash Requirements — tax deposits → `4a.tax_deposits`
- Back to **All Reports**.
- Click **Cash Requirements**.
- Check the boxes for **all payrolls run in the current quarter**.
- **Download** and **Combine**.

### 5. Employee information — profiles → `3a.employee_masterfile`
- Open **People List** (top-right icon: person with 3 lines).
- Click the first employee's name → **Profile**.
- Click **DOWNLOAD PROFILE** (top right, blue).
- Download, then click into the next employee and repeat.
- Do this for **all active employees plus any terminated employees paid in the
  current calendar year**.

### 6. Time Off Accruals → `6.time_off_accruals`  *(only if PTO tracked in Paychex)*
- Back to **All Reports**.
- In the search box, search **Employee Data for Time Clocks** and open it.
- Top right → **Create Report**, name it **"PTO"**.
- Click **Layout** → select **all fields** → output **xls**.
- **Download** and save.

### 7. Bank Proof → `2.bank_proof`
- Ask the operator for a **voided check or bank statement** for the account
  payroll is funded from, and have them upload/drop it into the folder.

## Quarterly timing — which quarter(s) to request

Which filing packet / date ranges to pull depends on the current month
(quarters must be **finalized**; always allow the prior quarter as fallback):

| Window | Request | Fallback |
|---|---|---|
| Jan | Q3 + Q4 (prior yr, if avail) | — |
| Feb–Mar | Q4 (prior yr) | — |
| Apr (early / late) | Q4 prior yr / Q1 current | Q1 if avail / Q4 |
| May–Jun | Q1 (current) | — |
| Jul (early / late) | Q1+Q2 / Q2 primary | Q2 if avail / Q1 |
| Aug–Sep | Q1 + Q2 | — |
| Oct (early / late) | Q1+Q2 / +Q3 | Q3 if avail |
| Nov–Dec | Q1 + Q2 + Q3 | — |

**Per-check-date rule:** for payroll-level pulls, each payroll check date =
one report with start date = end date = that check date. Only request check
dates between the current quarter start and today; never future/uncompleted
ones. Confirm the actual weekly/biweekly/monthly schedule with the operator.

## Ingest steps

1. `python3 "$ADA_HOME/scripts/ledger.py" authorize --ledger ./.ada/ledger.jsonl --connector paychex-export --scope <drop folder>`
2. `python3 "$ADA_HOME/scripts/enumerate.py" <drop folder> --connector paychex-export --out ./.ada/candidates.jsonl`
3. `python3 "$ADA_HOME/scripts/pii_scan.py" --candidates ./.ada/candidates.jsonl --update`
4. Classify each candidate against the ids above (filename-first). Then proceed
   to REVIEW (PROCEDURE Phase B).

## Notes

- Most Paychex artifacts are **high-sensitivity** (tax packets, payroll journals,
  earnings records/YTD, employee profiles). Expect the PII confirmation gate to
  fire often.
- Download each report immediately after generating it; don't wait to batch.
- A future `paychex-api` connector can replace this with the same `SOURCE.*`
  interface if partner API access is ever obtained — no pipeline change.
