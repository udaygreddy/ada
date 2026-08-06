# ADA — Executive status report

**ADP Discovery Agent** · prepared 2026-07-27 · owner: Uday Gangireddy

*Engineering counterpart: [`ARCHITECTURE.md`](ARCHITECTURE.md) — decision
records, invariants, and known weaknesses.*

---

## Legal approval

**Approved.** Covers both questions that were bundled into the ask:

1. ADP-authored scripts executing inside client environments.
2. The client's assistant calling an **ADP-operated policy endpoint**
   (the pull-only MCP — see [`MCP-DESIGN.md`](MCP-DESIGN.md), ADR-009).

This clears what was the longest-lead item in the programme. The secure handoff
channel is now the top blocker.

> **⚠ Conditions are not yet recorded.** Approvals of this kind normally carry
> constraints — client-reviewable source, no client data egress, disclosure,
> retention limits. Any such conditions must be written down here and, wherever
> they are testable, encoded as invariants in
> [`ARCHITECTURE.md`](ARCHITECTURE.md) §3 with a test that fails when violated —
> the way pull-only is enforced in `ada-policy-service`. A condition that lives
> only in an approval email is a condition that gets violated in six months.

---

## Bottom line

ADA works end to end as a **functioning prototype**, and its core architectural
bet — the client's own AI does the judgment while bundled code enforces consent
and audit — is built and verified.

It is **not yet ready for a client**. Two blockers are non-engineering: a legal
ruling on shipping ADP-authored code into client environments, and a secure
channel for the finished package (which contains W-2s, SSNs and bank details).
Everything to date has been validated on **synthetic data only** — no real
client, no live Paychex/Paylocity tenant, no real ADP request email.

The honest summary: **the hard design problems are solved; the hard
organizational and real-world problems are not yet started.**

---

## What exists today

| Area | Built |
|---|---|
| Workflow | Phase 0 intake → A collect → B validate → B.5 coverage → C package |
| Controls | 7 stdlib-only Python scripts (~1,470 lines), no dependencies |
| Document catalog | 18 document types mapped to source system + method |
| Acceptance rules | 24 validation checks, per doc type, mined from ADP's onboarding guide |
| Payroll providers | Paychex, Paylocity (guided export) |
| Accounting | Intuit QuickBooks (read-only) |
| Requirement sources | Pasted ADP request (primary), any connected mailbox (enrichment) |
| Hosts | Claude (Cowork / Desktop / Code), GitHub Copilot, Cursor, Codex |
| Packaging | `.plugin`, skill `.zip`, and apm — all from one source |
| Tests | 39 case folders / 42 documents, 39 sample client prompts, 4 code-enforced gate regressions |

**The trust model, which is the product's real differentiator:**
ADP never logs in. Two consent gates are enforced by scripts, not by the model's
good behaviour. Every authorization, approval and verdict lands in a hash-chained
ledger. A file the ledger hasn't blessed cannot enter the package — even if the
model misjudges it.

---

## Proven vs. unproven

Being precise about this matters more than the feature list.

**Proven (automated, repeatable):**
- Consent gate refuses un-approved files; override requires an explicit, logged act
- Content-hash binding — a file altered after approval is rejected
- Ledger tamper detection; packaging aborts on a broken chain
- PII masked in code before any document text reaches the model
- Validation logic across 39 positive/negative cases
- UX: a live blind CLI run confirmed the skill greets a client correctly
  ("What's your company name?" / "Which payroll provider are you switching from?")

**Unproven (no real-world exposure):**
- Never run with a real client or a real ADP request email
- Paychex/Paylocity click-paths come from ADP's guide — **never verified against
  a live tenant**; report names and menus may differ
- QuickBooks read-only pulls never executed against a real QBO account
- Validation judgment never measured against documents ADP actually rejected
- **The core value claim — fewer ADP↔client round trips — has no data behind it**

---

## Top risks

| # | Risk | Impact | Status |
|---|---|---|---|
| 1 | **Secure handoff**: final package (W-2s, SSNs, bank proof) has no defined transmission channel | Weakest link undoes every upstream control | **Now the top blocker** — undesigned |
| 2 | ~~**Legal**: ADP-authored scripts as access-by-proxy~~ | — | ✅ **APPROVED** — covers both client-side scripts *and* the client's assistant calling an ADP policy endpoint. **Conditions attached to the approval are not yet recorded here — see §Legal approval** |
| 3 | **Zero field validation** | Click-paths and value claim may not survive contact with a real client | Not started |
| 4 | **Windows** | Most clients are Windows; scripts assume `python3` and bash-style paths | Known, deferred |
| 5 | **No CI** | Controls are the product's credibility and nothing guards them per-change | Tests exist; automation doesn't |
| 6 | **Distribution/staleness** | Three stale installs already found on one machine; a stale copy silently reintroduces fixed bugs | Observed, unmanaged |
| 7 | **Sandboxed hosts** | Live test hit a host that blocked executing scripts from the skill directory | Newly observed, unresolved |
| 8 | **Coverage** | 2 of 12 payroll providers in ADP's guide are implemented | By design so far |

