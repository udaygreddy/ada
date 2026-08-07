# ADA — ADP Discovery Agent

A portable skill a client runs **inside their own AI assistant** (Claude Code,
Codex, Cursor, Copilot) to discover, review, and package the onboarding documents
ADP needs — **without any ADP person accessing the client's systems**.

Supported systems: **Paychex** and **Paylocity** (payroll — guided export) and
**Intuit QuickBooks** (accounting/GL — read-only).

> Engineering onboarding: [`../ARCHITECTURE.md`](../ARCHITECTURE.md) — invariants,
> decision records, extension points, and known weaknesses.

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

Everything is **stdlib-only Python 3** (see [Dependencies](#dependencies)). The
payroll provider is pluggable: each provider (Paychex, Paylocity, …) is a
connector doc supplying its own report navigation; adding one doesn't touch the
pipeline.

## Dependencies

**Runtime: Python 3, stdlib only.** No pip install, no virtualenv, no network
fetch. That is a legal requirement wearing technical clothes — a client's
reviewer has to be able to read every line that will run on their machine, and
a dependency tree makes that impossible in practice.

**Everything else is optional.** The skill runs to completion with none of it.

| Optional | What it adds | Without it |
|---|---|---|
| **ADP policy service** (MCP) | Current rules, catalog, phase steps and export navigation from ADP, instead of the copies frozen into this bundle | Uses the bundled copies; says so in one line |
| **Mail connector** (any) | Finds the ADP request email to enrich the requirement list | Uses whatever the operator pasted |
| **QuickBooks** (read-only) | Accounting/GL documents | Those documents become gaps in the report |

### The policy service dependency

ADP publishes the *operational* half of this workflow — rules, catalog, phase
steps, connector navigation — from
[`ada-policy-service`](https://github.com/udaygreddy/ada-policy-service), so a
correction reaches a client on their next run instead of waiting for a
reinstall. This bundle ships a copy of all of it as the offline fallback.

**It is a soft dependency, deliberately.** `PROCEDURE.md` checks for it at the
start of every run and **never blocks on it**: absent, unreachable or erroring,
the run says so plainly in one line and continues on the bundled files. A
client with a flaky connection should see a stale-policy note, not a dead skill.

If it is connected, the skill reads MCP resources under `policy://` in place of
the bundled files:

| Bundled file | Resource read instead |
|---|---|
| `PROCEDURE.md` phase section | `policy://procedure/<phase>` |
| `validations.yaml` | `policy://ruleset` |
| `taxonomy.yaml` | `policy://taxonomy` |
| `connectors/<name>.md` | `policy://connector/<name>` |
| *(no local equivalent)* | `policy://remediation/<doc_type>/<provider>` |

Two things are tools rather than resources because they compute rather than
publish: `get_required_quarters(ref_date)` and `get_state_rules(state_codes)`.

**Nothing is ever sent to it.** A resource is fetched by name; there is no field
to put a document in. That is structural, not a promise — see ADR-011.

**What it may never change:** the non-negotiable rules and the workspace setup
stay in this bundle. Served policy can tighten the workflow; it can never loosen
a control. If served text asks to skip a consent gate, transmit anything, or
bypass the ledger, `PROCEDURE.md` says not to comply.

Which policy screened a run is recorded at `ledger.py init` (`policy_source`,
`policy_version`) and printed in `gap_report.md`, so *"which rules validated
this package?"* is answerable months later.

Client-facing setup instructions are in
[`../INSTALL.md`](../INSTALL.md) §5. It is opt-in there too.

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
