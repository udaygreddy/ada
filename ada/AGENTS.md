# ADA — ADP Discovery Agent (Codex / Cursor / Copilot entry)

This repo is an ADA bundle. When asked to run discovery / collect ADP onboarding
documents, follow [PROCEDURE.md](PROCEDURE.md) exactly — it is the source of
truth for the scan → review → package workflow and the non-negotiable rules.

**Core principle:** never transmit data anywhere. Read locally, record every
source authorization and document approval through `scripts/ledger.py`, and
produce a local `ada_package/` folder that the client transmits to ADP.

Map of the bundle:
- [PROCEDURE.md](PROCEDURE.md) — the workflow to execute.
- [taxonomy.yaml](taxonomy.yaml) — in-scope documents mapped to system.
- [connectors/paychex_export.md](connectors/paychex_export.md) — Paychex export checklist.
- [connectors/intuit.md](connectors/intuit.md) — QuickBooks read-only allow-list.
- `scripts/` — hard controls (ledger, enumerate, pii_scan, package). Stdlib
  Python 3; run with `python3 scripts/<name>.py`. No dependencies to install.

Begin by reading PROCEDURE.md, then greet the operator and start Phase A.
