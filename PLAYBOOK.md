# ADA — Host-Neutral Playbook

**ADA (ADP Discovery Agent)** — a portable procedure that a client runs inside
their *own* AI assistant (Claude, Cursor, Copilot, Codex, ChatGPT) to discover,
review, and package the onboarding documents ADP needs — without any ADP person
touching the client's systems.

This document is the **core**. It is deliberately host-agnostic prose. Each host
gets a thin wrapper (`SKILL.md`, `AGENTS.md`, `.cursor/rules`,
`copilot-instructions.md`, a Custom GPT) that points the host's agent at this
procedure. Nothing here assumes a specific vendor.

---

## 1. Why this exists (the boundary that drives every design choice)

ADP implementation associates are legally barred from accessing client systems.
ADA moves the **data-access action** from the associate to the client. Therefore:

- ADA ships **instructions, not a service**. It never phones home. ADP operates
  no endpoint in the loop.
- The reasoning is done by the **client's already-approved assistant**, under the
  client's own credentials and org policy. No new LLM key, no new data-processing
  review, no content leaving any boundary it wasn't already allowed to cross.
- The real deliverable is not just files — it is **provable consent**: an
  append-only record that ADP never reached in and the client approved every
  access and every outbound file.

If a design choice weakens that record, it is wrong, however convenient.

---

## 2. Operating principles

1. **Client-run, client-credentialed.** Every system is reached with the
   client's own access, inside the client's environment.
2. **Two consent gates.** (a) connecting/authorizing a source, (b) including a
   specific document in the outbound package. Neither is implied by the other.
3. **Nothing leaves until packaged.** ADA reads and stages locally. The only data
   that crosses to ADP is a package the client explicitly assembles and transmits
   by hand.
4. **Metadata before content.** Classify on filename/path/folder/type first. Read
   document content only when necessary, and never for PII-flagged files.
5. **Gaps are a deliverable.** "What's missing and where to find it" is as
   valuable to onboarding as the files themselves.
6. **Append-only audit.** Every access, match, and decision is logged with who,
   when, and what. The log is evidence.

---

## 3. Capability abstraction (what the host must provide)

ADA is defined against abstract capabilities. Each host wrapper maps these to
native tools or MCP connectors; the procedure never names a vendor tool.

| Capability | Meaning | Typical host mapping |
|---|---|---|
| `LOCAL.list(path)` / `LOCAL.read(ref)` | Enumerate & read local files | Native filesystem tools |
| `SOURCE.list(connector, query)` | Enumerate candidates in a cloud source | MCP connector (Drive, SharePoint, Gmail, QuickBooks…) |
| `SOURCE.fetch(connector, ref)` | Retrieve one item's content/metadata | MCP connector |
| `PII.scan(text)` | Local pattern scan for sensitive data | In-procedure regex; never an external call |
| `OUT.write(path, bytes)` | Write staged files & reports locally | Native filesystem tools |
| `ASK.confirm(prompt)` | Get an explicit human decision | The host's normal chat turn |

**Source connectors are pluggable.** The POC requires only `LOCAL`. Cloud sources
are added by declaring a connector that satisfies `SOURCE.*`. "Supports all
systems" = this interface exists; each system is one connector behind it.

---

## 4. The checklist taxonomy

The master list lives in [documentstocollect.md](documentstocollect.md). ADA
consumes it as a structured taxonomy. Each item:

```yaml
- id: "1.msa"                      # stable identifier
  section: "1. Sales & Contracting"
  label: "Master Service Agreement (MSA)"
  synonyms: ["MSA", "master service agreement", "master agreement"]
  expected_formats: ["pdf", "docx"]
  sensitivity: "low"              # low | medium | high(PII)
  source_hints: ["drive", "email", "contracts folder"]
  collection_tier: "loose-file"   # loose-file | api-pull | email | portal | generated
```

`collection_tier` is the difficulty signal that drives POC scope:

- **loose-file** 🟢 — sits in a drive/folder; find + classify. *(POC target.)*
- **api-pull** 🟡 — structured data from an accounting/payroll system via connector.
- **email** 🟡 — attachment search.
- **portal** 🔴 — locked in an incumbent vendor's UI; needs browser automation.
- **generated** 🔴 — produced (POA/CAA/RAA), not collected.

---

## 5. The procedure

Three phases. A host may run them as one conversation or three commands.

### Phase A — SCAN (discover candidates)

1. Load the taxonomy (§4). Confirm with the operator which sections are in scope.
2. For each authorized source (gate 1 — `ASK.confirm` before first access to each
   source; log it):
   - `SOURCE.list` / `LOCAL.list` to enumerate candidates.
   - For each candidate, classify **metadata-first** against the taxonomy →
     `{item_id, confidence, rationale}`. Read content only if metadata is
     ambiguous **and** the file is not PII-flagged.
   - Run `PII.scan` on filename/metadata; if matched, tag `sensitivity: high`
     and **do not** send its content anywhere for classification.
