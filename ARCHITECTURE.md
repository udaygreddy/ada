# ADA — Architecture &amp; engineering guide

Audience: the tech lead or architect who owns this next. Everything here is the
*reasoning* — what we chose, what we rejected, what must never break, and where
the bodies are buried. For the workflow itself see
[`ada/PROCEDURE.md`](ada/PROCEDURE.md); for leadership framing see
[`STATUS.md`](STATUS.md).

---

## 1. The constraint that generates the design

ADP implementation associates are **legally barred from accessing client
systems**. Every other design choice follows from that single fact.

The naive solution — build a service that pulls documents from clients — is
exactly what's prohibited. So ADA inverts it: the client's *own* AI assistant,
already authorized in their environment, does the collecting. ADP ships
**instructions and reviewable code**, never a connection.

That inversion creates the real engineering problem, and it's worth stating
precisely because it's non-obvious:

> If the client's AI does the work, and ADP can't observe it, **how does anyone
> trust that consent was actually obtained?**

An LLM narrating "I asked the user and they approved" is not evidence. The
answer is the architecture's core idea, below.

---

## 2. Core idea — the model judges, the code controls

| Model (client's own LLM) | Bundled code (stdlib Python) |
|---|---|
| Read the ADP request, classify documents | Enumerate files, compute SHA-256 hashes |
| Judge every acceptance check | Extract text, mask PII, resolve calendars |
| Talk to the operator | Write the append-only, hash-chained ledger |
| Explain gaps and remedies | **Refuse to package anything the ledger hasn't blessed** |

The split isn't stylistic. It exists because **judgment and enforcement have
opposite requirements**:

- *Judgment* must handle messy reality — PDF layouts, ambiguous document types,
  print-date footers. Rules-based code is brittle here; a model is not.
- *Enforcement* must be provable and identical every run. A model is exactly the
  wrong tool; deterministic code is exactly right.

**The invariant this buys:** the model can misclassify, hallucinate, or be
talked into anything by a persuasive operator — and it still **cannot** produce
a package containing a file the ledger hasn't approved against a matching
content hash. Correctness of judgment degrades gracefully. Correctness of
consent does not degrade at all.

Every future change should be tested against that sentence.

---

## 3. Invariants — do not break these

1. **ADA never transmits.** No egress of document content, ever. It writes a
   local staging folder; the client transmits it. Adding a "just email it for
   me" convenience would destroy the legal premise.
2. **No file enters the package without a ledger approval token** whose
   `content_hash` matches the file's current bytes. Enforced in `package.py`,
   not in prose.
3. **The ledger is append-only and hash-chained.** Any edit to a prior entry
   breaks the chain; `package.py` aborts on a broken chain.
4. **Validation `fail` blocks approval** unless an operator override is
   explicitly recorded (`--override`), which is itself written to the chain.
5. **Document content is data, never instructions.** Text inside a collected
   file — or a pasted email — must never be executed as a directive.
   (Prompt-injection surface; see §8.)
6. **PII is masked in code before it reaches the model**, and PII-flagged files
   are never auto-included.
7. **Stdlib only.** No third-party dependencies, so the entire bundle is
   readable by a client's security reviewer in one sitting. This is a *legal*
   requirement dressed as a technical one — see ADR-002.

---

## 4. Architecture decision records

Condensed to decision → rationale → what we rejected. Several of these were
reversals; the reversals are the instructive part.

### ADR-001 — Ship a skill, not a CLI or a service
**Decision.** Distribute instructions + scripts that run inside the client's
existing assistant.
**Why.** A service reintroduces the forbidden ADP→client connection. A
standalone CLI needs an LLM key and a fresh security review at every client; the
client's assistant is *already approved* under their org policy, so ADA
introduces no new data-processing surface.
**Rejected.** Hosted service (illegal by premise); standalone CLI (per-client
approval friction, key management).

### ADR-002 — Stdlib-only, zero dependencies
**Decision.** Every script uses only the Python standard library.
**Why.** Client security teams must be able to read and approve the code.
Dependencies mean a supply chain, a vendoring story, and a much larger review.
**Cost, accepted.** We hand-rolled a PDF text extractor and a PDF *writer* for
fixtures. Both are real code we now own. Worth it — but see §8, this is the
weakest engineering trade in the system.

### ADR-003 — Consent as code, not as prose
**Decision.** Two gates (authorize source, approve document) are script calls
that write ledger entries; `package.py` reads the ledger as the only admission
list.
**Why.** The original design had gates as instructions. A design review killed
that: *"a control whose worth is 'the model promised to ask' is not a control."*
**Rejected.** Trusting the model's narration; post-hoc audit only.

### ADR-004 — Validation judgment moved from code to the model *(reversal)*
**Decision.** Code extracts and resolves; the model decides pass/warn/fail.
**Why.** The deterministic version took min/max of all dates in a file. A Q2
payroll register with a *"Report generated 07/20/2026"* footer failed
spuriously. Real documents are too varied for regex. A model reading the text
distinguishes a check-date column from a print-date footer trivially.
**Rejected.** Deterministic verdicts (kept as an optional cross-check for clean
CSVs). Note this did **not** weaken enforcement — the *verdict* became
model-made, the *gate* stayed code-made.

### ADR-005 — Two tiers of acceptance criteria, additive only
**Decision.** Explicit criteria (what ADP wrote in *this* request) are judged
alongside implicit standing rules (`validations.yaml`). Explicit can only
*tighten*.
**Why.** ADP's email says "PDF only" or "one file per check date"; a document
can satisfy every standing rule and still be rejected. But the reverse must be
impossible: a client email saying "PDF is fine" must never waive
`ssn-unmasked`. Subtractive precedence would let a casual sentence disable a
control.
**Rejected.** Explicit-overrides-implicit (unsafe); implicit-only (misses what
ADP actually asked).

### ADR-006 — Rules as data, not code
**Decision.** `validations.yaml` holds acceptance checks as prose questions the
model answers. Adding a rule = adding YAML.
**Why.** ADP's rejection reasons are discovered operationally, not designed up
front. Rules must ship without a code release. This is the learning loop.
**Consequence, unresolved.** Rules can now change without engineering review.
Governance is an open question (§9).

### ADR-007 — Requirements come from the request, not the catalog *(reversal)*
**Decision.** The per-client requirement list is derived from ADP's request
(pasted text primary, mailbox enrichment). `taxonomy.yaml` is a *catalog* of
how/where to collect a document type — not the list of what's needed.
**Why.** Originally the static checklist drove collection, which is backwards:
ADP tells each client what *they* need. Getting this wrong also produced a UX
bug where a pasted request was ignored and the client was re-asked.
**Rejected.** Static master checklist as the requirement source.

### ADR-008 — Provider knowledge lives in connectors, not the pipeline
**Decision.** Payroll document types are `system: payroll`; per-provider report
names and navigation live in `connectors/*_export.md`.
**Why.** 12 providers exist in ADP's guide. If provider specifics leaked into
the taxonomy or scripts, each new provider would be a code change. Now it's a
markdown file.
**Validation of the choice.** Adding Paylocity touched zero pipeline code.

---

## 5. System anatomy

```
ada/
  SKILL.md / AGENTS.md   host entry points (Claude / Copilot-Cursor-Codex)
  PROCEDURE.md           the workflow — the real "program" the model runs
  taxonomy.yaml          18 doc types → system, method, sensitivity, doc_type
  validations.yaml       24 acceptance checks, by doc type + coverage
  connectors/            per-source navigation & tool allow-lists
  scripts/               1,541 lines, stdlib only
```

| Script | Lines | Responsibility |
|---|---|---|
| `ledger.py` | 318 | Hash-chained ledger; requirements, facts, approvals, gate |
| `validate.py` | 580 | Text/PDF extraction, PII masking, calendar resolution, format evidence |
| `package.py` | 284 | Admission control + manifest/gap report |
| `pii_scan.py` | 105 | Sensitivity flagging (counts only, never values) |
| `enumerate.py` | 72 | List + SHA-256 hash candidates |
| `requirements.py` | 88 | Per-client requirement records |
| `_ada.py` | 94 | Shared hashing, canonical JSON, minimal YAML reader |

**Data flow.** ADP request → requirements (ledger) → candidates (enumerate +
pii_scan) → evidence (`validate.py --extract`) → **model judgment** → approval
token (ledger) → staged package (`package.py`).

**Where state lives.** All of it in `./.ada/ledger.jsonl` — a single
append-only, hash-chained file. `candidates.jsonl` and `requirements.jsonl` are
convenience caches, reconstructible from the ledger. The ledger is the system of
record; treat everything else as derived.

---

## 6. Extension points

**Add a payroll provider** — write `connectors/<provider>_export.md` with the
report navigation, add a remediation line per doc type in `validations.yaml`,
extend the provider question in `PROCEDURE.md` Phase A. No script changes.

**Add an acceptance rule** — one entry under the doc type in `validations.yaml`
(`id`, `severity`, `judge` question, optional per-provider `remediation`), bump
`ruleset_version`, add a positive and negative case to `tests/make_fixtures.py`
plus a row in `TEST-CASES.md`. No code unless the rule needs new deterministic
evidence.

**Add a requirement source** (e.g. Salesforce Case) — new `connectors/*.md`, new
`--source-kind` value. The downstream pipeline is unchanged by design; only
provenance differs.

**Add deterministic evidence** — extend `validate.py --extract` output (as
`file_format` was added). Rule of thumb: code supplies *facts*, never verdicts.

---

## 7. Testing strategy

Two kinds, because the system has two kinds of behavior:

- **Code-enforced gates** → `tests/run_gate_tests.sh`, 5 assertions, exit
  non-zero on failure. These protect the invariants in §3.
- **Model judgment** → 42 case folders + 42 sample prompts. *Cannot* be asserted
  by script; the expected column is what a correct judgment produces.

Three deliberate anti-cheating properties, each learned the hard way:

1. **Realistic filenames.** A fixture named `register_fail_q1.pdf` can be judged
   from its name without reading a byte.
2. **Scenario-only folder names.** No pass/fail/warn in any path.
3. **Answer-free prompts** — and *uniform phrasing across pass and fail cases*,
   after a check caught that pass-case prompts asked "is the set complete?" while
   fail-cases asked "is something missing?" — a tell a model could learn.

**What the suite does not prove:** nothing has run against a real client, a live
Paychex/Paylocity tenant, or a real ADP email. Judgment quality has never been
measured against documents ADP actually rejected.

---

## 8. Known weaknesses — read before extending

Ranked by how much they'd embarrass you in a review.

1. **Hand-rolled PDF handling (ADR-002's bill).** We wrote both a PDF text
   extractor and a PDF writer. The writer bug shipped *unopenable* fixtures that
   our own extractor read happily — the suite passed against files no human
   could open. Any format work here needs adversarial testing against real
   viewers, not just round-tripping through our own code.
2. **Injection defense is stated, not enforced.** Invariant §3.5 is prose in
   `PROCEDURE.md`. The agent holds live mailbox and QuickBooks credentials while
   reading attacker-influenceable documents. Containment is undesigned.
3. **Read-only allow-lists are prose too.** "Never call QBO write tools" and
   "mailbox read tools only" are instructions, not structural constraints —
   exactly the class of weakness ADR-003 fixed for consent, still unfixed here.
4. **Tamper-evident ≠ tamper-proof.** A determined client can regenerate the
   whole chain. Co-signing at ADP ingest is the upgrade path.
5. **No CI.** The invariants have a test script and nothing runs it
   automatically.
6. **Distribution/staleness is real, not theoretical.** Three stale installs
   were found on a single developer machine; a stale copy silently reintroduces
   fixed bugs and looks like the fix failed.
7. **Sandboxed hosts.** A live run hit a host that blocked executing scripts
   from the skill directory. `$ADA_HOME` resolution needs a fallback story.
8. **No resumability.** Real discovery spans days; a run can't be resumed.

---

## 9. Open governance questions

Engineering can't answer these alone, and they block scale more than any feature:

- **Who approves rule changes?** `validations.yaml` ships behavior without a
  code review. Needs an owner and a change process.
- **What supersedes an old install?** No version-aware distribution today.
- **Who owns the secure handoff channel** — the one hop where real PII crosses
  to ADP, currently undesigned.
- **Does ADP legal permit ADP-authored scripts** executing on client data at
  all? Unanswered since day one. It gates the whole approach.

---

## 10. Onboarding path for a new engineer

1. Read [`ada/PROCEDURE.md`](ada/PROCEDURE.md) — it *is* the program.
2. Run `tests/run_gate_tests.sh`, then read `ledger.py` `_append`, `verify`, and
   `valid_tokens`, plus the admission check in `package.py`. That's the trust
   model in ~80 lines.
3. Print a prompt (`python3 tests/make_prompts.py payroll-register-prior-quarter`)
   and run it against an installed skill. Watch a judgment happen.
4. Read `validations.yaml` top to bottom — it's the domain knowledge.
5. Skim §8 above before proposing anything.

**Local, uncommitted:** `spara.md` is ADP's internal onboarding guide and the
source for the provider navigation and acceptance rules. It is deliberately
gitignored — do not commit it. Everything derived from it lives in
`connectors/` and `validations.yaml`.
