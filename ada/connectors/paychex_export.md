# Connector: paychex-export (guided export ingest)

Paychex Flex's API is partner-gated and clients generally can't grant it, so ADA
collects Paychex data by **guiding the operator to export reports**, then
ingesting the dropped files. This reuses the loose-file pipeline
(`enumerate.py` → `pii_scan.py` → classify → review → `package.py`).

## Operator export checklist

Ask the operator to log into **Paychex Flex** and export the following into a
single drop folder (you'll tell them the path). CSV preferred where offered;
otherwise PDF. Items map to `taxonomy.yaml` ids.

| Export from Paychex Flex | taxonomy id | Notes |
|---|---|---|
| Employee / Census report | `3a.employee_masterfile` | demographics, job, comp — **PII** |
| Earnings setup report | `3b.earnings_codes` | |
| Deductions report | `3b.deduction_codes` | |
| Company tax setup report | `3b.tax_setup` | |
| YTD earnings report | `3c.ytd_balances` | **PII** |
| Payroll Journal / Register (recent quarters) | `3c.payroll_register` | **PII** |
| Payroll summary | `3c.payroll_summary` | |
| Sample paystubs (a few employees) | `3d.paystubs` | **PII** |
| Prior-year W-2s | `3d.w2s` | **PII** |
| Quarterly/annual tax forms (941/940/SUI/SIT) | `4a.tax_returns` | |
| Tax deposit / liability report | `4a.tax_deposits` | |

> ⚠ The exact Paychex Flex report names and navigation paths above are a **first
> draft of intent** and must be verified against a live Paychex tenant
> (POC-DESIGN §6). Adjust labels to match what the operator actually sees.

## Ingest steps

1. `ledger.py authorize --connector paychex-export --scope <drop folder>`
2. `enumerate.py <drop folder> --connector paychex-export --out .ada/candidates.jsonl`
3. `pii_scan.py --candidates .ada/candidates.jsonl --update`
4. Classify each candidate against the ids above (filename-first). Then proceed
   to REVIEW (PROCEDURE Phase B).

## Notes

- Most Paychex artifacts are **high-sensitivity** (W-2s, paystubs, registers,
  YTD, census). Expect the PII confirmation gate to fire often.
- A future `paychex-api` connector can replace this with the same `SOURCE.*`
  interface if partner API access is ever obtained — no pipeline change.