---

## Path to enterprise implementation

Four phases. Phase 1 is sequential; later phases can overlap.

### Phase 1 — Make it real (unblocks everything)
*Target: one successful onboarding with a friendly client.*

- ~~**Obtain the legal ruling**~~ — ✅ **done, approved.** Covers both
  ADP-authored scripts running client-side and the client's assistant calling
  an ADP-operated policy endpoint. See §Legal approval below.
- **Design the secure handoff** — encryption at rest, transmission mechanism,
  package integrity ADP can verify on receipt, and post-transmission cleanup.
  Likely reuses an existing ADP secure-upload portal.
- **Verify against live tenants** — walk a real Paychex and Paylocity account and
  correct the report names, menu labels and navigation.
- **Windows parity** — `python3`/`python` resolution, PowerShell-safe paths.
- **Resumability** — real discovery spans days; support resuming a run.
- **Pilot with 1–2 friendly clients**, instrumented to measure round trips.

### Phase 2 — Harden (make it safe at scale)
- **CI on every change**: gate regressions, script compile, artifact build, and a
  validity check on generated fixtures (a bug that shipped unopenable PDFs would
  have been caught by this).
- **Automated eval harness** — score the 39 judgment cases on model or rule
  changes, so upgrades don't silently regress validation quality.
- **Versioning & release discipline** — semver, changelog, version stamped in
  every run manifest, and a single distribution channel that supersedes old
  installs instead of accumulating them.
- **Security hardening** — make the mailbox read-only allow-list structural
  rather than prose; concrete prompt-injection containment; independent review.
- **PII lifecycle** — retention guidance and deletion after transmission.
- **Package integrity** — signature or checksum ADP verifies at ingest, closing
  the audit loop end to end.

### Phase 3 — Scale coverage
- **Remaining 10 payroll providers** (Gusto, Heartland, iSolved, Paycor, Asure,
  PrimePay, OnPay, SurePayroll, QuickBooks Online/Desktop payroll). Each is a
  connector document — the pipeline doesn't change.
- **State-specific intake rules** (DC/OK POA, Iowa BEN, Oregon BIN, sick-leave
  minimums) — these change *which documents are required*.
- **Forms that must be completed, not collected** (POA, Form 8655/RAA) — today
  ADA records the requirement and stops. These gate ADP's ability to file taxes.
- **Salesforce Case as requirement source** — structured, authoritative, and
  removes email-spoofing risk.
- **Feedback loop to ADP** — implementation currently learns nothing until the
  client sends the package.

### Phase 4 — Operate
- **Telemetry**: aggregate, opt-in, no client data — completion rates, where
  clients stall, which rules fire most.
- **Support escalation** — ADP's guide already defines live-rep handoff
  (including out-of-scope states); ADA has no path to it.
- **Rule governance** — `validations.yaml` is data, so rules can ship without a
  release. Decide who approves changes and how they're versioned.

---

## Decisions needed from leadership

| # | Decision | Blocks |
|---|---|---|
| 1 | ~~Legal ruling~~ | ✅ **Resolved — approved**, both scripts and the MCP endpoint |
| 2 | Who owns the secure handoff channel — reuse an existing ADP portal? | **Now the top blocker.** Any real PII collection |
| 3 | Approve a 1–2 client pilot and provide tenant access for verification | Field validation |
| 4 | Which team owns the ruleset, releases and support escalation | Phase 2 onward |
| 5 | Repo home and licensing (currently a personal repo, marked `UNLICENSED`) | Distribution at scale |

---

## How to measure success

The product exists to reduce back-and-forth. Instrument that directly:

- **Round trips per onboarding** — baseline today vs. with ADA *(primary)*
- **First-time acceptance rate** — documents accepted without a re-request
- **Time from ADP request → complete package**
- **Client completion rate** and where runs are abandoned
- **Validation precision/recall** vs. what ADP implementation actually rejects

None of these have a baseline yet. Capturing the current-state numbers for a
handful of onboardings would cost little and would make the pilot's result
interpretable.

---

## Recommendation

Do not add features next. Spend the next increment on **Phase 1**: get the legal
ruling, design the handoff channel, and run one instrumented pilot. Those three
answers determine whether ADA becomes a product or stays a very well-built
prototype — and no amount of additional provider coverage changes that.
