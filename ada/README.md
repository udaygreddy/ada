# ADA — ADP Discovery Agent

A portable skill a client runs **inside their own AI assistant** (Claude Code,
Codex, Cursor, Copilot) to discover, review, and package the onboarding documents
ADP needs — **without any ADP person accessing the client's systems**.

Supported systems: **Paychex** and **Paylocity** (payroll — guided export) and
**Intuit QuickBooks** (accounting/GL — read-only).

## Two roles: requirements vs. taxonomy

- **Requirements (the WHAT)** — which documents *this* client must provide — are
  derived from the **ADP request**: text the operator pastes into chat and/or the
  request email in any connected mailbox (Phase 0; operator input is primary,
  email enriches it; future: a Salesforce Case via MCP). This is the per-client
  checklist.
- **Taxonomy (the HOW/WHERE)** — `taxonomy.yaml` is a master *catalog*. Once a
  requirement is mapped to a taxonomy id, the catalog supplies the source system,
  collection method, and sensitivity for that document type.

## How it works

The agent (the client's assistant) does the *judgment* — talking to the operator,
classifying documents. Bundled **scripts do the controls** — so consent and audit
don't depend on the model behaving:

- `scripts/ledger.py` — append-only, **hash-chained** consent ledger. Records
  source authorizations (gate 1), per-document approvals (gate 2), and per-client
  **requirements** with their source-email provenance. Each approval mints a
  token bound to the file's content hash.
- `scripts/requirements.py` — record/list the per-client requirements derived
  from the ADP request source (email now, Salesforce Case later).
- `scripts/enumerate.py` — lists + SHA-256 hashes candidate files.
- `scripts/pii_scan.py` — local regex sensitivity flagging (counts only, never
  stores PII values). Content scanned in code — never sent to the LLM.
- `scripts/validate.py` — validation support: `--extract` reads the file's
  content (text/CSV directly; PDFs via stdlib zlib stream extraction), **masks
  PII**, and resolves the expected period deterministically; `--required-quarters`
  and `--expected-check-dates` compute calendar expectations (ADP's quarterly
  timing rules; per-check-date schedules). The **agent judges every acceptance
  check in `validations.yaml`** from that evidence — code never issues a
  verdict. Verdicts are recorded via `ledger.py approve`, whose fail-gate blocks
  a `fail` unless the operator records an override.
- `validations.yaml` — the acceptance-check catalog, **keyed by document type**
  (mined from ADP's onboarding guide): per-type checks, per-provider remediation
  strings, companions/conditionals, and cross-document coverage checks. Adding a
  future validation = adding a line to the right doc_type block.
- `scripts/package.py` — stages **only** ledger-approved, hash-matched files;
  emits `manifest.json` + `gap_report.md` (with a validation summary). Aborts if
  the ledger chain is broken.

Everything is **stdlib-only Python 3** — no dependencies — so the code is fully
client-reviewable (a legal requirement). The payroll provider is
pluggable: each provider (Paychex, Paylocity, …) is a connector doc supplying its
own report navigation; adding one doesn't touch the pipeline.

## Layout

```
SKILL.md / AGENTS.md      host entry points → PROCEDURE.md
PROCEDURE.md              the Phase 0 → scan → review → package workflow
taxonomy.yaml             master catalog: source + method + sensitivity per type
validations.yaml          acceptance checks by doc_type + coverage (model-judged)
connectors/
  mailbox.md              enrich requirements from ADP emails (any mail connector, optional)
  salesforce_case.md      future requirement source (Salesforce Case via MCP)
  paychex_export.md       Paychex export navigation (guided ingest)
  paylocity_export.md     Paylocity export navigation (guided ingest)
  intuit.md               QuickBooks read-only allow-list + tiered fallback
scripts/                  hard controls (ledger/requirements/enumerate/pii_scan/package)
```

## Quick manual run (for testing the scripts directly)

```sh
W=.ada
python3 scripts/ledger.py    init --ledger $W/ledger.jsonl --run-id R1 \
        --client "Acme" --operator op --host claude-code
# Phase 0 — requirements derived from the ADP email (the WHAT):
python3 scripts/requirements.py add --ledger $W/ledger.jsonl --reqs $W/requirements.jsonl \
        --req-id R1 --text "Employee census" --source-kind email \
        --source-ref <thread> --source-from impl@adp.com --taxonomy-id 3a.employee_masterfile
# Phase A/B — collect + approve against the taxonomy's source for each requirement:
python3 scripts/enumerate.py <drop_folder> --connector paychex-export --out $W/candidates.jsonl
python3 scripts/pii_scan.py  --candidates $W/candidates.jsonl --update
python3 scripts/ledger.py    authorize --ledger $W/ledger.jsonl \
        --connector paychex-export --scope <drop_folder>
python3 scripts/ledger.py    approve --ledger $W/ledger.jsonl \
        --path <drop_folder>/<file> --checklist-id 3a.employee_masterfile
# Phase C — package; gap report measures collected vs REQUESTED:
python3 scripts/package.py   --ledger $W/ledger.jsonl --candidates $W/candidates.jsonl \
        --taxonomy taxonomy.yaml --out ada_package
```

Normally you don't run these by hand — the assistant drives them per
`PROCEDURE.md`. The package the client transmits to ADP is `ada_package/`. **ADA
never transmits anything itself.**

## Status

Pipeline verified end-to-end on synthetic data, including: gate refuses
un-approved files, ledger tamper detection, and content-hash binding (a file
modified after approval is rejected). Paychex and Paylocity export navigation is
sourced from ADP's onboarding guide. Not yet done: live QBO read-entity calls +
OAuth scope confinement, and the secure handoff channel — required before any
real PII collection.
