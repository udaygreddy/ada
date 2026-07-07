# ADA Discovery — Cowork plugin

ADA (ADP Discovery Agent) helps a client gather the onboarding documents ADP
requested, from the client's **own** systems — so no ADP person accesses those
systems. It derives the required-document list from the ADP request email, then
collects from the client's payroll provider — Paychex or Paylocity (guided
export) — and Intuit QuickBooks (read-only accounting/GL), staging a package the
client transmits to ADP. Consent is enforced in code and every action is
recorded in a hash-chained, tamper-evident ledger.

## Install

Accept the `ada-discovery.plugin` card in chat.

## Prerequisites

- **Gmail connector** connected in Cowork — used read-only in Phase 0 to find the
  ADP request email and derive the requirement list.
- *(Optional)* **QuickBooks (QBO)** connector — for read-only GL/financial pulls.
- Paychex / Paylocity need no connector (the skill guides a manual export).
- `python3` on the machine (bundled scripts are stdlib-only; nothing to install).

## Try it

Say any of:
- "ADP asked us for documents — help me gather everything they requested."
- "We're switching payroll from Paychex to ADP. Find the documents ADP requested and package them."
- "Check my email for ADP's document request, then collect what they need."

## What it does not do

It never transmits data anywhere. It reads locally and produces an `ada_package/`
folder in your working directory; you transmit that to ADP yourself.
