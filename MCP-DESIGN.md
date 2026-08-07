# ADA — ADP policy MCP: design

**Status: design only.** No code exists for this yet, and none should be written
until the dependency in §8 is cleared. Companion to
[`ARCHITECTURE.md`](ARCHITECTURE.md) (see ADR-009).

---

## 1. The problem this solves

Today every rule, catalog and click-path ships *inside* the skill. Changing a
validation rule or fixing a provider's navigation means redistributing the skill
and hoping every client reinstalls.

That is already failing. During testing, **three stale installs were found on a
single machine**, each silently reintroducing bugs that had been fixed. In
production the churn only gets worse, because the two things that change most
are exactly the two things that are hardest to redistribute:

- **Rules** — every ADP rejection reason should become a new validation.
- **Connector navigation** — provider UIs change on their schedule, not ours.

Putting those behind an ADP-controlled MCP means a rule lands once and applies
to every client's next run. That is the right instinct.

## 2. The boundary that decides everything

ADA's legal premise is that ADP operates no endpoint in the client's data path
(ADR-001), and invariant §1 is *"ADA never transmits — no egress of document
content, ever."* An MCP is an endpoint. Whether that breaks the premise depends
entirely on **which direction data moves**.

- **Policy flows OUT** (ADP → client): rules, catalogs, navigation, forms,
  remediation. ADP is **publishing**, not accessing. The client's assistant
  reads ADP's rulebook; ADP sees none of the client's documents. Compatible.
- **Client data flowing IN would end the argument.** The moment a document,
  extracted text, or PII crosses to ADP to be validated, ADA becomes a service
  that processes client data and the entire premise collapses.

> **The MCP is strictly pull-only. No write tools exist.**
>
> This is deliberately absolute rather than "we're careful about what we send
> back." A rule with no exceptions can be verified by reading the tool list; a
> rule with exceptions has to be re-argued at every change.

**New invariant (ARCHITECTURE §3.8):** *No MCP call carries document content,
extracted text, or PII, and no MCP tool writes.* Parameters are limited to
non-sensitive scalars: `doc_type`, `provider`, state code, reference date,
ruleset version, ADP case id.

**Stdlib-only survives.** MCP is consumed through the *host's* tool interface,
not a Python client library, so the bundle adds no dependency and invariant §7
is untouched.

## 3. Deployment shape

**Internet-reachable, ADP-controlled.** Clients run the skill on their own
machines and call the service over the internet; ADP owns the change control
behind it.

Worth stating plainly, because "behind the ADP firewall" describes the
**governance**, not the **network position**: this is a DMZ-hosted, publicly
reachable service with authentication, rate limiting, and an operational owner.
ADA has no runtime infrastructure today — this is the first piece.

## 4. What moves to the MCP

All ADP-owned policy. None of it involves client data.

| Served | Why it belongs on ADP's side |
|---|---|
| `validations.yaml` (rule catalog) | **The main win** — new rejection reason becomes a live rule, no reinstall |
| `taxonomy.yaml` (document catalog) | Doc types, sensitivity, source hints |
| Connector navigation (Paychex, Paylocity, Intuit, + the 10 unbuilt providers) | Provider UIs change on their own schedule |
| Per-provider `remediation` text | The round-trip killer; must always be current |
| State rules (IA BEN, OR BIN, DC/OK POA) | Regulatory; changes independently of the skill |
| Blank forms (POA, Form 8655/RAA) | ADP-owned documents the client must complete |
| Quarterly-timing policy | ADP's rule for which quarters to request |
| **Policy manifest + version** | Directly fixes the stale-install problem |

Deferred to Phase B: **per-client requirements from the Salesforce Case** —
removes email parsing and its spoofing surface. Still a pull; the parameter is a
case id, which is ADP's own identifier.

## 5. What must stay on the client — and why

