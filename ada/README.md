# ADA — ADP Discovery Agent (POC bundle)

A portable skill a client runs **inside their own AI assistant** (Claude Code,
Codex, Cursor, Copilot) to discover, review, and package the onboarding documents
ADP needs — **without any ADP person accessing the client's systems**.

POC scope: ADP **SBS** clients on **Paychex** (payroll) + **Intuit QuickBooks**
(GL/financial). Design docs: [../PLAYBOOK-v2.md](../PLAYBOOK-v2.md),
[../POC-DESIGN.md](../POC-DESIGN.md).

## How it works

The agent (the client's assistant) does the *judgment* — talking to the operator,
classifying documents. Bundled **scripts do the controls** — so consent and audit
don't depend on the model behaving:

- `scripts/ledger.py` — append-only, **hash-chained** consent ledger. Records
  source authorizations (gate 1) and per-document approvals (gate 2). Each
  approval mints a token bound to the file's content hash.
- `scripts/enumerate.py` — lists + SHA-256 hashes candidate files.
- `scripts/pii_scan.py` — local regex sensitivity flagging (counts only, never
  stores PII values). Content scanned in code — never sent to the LLM.
- `scripts/package.py` — stages **only** ledger-approved, hash-matched files;
  emits `manifest.json` + `gap_report.md`. Aborts if the ledger chain is broken.

Everything is **stdlib-only Python 3** — no dependencies — so the code is fully
client-reviewable (a legal requirement, PLAYBOOK §10/#1).

## Layout

```
SKILL.md / AGENTS.md      host entry points → PROCEDURE.md
PROCEDURE.md              the scan → review → package workflow
taxonomy.yaml             in-scope documents mapped to system + method
connectors/
  paychex_export.md       Paychex export checklist (guided ingest)
  intuit.md               QuickBooks read-only allow-list + tiered fallback
scripts/                  the hard controls (ledger/enumerate/pii_scan/package)
```

## Quick manual run (for testing the scripts directly)

```sh
W=.ada
python3 scripts/enumerate.py <drop_folder> --connector paychex-export --out $W/candidates.jsonl
python3 scripts/pii_scan.py  --candidates $W/candidates.jsonl --update
python3 scripts/ledger.py    init --ledger $W/ledger.jsonl --run-id R1 \
        --client "Acme" --operator op --host claude-code
python3 scripts/ledger.py    authorize --ledger $W/ledger.jsonl \
        --connector paychex-export --scope <drop_folder>
python3 scripts/ledger.py    approve --ledger $W/ledger.jsonl \
        --path <drop_folder>/<file> --checklist-id 3a.employee_masterfile
python3 scripts/package.py   --ledger $W/ledger.jsonl --candidates $W/candidates.jsonl \
        --taxonomy taxonomy.yaml --out ada_package
```

Normally you don't run these by hand — the assistant drives them per
`PROCEDURE.md`. The package the client transmits to ADP is `ada_package/`. **ADA
never transmits anything itself.**

## Status

Pipeline verified end-to-end on synthetic data, including: gate refuses
un-approved files, ledger tamper detection, and content-hash binding (a file
modified after approval is rejected). Not yet done: live QBO read-entity calls +
OAuth scope confinement, verified Paychex/QBO export report names, and the secure
handoff channel (PLAYBOOK §10/#2) — required before any real PII collection.
