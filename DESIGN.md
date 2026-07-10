# ADA — Skill Design: Paychex / Paylocity / Intuit

Concrete instantiation of [PLAYBOOK-v2.md](PLAYBOOK-v2.md). Target clients run a
payroll provider — **Paychex** or **Paylocity** — plus, optionally, **Intuit
QuickBooks** for accounting. Migration shape: payroll moves off the incumbent
provider → ADP; QuickBooks stays and integrates for GL.

The two payroll providers share the same **guided-export** pattern and differ
only in report navigation (see `ada/connectors/paychex_export.md` and
`ada/connectors/paylocity_export.md`). The sections below use Paychex as the
worked example; Paylocity follows the same shape.

---

## 1. The two systems play different roles → two connector styles

| | **Intuit / QuickBooks** | **Paychex** |
|---|---|---|
| Role for client | Accounting / General Ledger | Incumbent payroll (being replaced) |
| What it holds | Company info, chart of accounts, GL, P&L, balance sheet | Employee masterfile, payroll registers, YTD, tax filings, paystubs, W-2s |
| Access path | **Structured pull** via QBO API / MCP (read-only) | **Guided export ingest** — operator downloads reports, ADA classifies files |
| Why | Real API; MCP connector already exists | API is partner-gated; clients can't grant it. Export is realistic & low-friction |
| Collection tier | `api-pull` 🟡 | `loose-file` 🟢 (after operator export) |
| Sensitivity | medium (financials) | **high** (W-2s, paystubs, SSNs) |

This split keeps the design honest: QuickBooks proves the structured-pull path,
the payroll providers prove the file-ingest path. Between them they cover the
bulk of a small-business onboarding without incumbent-portal scraping or form
generation.

---

## 2. In-scope taxonomy

Subset of [documentstocollect.md](documentstocollect.md), mapped to system +
method. Payroll items are provider-agnostic (`system: payroll`); the exact report
per provider lives in the connector docs.

### From Paychex (guided export ingest)

| Checklist item | Paychex report to export | Sensitivity |
|---|---|---|
| §3A Employee Masterfile / Demographics / Job & comp | Employee/Census report (CSV) | high (PII) |
| §3B Earnings codes & setup | Payroll/earnings setup report | low |
| §3B Deduction codes & setup | Deductions report | low |
| §3B Tax setup (fed/state/local) | Company tax setup report | medium |
| §3C YTD balances | YTD earnings report | high |
| §3C Payroll registers (prior periods) | Payroll Journal / Register | high |
| §3C Payroll summary reports | Payroll summary | medium |
| §3D Paystubs | Sample paystub PDFs | **high** |
| §3D W-2s | Prior-year W-2s | **high** |
| §4A Prior quarter tax returns (941/940/SUI/SIT) | Quarterly/annual tax forms (PDF) | medium |
| §4A Proof of tax deposits | Tax deposit/liability report | medium |

### From QuickBooks (structured pull, read-only MCP)

| Checklist item | QBO MCP tool(s) | Materialized as |
|---|---|---|
| §2 Company / EIN verification | `company_info` / `qbo_payroll_get_company_info` | `company_info.json` |
| §2 Financial verification | `qbo_accounting_get_balance_sheet`, `profit_loss_generator` | `balance_sheet.pdf`, `pnl.pdf` |
| §5A Chart of accounts | MCP n/a → fallback: API `Account` *or* guided export | `chart_of_accounts.csv` |
| §5A Recent journal entries / payroll journal | MCP n/a → fallback: API `JournalEntry` *or* guided export | `gl_detail.csv` |
| §5B Accounting software name / calendar | `company_info` metadata | in `company_info.json` |
| (context) AR/AP aging | `qbo_accounting_get_ar_aging_summary`, `..._ap_aging_summary` | `ar_aging.csv`, `ap_aging.csv` |

> **Tiered resolution (not a dead end):** the available QBO MCP surface exposes
> reports (balance sheet, P&L, aging, sales) but not a direct **Chart of Accounts
> / GL detail** endpoint. ADA handles this with a fallback ladder per item:
> **(1)** pull via MCP where available; **(2)** for the remainder, offer the
> operator a choice — a read-only direct QBO API call (`Account` / `JournalEntry`
> entities) *or* a guided QuickBooks export (download from the QBO UI, drop in a
> folder, ingest like Paychex files); **(3)** if the operator declines both, flag
> the item as a gap. The connector picks tier 1 automatically and asks at tier 2.
> See §3 and §6.