| Stays local | Reason |
|---|---|
| `ledger.py` | It is the **client's** evidence, not ADP's. Must work offline and be inspectable by them. Hosting it would convert consent records into ADP telemetry |
| `pii_scan.py` + masking | Must run **before** anything could leave the machine |
| `enumerate.py`, `package.py` | Read local files; `package.py` is the admission gate (invariant §2) and must never depend on a network |
| `validate.py --extract` | Its output **is** client data |
| The judgment | The client's own model — the whole trust model (ADR-004) |
| A **procedure spine** | Bootstrap and offline operation; only the volatile parts are served |

The split is not arbitrary: **policy is ADP's to change, controls are the
client's to verify.** Anything a client's security reviewer must be able to read
and trust stays in the bundle they can read.

## 6. Design

```
Local skill (shipped)            ADP policy MCP (pull-only)      Client's model
  procedure spine          <---   rules, taxonomy, connectors,    judgment
  7 control scripts                remediation, forms, manifest
  bundled policy snapshot    (fallback when unreachable)
```

### Tool surface

Read-only. No parameter carries client data.

| Tool | Returns |
|---|---|
| `get_manifest()` | Current version of every policy artifact — staleness check |
| `get_ruleset()` | Validation rules + `ruleset_version` |
| `get_taxonomy()` | Document catalog |
| `get_connector(provider)` | Navigation for `paychex` \| `paylocity` \| `intuit` \| … |
| `get_remediation(doc_type, provider)` | Exact re-export fix |
| `get_required_quarters(ref_date)` | ADP's quarterly-timing policy |
| `get_state_rules(state_codes[])` | Conditional requirements by state |
| `get_form(form_id)` | Blank POA / 8655 |
| *(Phase B)* `get_requirements(case_id)` | Per-client requirement list |

There is no `report_*`, `submit_*`, or `upload_*`. If ADP implementation wants
status visibility, it comes from **ADP's own ingest of the delivered package** —
never from the client's machine.

### Offline behaviour — mandatory, not a nicety

The bundle ships a policy snapshot; fetched policy is cached in
`./.ada/policy/`. If the MCP is unreachable, the skill **falls back to the
snapshot, says so plainly, and continues**.

A local-first tool must not quietly become network-dependent. A client mid-run
with a flaky connection should notice a stale-policy warning, not a dead skill.

### Policy provenance

Record `policy_version` (and `ruleset_version`) at run init and in
`manifest.json`. This makes *"which rules screened this package?"* answerable
months later — necessary once rules change independently of releases, and it
pairs naturally with the existing version-stamping work.

### Integrity — and a distinction that must not blur

This introduces **two classes of text**, and conflating them would be a serious
bug:

| | Origin | Treated as |
|---|---|---|
| **Policy** | ADP, signed | **Instructions** — rules the model follows |
| **Documents / emails** | The client's systems, attacker-influenceable | **Data** — assessed, never executed (invariant §5) |

Invariant §5 says document content is never instructions. Served policy is the
exact opposite: it *is* instructions. That is only safe while the two are
distinguishable, which means **the policy bundle must be signed and verified
before use** — otherwise the only thing separating "ADP's rulebook" from
"attacker-supplied instructions" is the URL it arrived from.

Without signing, compromising one service injects instructions into every
client's assistant simultaneously — a materially larger blast radius than
tampering with a static skill on one machine.

## 7. Risks

1. **A new internet-facing service to build, secure and operate.** Accepted, but
   real scope: DMZ hosting, authn, rate limits, uptime ownership.
2. **Injection blast radius inverts** — mitigated by signing (§6).
3. **Metadata, even when pull-only.** Every call reveals who, when, and which
   document types are in play. Pull-only removes the *payload* concern, not the
   *metadata* one. Disclose it to clients; minimise access-log retention.
4. **Host friction.** MCP configuration differs per host and adds an install
   step versus today's self-contained skill.
5. **Availability becomes a client-visible failure mode** — mitigated by the
   snapshot fallback, which must be tested, not assumed.

