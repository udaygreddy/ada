# Connector: salesforce-case (requirement source — FUTURE)

> Status: **planned, not built.** Documented so the requirement-source interface
> stays pluggable. The current build uses [mailbox.md](mailbox.md) instead.

In the target state, the per-client requirement list comes from the **ADP
implementation Case in Salesforce** rather than (or in addition to) the request
email. The Case is the system-of-record for what ADP is asking the client to
provide, so it is a cleaner, more authoritative source than parsing email.

## Intended shape

- **Access:** Salesforce via MCP — **read-only**. Read the implementation Case,
  its required-document checklist / related items, and any attached blank forms.
- **Extract:** the requested documents (and `complete`-kind blank forms), the
  conversion/start date, and the case-defined return channel.
- **Record:** identical to the mailbox flow, but with provenance set to the Case:
  `requirements.py add … --source-kind salesforce-case --source-ref <case_id> \
     --source-from <case_owner> --taxonomy-id <id>`

Everything downstream (map to taxonomy for HOW/WHERE → SCAN → REVIEW → PACKAGE,
gap report measured against requested) is unchanged. Only the requirement
*source* differs, which is why `source_kind` exists on every requirement record.

## Why a separate source matters

Email parsing is heuristic and spoofable (see mailbox.md security notes). A
Salesforce Case read under the client's authenticated Salesforce session removes
the spoofing surface and gives a structured checklist instead of free-text email
bodies — so this is the preferred source once the MCP integration exists.