> **Note:** the QBO MCP also exposes *payroll* tools, but small-business clients
> on Paychex/Paylocity typically have **no QBO Payroll**, so those return empty.
> Payroll comes from the payroll provider, not QBO. Do not pull QBO payroll.

---

## 3. Connector designs

Both satisfy the `SOURCE.*` capability (PLAYBOOK §3); they differ only in how
candidates appear.

### `intuit` connector (structured pull)

- **Auth (gate 1):** operator connects their QBO via the host's MCP; `ledger.py`
  records `authorize_source: intuit`.
- **List/fetch:** call the **read-only** subset in §2. Hard rule: **no QBO write
  tools** (`create_*`, `update_*`, `delete_*`, `send_*`, `import`) are ever
  invoked. The connector exposes an allow-list of read tools only.
- **Materialize:** each pull is written locally as a file (`*.json/.csv/.pdf`),
  hashed, and entered as a candidate. The API response *is* the document, so the
  rest of the pipeline (review, ledger, package) treats QBO data identically to
  Paychex files.
- **Tiered acquisition per taxonomy item** (for items the MCP can't serve, e.g.
  Chart of Accounts / GL detail):
  1. **MCP read tool** — used automatically when one exists for the item.
  2. **Operator choice** when no MCP tool exists — ADA presents two options:
     - **Direct read-only API call** to the QBO entity (`Account`,
       `JournalEntry`), under the operator's own OAuth; allow-list confined to
       read scopes.
     - **Guided QBO export** — ADA tells the operator exactly which QuickBooks
       report to export to a drop folder, then ingests it like a Paychex file.
  3. **Gap** — if the operator declines both, the item is logged as a gap.
  The chosen tier is recorded in the ledger alongside the artifact, so the
  manifest shows *how* each QBO item was obtained.

### `paychex-export` connector (guided export ingest)

