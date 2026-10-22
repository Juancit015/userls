# Design

## Context

See `proposal.md` for motivation. `userls.py` is a single standard-library
module. `SystemDataSource` caches NSS-backed `Account` and `Group` records;
`groups_for_account` already resolves an account's primary plus supplementary
groups by name or UID. Rendering goes through `render_table`, the
`*_payload` helpers, `write_csv`, and JSON/CSV flags attached with argparse
`parents=[output]`. `SCHEMA_VERSION` is 1 and existing payloads must not
change shape. No new data source is needed: privilege levels are a projection
of accounts plus groups.

## Goals / Non-Goals

**Goals:**

- One authoritative, ordered group-to-level mapping used by classification,
  documentation and tests.
- Per-account level plus the mapped groups held, derived without extra I/O.
- Output that follows the existing table, JSON, CSV, filter and error
  conventions.
- Completion and documentation coverage for the new subcommand.

**Non-Goals:**

- Reading sudoers, shadow, ACLs, file modes or capabilities; any `stat()`.
- Colouring the level column, or changing the existing `type` colour policy.
- Changing `Account`, its JSON/CSV payloads, or `SCHEMA_VERSION`.
- Modelling transitive privilege (for example a user who can edit a
  root-owned unit file).

## Decisions

**Level is computed, not stored on `Account`.**
Adding a `level` field to the dataclass would leak into `userls info`, the
account listing and the export CSV, changing three existing payloads for a
new view. Instead a `privilege_report(accounts, groups)` helper returns
`Permission` records. Alternative rejected: a lazy property on `Account`,
which would still couple the dataclass to group data.

**Ordered mapping as module data.**
`PRIVILEGE_LEVELS = ("root", "sudo", "privileged", "standard")` plus
`PRIVILEGE_GROUPS = {"sudo": ..., "privileged": ...}` drive a first-match
classifier, mirroring `classify()` for account types. Evaluating in tuple
order makes precedence explicit and lets tests and the README table assert the
same structure. Alternative rejected: nested `if/elif` on group names, which
repeats the order in three places.

**Batch membership index.**
Build `group_names_by_member` once from `Group.members`, then for each
account union it with the primary group name. This is O(accounts + groups +
memberships), whereas calling `groups_for_account` per account re-scans every
group's member list. The primary group counts, matching the established
`userls groups` semantics.

**Only mapped groups are reported.**
The report lists the groups from the mapping that the account actually holds,
not every group it belongs to; unmapped groups carry no privilege signal.
`root` accounts show any mapped groups they hold too, keeping the column
factual even when UID 0 already decides the level. `standard` accounts show an
empty list, rendered as `-`.

**Severity-first ordering.**
Rows sort by level rank (`root`, `sudo`, `privileged`, `standard`), then UID,
then name. The rest of the CLI sorts by UID, but this view exists to surface
privilege, and a UID sort would bury the answer under system accounts.
Filtering still uses the shared `filter_accounts` before ordering.

**`perms` reuses the shared option groups.**
The subparser takes `parents=[output, filters]`, like `export`, so `--json`,
`--csv`, `--no-color`, `--type` and `--search` work before or after the
subcommand. The single-account path ignores the filters, consistent with how
global filters are already ignored by `info`.

**Payload shapes.**
Listing: `{"schema_version": 1, "count": N, "permissions": [{"name", "uid",
"type", "level", "groups"}]}` with `groups` as a JSON array. Detail:
`{"schema_version": 1, "account": {...}, "permission": {"level", "groups"}}`
where `account` is the existing `account_dict`. CSV columns are
`name,uid,type,level,groups`, with `groups` comma-joined inside the field; a
CSV parser yields that string, and NSS group names cannot contain commas.
`SCHEMA_VERSION` stays 1 because no existing payload changes.

**Detail rendering mirrors `print_info`.**
Aligned `Label: value` lines computed with `display_width`/`pad`, adding
`Level` and `Privileged groups`, with `-` for an empty list.

**Completions extend existing lists.**
`perms` joins the subcommand candidates in all three shells and the live
account enumeration shared by `info`/`groups`; fish gets a one-line
description. No new completion machinery is needed.

## Risks / Trade-offs

- **Heuristic completeness** → A group-based level cannot see sudoers rules,
  polkit, or indirect escalation. Mitigated by naming it a group-derived
  level in README and man page, and by listing the exact mapped groups so the
  user can judge.
- **Distribution drift** → Distributions use different privileged groups
  (`wheel` vs `sudo`, `libvirt`). Mitigated by including both common sudo
  groups and documenting the closed mapping; extending it later is a spec
  change, not a silent behaviour shift.
- **Large NSS directories** → The batch index keeps a full listing linear;
  the report adds no per-account subprocess or file access.
- **CSV group field** → Comma-joined groups rely on group names lacking
  commas. Accepted because NSS group names cannot contain commas and the CSV
  writer quotes the field anyway.
- **Filter semantics on detail** → Filters are accepted and ignored on the
  single-account path. This matches existing global-filter behaviour and is
  stated in the spec, at the cost of a slightly surprising flag.

## Migration Plan

Additive only: no account, group or export data changes, no configuration, no
new dependency. Ship as 1.2.0; rollback is reverting the commit and the
version bump. Existing consumers of `--json`/`--csv` see identical payloads
for existing commands.