3. Produce a candidate set: each candidate mapped to zero or more checklist items
   with a confidence and a sensitivity flag.

### Phase B — REVIEW (human consent, per document)

1. Present candidates grouped by checklist item, highest confidence first.
2. For each, the operator decides **include / exclude / defer** (gate 2). PII-
   flagged items show a `⚠ sensitive — confirm` prompt and are never pre-checked.
3. Record each decision (who, when, decision, item) in the consent log.
4. Show the running gap view: items still `missing` or `partial`.

### Phase C — PACKAGE (assemble handoff)

1. `OUT.write` the approved files into a staging folder, organized by section.
2. Emit `manifest.json` (§6), a human-readable **gap report**, and the
   **consent log**.
3. Stop. The operator reviews the staging folder and transmits it to ADP
   manually. ADA does not send anything.

---

## 6. Output artifacts

### `manifest.json`

```json
{
  "run": {
    "id": "uuid",
    "timestamp": "ISO-8601",
    "client": "Acme Corp",
    "operator": "person who ran ADA (client side)",
    "host": "claude-code | cursor | copilot | codex | chatgpt",
    "ada_version": "0.1.0"
  },
  "sources_accessed": [
    { "connector": "local", "scope": "/Onboarding", "consented_at": "ISO-8601" }
  ],
  "items": [
    {
      "checklist_id": "1.msa",
      "label": "Master Service Agreement (MSA)",
      "status": "found | partial | missing",
      "candidates": [
        {
          "source": "local",
          "source_ref": "/Onboarding/Contracts/MSA_Acme_2023_signed.pdf",
          "filename": "MSA_Acme_2023_signed.pdf",
          "confidence": 0.94,
          "sensitivity": "low",
          "decision": "included | excluded | deferred | pending",
          "decided_by": "operator",
          "decided_at": "ISO-8601"
        }
      ]
    }
  ],
  "gaps": [
    { "checklist_id": "4.a.941", "label": "Prior quarter 941 returns",
      "reason": "not found", "source_hint": "incumbent payroll portal" }
  ]
}
```

### Gap report (human-readable)

> **Acme Corp — Discovery, 2026-06-18**
> 23 of 41 in-scope items collected.
> ✅ Collected: MSA, SOW, benefit plan PDFs, onboarding packet, company policies…
> ⚠ Found, pending review (sensitive): 4 paystubs, 1 voided check
> ❌ Still needed: 941 returns (payroll portal), D&B documentation, POA forms (to be generated)

### Consent log (append-only)

One line per event: `timestamp · actor · action · target`. Covers source
authorizations and per-document decisions. This is the evidence ADP never
reached in.

---

## 7. Sensitive data handling (PII)

- Local `PII.scan` looks for SSN, bank routing/account numbers, EIN, and similar.
- Matched files are tagged `high` sensitivity: classified on **metadata only**,
  never auto-included, and surfaced behind an explicit confirm in REVIEW.
- POC does **not** auto-redact. Redaction is a later capability; for now the
  human decides per document.

---

## 8. POC scope (v1)

- **Sources:** `LOCAL` only (interface ready for cloud connectors next).
- **Items:** the `loose-file` tier — §1 Sales/Contracting, §7E benefit plan PDFs,
  §8B onboarding, §12 policies.
- **PII:** collect-but-flag per §7.
- **Out of scope:** portal scraping, POA/CAA/RAA generation, auto-redaction,
  multi-host wrappers.
- **Definition of done:** running ADA over a sample client folder produces a
  correct staging folder + manifest + gap report + consent log, with sensitive
  files held for explicit review.

---

## 9. Host adapters (later, not POC)

Each wrapper is thin and points at §5. Mapping notes:

| Host | Wrapper file | Capability mapping notes |
|---|---|---|
| Claude Code / Cowork | `SKILL.md` (Agent Skill) | Richest: bundle helper scripts, progressive disclosure; MCP for sources |
| Cursor | `.cursor/rules` | Same procedure as rules; MCP for sources |
| GitHub Copilot | `copilot-instructions.md` / `AGENTS.md` | Agent mode + MCP in VS Code |
| OpenAI Codex | `AGENTS.md` | Repo-rooted; MCP for sources |
| ChatGPT (chat) | Custom GPT / Project | Trimmed procedure; connectors only, no local FS — cloud sources only |

The core procedure (§5), taxonomy (§4), and artifacts (§6) do **not** change per
host. Only the capability bindings (§3) and the wrapper file do.