- **Auth (gate 1):** there is no API session — ADA presents a precise **export
  checklist** (the left column of §2's Paychex table) telling the operator which
  reports to download from Paychex Flex and into which folder. `ledger.py`
  records `authorize_source: paychex-export` with the folder scope.
- **List/fetch:** `enumerate.py` scans the drop folder; `pii_scan.py` flags
  W-2s/paystubs/registers as high-sensitivity; the agent classifies each file
  against the Paychex taxonomy rows (metadata-first).
- **Future:** a `paychex-api` connector can replace this if/when Paychex partner
  API access is obtained — same `SOURCE.*` interface, no pipeline change.

---

## 4. Procedure (specialized scan/validate/review/package)

### SCAN
1. Load `taxonomy.yaml`; confirm scope with operator (payroll-from-Paychex,
   GL-from-QuickBooks).
2. **QuickBooks:** gate 1 → call read-only MCP tools → materialize artifacts →
   hash → candidates. Note any empty/blocked pulls as gaps (COA, etc.).
3. **Paychex:** gate 1 → present export checklist → operator drops files →
   `enumerate.py` + `pii_scan.py` → classify.

### VALIDATE + REVIEW
- **Validate** each candidate against its requirement (document type + period).
  `validate.py` reads the content itself for text/CSV **and PDFs** (stdlib zlib
  stream inflation + text extraction + keyword doc-type detection), resolves the
  expected period ("last quarter" → a concrete range), and returns
  `pass/warn/fail`. Only for scanned/image PDFs and XLSX does the agent read the
  file and supply the dates/type (agent flags take precedence). Present
  expected-vs-actual — and the extraction source — to the operator.
- Per-artifact include/exclude/defer (gate 2). W-2s, paystubs, YTD, registers,
  employee census → `⚠ sensitive — confirm`, never pre-checked. On include,
  `ledger.py` records the **validation verdict** and mints an approval token bound
  to the file hash. A validation `fail` is **refused unless the operator records
  an override** — logged in the chain.

### PACKAGE
- `package.py` stages only ledger-approved artifacts, organized by section, and
  emits `manifest.json`, the gap report, and `ledger.jsonl`. Operator reviews and
  transmits via the agreed secure channel (still an open item — PLAYBOOK §10/#2).

---

## 5. Skill bundle

```
ada/                       # canonical skill — the folder you edit
  SKILL.md                 # Claude entry
  AGENTS.md                # Codex / Cursor / Copilot entry
  PROCEDURE.md             # scan/validate/review/package core (from PLAYBOOK §5)
  taxonomy.yaml            # the §2 subset, structured
  connectors/
    intuit.md              # read-tool allow-list + materialization rules
    paychex_export.md      # the operator export checklist + drop-folder spec
    paylocity_export.md    # Paylocity export navigation
  scripts/
    enumerate.py           # list + hash + pre-filter (Paychex folder; QBO outputs)
    pii_scan.py            # SSN / routing / account / EIN flagging
    validate.py            # file-vs-requirement check (type + period); fail-gate
    ledger.py              # hash-chained ledger + approval tokens + validation
    package.py             # stage approved-only; emit manifest + gap report
```

**Packaging outputs (generated from `ada/` by `build-plugin.sh`):**
`adp-discovery.plugin` (Cowork) and `adp-discovery-skill.zip` (claude.ai / Claude
Code). The build also regenerates a `.apm/` mirror of `ada/` and runs `apm pack`
to emit apm/plugin manifests — all **generated, gitignored** build artifacts, not
committed. Edit `ada/`; run `build-plugin.sh` to rebuild everything.

> Because `.apm/` is not committed, `apm install udaygreddy/ada` from GitHub is
> not offered — apm here is a local build-time packaging step. To enable
> install-from-GitHub later, commit the generated `.apm/` mirror.

`SKILL.md` / `AGENTS.md` are ~10-line pointers to `PROCEDURE.md` + `scripts/` +
the two `connectors/` specs. Everything else is shared and host-neutral.

---

## 6. Open items (added to PLAYBOOK §10)

- **QBO Chart-of-Accounts / GL detail — tiered fallback (resolved approach).**
  MCP lacks COA/journal endpoints, so ADA uses the §3 ladder: MCP where
  available → operator-chosen direct read-only API (`Account`/`JournalEntry`) or
  guided QBO export → gap. Remaining build work: implement the read-only QBO
  entity calls + OAuth read-scope confinement, and write the QBO export checklist
  (exact report names) — both need verification against a real QBO tenant.
- **Export navigation source.** Paychex and Paylocity report navigation is taken
  from ADP's onboarding guide (`connectors/*_export.md`); keep it in sync if ADP
  updates its report names/paths.
- **High-PII concentration.** The payroll side is almost entirely high-sensitivity
  (W-2s, paystubs, registers, census). The secure-handoff channel (PLAYBOOK
  §10/#2) is therefore on the critical path, not deferrable.
- **Read-only enforcement for QBO.** Must be a hard allow-list in the `intuit`
  connector, not a prose instruction — the QBO MCP exposes many write/delete
  tools that must be structurally unreachable.
- **Validation checks (extensible).** `validate.py` covers document type + period
  today. The check registry is built to grow — scope/population (all employees,
  YTD-vs-QTD), employee-count, and per-provider heuristics are planned as
  additional checks. **PDFs are parsed in-script** (stdlib zlib inflation of
  content streams + text-show extraction) — covers machine-generated payroll
  PDFs; scanned/image PDFs and XLSX fall back to agent-supplied dates/type
  (flags take precedence). The bundle stays stdlib-only.

---

## 7. Definition of done

Running ADA for a sample small-business client:
1. Pulls QuickBooks company + financial artifacts read-only and materializes them.
2. Guides a Paychex or Paylocity export and ingests + classifies the dropped files.
3. Flags every W-2/paystub/register as sensitive and holds for explicit review.
4. **Validates** each included file against its requirement (type + period);
   a mismatch (wrong quarter/type) blocks approval unless the operator overrides.
5. Produces a staging folder where **every file traces to a ledger approval
   token** and carries its validation verdict, plus `manifest.json`, a gap report
   (incl. the COA gap and a validation summary), and a hash-chained ledger.