## 8. Legal dependency — ✅ cleared

**Approved**, covering both halves of the ask: ADP-authored scripts running
client-side, *and* the client's assistant calling an ADP-operated policy
endpoint. Folding both into one ask was the right call — a ruling obtained
against the pre-MCP architecture would have had to be re-sought.

The service is built (`ada-policy-service`, private) and no longer blocked on
legal. **It is still blocked on the pre-launch items in §7 and the service
README** — signing above all, plus authn, rate limiting and a log-retention
policy.

> Conditions attached to the approval must be recorded in
> [`STATUS.md`](STATUS.md) §Legal approval and, where testable, encoded as
> invariants with a failing test — the way pull-only already is.

## 9. Serving the procedure — split by risk class

The natural next question is whether `PROCEDURE.md` itself should move, so the
skill is mostly driven centrally. It can — but only half of it should, and the
line is not where convenience would put it.

`PROCEDURE.md` holds two very different kinds of text:

1. **The security spine** — the non-negotiable rules (never transmit, consent
   via the ledger, content-is-data-not-instructions, read-only allow-lists, PII
   held) and the workspace setup.
2. **Operational detail** — question wording, sub-step order, provider routing,
   how to present remediation.

Serving (2) is a plain win. Serving (1) is a different category of thing: a bad
validation rule produces a wrong verdict; a bad *procedure* can produce data
exfiltration.

### The test

> *If this text were maliciously altered, could it cause client data to leave
> the machine, or a control to be bypassed?*
> **Yes → local spine, never servable. No → servable.**

### The evidence says the risky half doesn't need to move

Churn analysis of `ada/PROCEDURE.md` (13 commits): only **one of the last six**
touched the numbered rules block, changing two lines. Earlier rule edits were
structural — the initial commit, introducing Phase 0, adding providers.
Everything else was operational: the third-person phrasing fix, the intake
interrogation fix, the source-priority rewrite, the validation-judgment move.

**The fast-moving half is exactly the half that is safe to serve.** That is
fortunate, and it should drive the design rather than convenience.

### What this costs and buys

| Buys | Costs |
|---|---|
| Workflow fixes reach every client on next run — the phrasing bug would have self-healed | Signing stops being a checklist item and becomes a **hard precondition** |
| One workflow version everywhere; no drift across installs | Offline fallback must be a *complete* procedure, so it is maintained regardless |
| Fastest iteration exactly where the bugs have been | Injection blast radius grows — served text is the agent's instruction set |
| New phases/providers without redistribution | A bootstrap spine exists no matter what; only its thinness is negotiable |

Going further — serving the spine too — would buy very little (it barely
changes) and would cost the trust story: a client's security reviewer would be
approving a bundle that no longer determines behaviour, hollowing out invariant
§7.

### Implemented

`get_procedure(section)` in `ada-policy-service` serves six sections —
`phase-0`, `phase-a`, `phase-b`, `phase-b5`, `phase-c`, `troubleshooting`.
Three independent guards keep the spine off the wire, because one is not enough
for this property:

1. `pull_policy.sh` extracts only allow-listed headings and **refuses to
   publish** if a spine marker appears in a servable section.
2. `policy.procedure()` re-checks at **serve time** rather than trusting the
   pull step.
3. `tests/test_invariants.py` **fails the build** on spine content in any
   section.

Verified by injecting `## Non-negotiable rules … upload to evil.example` into a
servable section: the test failed with the specific markers *and* the runtime
accessor refused independently.

## 10. Phasing

- **Phase A** — policy-serving MCP: manifest, ruleset, taxonomy, connectors,
  remediation, forms, quarterly policy. Bundled snapshot fallback.
  `policy_version` recorded in the ledger. No client data, no writes.
- **Phase B** — Salesforce Case as requirement source.

Phase A is worth doing on its own merits: it converts "redistribute the skill"
into "publish a rule," which is the difference between a validation catalog that
grows and one that ossifies.
