# Connector: intuit (QuickBooks — structured pull, READ-ONLY)

QuickBooks is the client's accounting/GL system and has a real API. ADA pulls a
**read-only** subset via the QBO MCP connector the client has already authorized,
materializes each result as a local file, and feeds those files into the same
pipeline as Paychex exports.

## Hard rule: read-only allow-list

Only the **read** tools below may be called. Never call any QBO tool whose name
contains `create`, `update`, `delete`, `send`, `duplicate`, or `import`. This is
a structural constraint, not a preference — QBO MCP exposes many write/delete
tools that must remain unreachable (DESIGN §6).

| taxonomy id | QBO MCP read tool(s) | Materialize as |
|---|---|---|
| `2.company_verification` | `company_info` / `qbo_payroll_get_company_info` | `qbo/company_info.json` |
| `5b.accounting_metadata` | `company_info` (metadata fields) | `qbo/company_info.json` |
| `2.financial_verification` | `qbo_accounting_get_balance_sheet`, `profit_loss_generator` | `qbo/balance_sheet.json`, `qbo/pnl.json` |
| (context) AR/AP aging | `qbo_accounting_get_ar_aging_summary`, `..._ap_aging_summary` | `qbo/ar_aging.json`, `qbo/ap_aging.json` |

> **Do not pull QBO Payroll.** SBS-on-Paychex clients typically have no QBO
> Payroll; those tools return empty. Payroll comes from Paychex.

## Tiered resolution for items the MCP can't serve

Chart of Accounts (`5a.chart_of_accounts`) and journal entries
(`5a.journal_entries`) have **no MCP endpoint**. Offer the operator, per item:

1. **MCP** — n/a here (no tool), so skip to choice.
2. **Operator choice:**
   - **Direct read-only API call** to the QBO `Account` / `JournalEntry` entity
     under their own OAuth (read scopes only), materialized to
     `qbo/chart_of_accounts.json` / `qbo/journal_entries.json`; or
   - **Guided QBO export** — tell them which QuickBooks report to export to the
     drop folder; ingest it like a Paychex file.
3. **Gap** — if they decline both, log it as a gap (it appears in the report).

Record which tier was used (it shows up via the ledger/manifest as provenance).

## Ingest steps

1. `ledger.py authorize --connector intuit --scope <realm/company id>`
2. Call the read tools above; write each JSON result to `./qbo/`.
3. `enumerate.py ./qbo --connector intuit --out .ada/candidates.jsonl` (append).
4. `pii_scan.py --candidates .ada/candidates.jsonl --update`, then classify and
   proceed to REVIEW.
