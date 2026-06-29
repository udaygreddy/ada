# ADA — ADP Discovery Agent (Codex / Cursor / Copilot entry)

This repo is an ADA bundle. When asked to run discovery / collect ADP onboarding
documents, follow [PROCEDURE.md](PROCEDURE.md) exactly — it is the source of
truth for the scan → review → package workflow and the non-negotiable rules.

**Core principle:** never transmit data anywhere. Read locally, record every
source authorization and document approval through `scripts/ledger.py`, and
produce a local `ada_package/` folder that the client transmits to ADP.

The per-client requirement list (the WHAT) comes from the ADP request **email**
(Phase 0); the **taxonomy** is only a catalog of HOW/WHERE per document type.

Map of the bundle:
- [PROCEDURE.md](PROCEDURE.md) — the workflow to execute (Phase 0 → A → B → C).
- [connectors/mailbox.md](connectors/mailbox.md) — derive requirements from ADP emails (Gmail, read-only).
- [connectors/salesforce_case.md](connectors/salesforce_case.md) — future requirement source.
- [taxonomy.yaml](taxonomy.yaml) — master catalog: source + method + sensitivity per document type.
- [connectors/paychex_export.md](connectors/paychex_export.md) — Paychex export checklist.
- [connectors/intuit.md](connectors/intuit.md) — QuickBooks read-only allow-list.
- `scripts/` — hard controls (ledger, requirements, enumerate, pii_scan,
  package). Stdlib Python 3; run with `python3 scripts/<name>.py`. No deps.

Begin by reading PROCEDURE.md, then greet the operator and start Phase A.
