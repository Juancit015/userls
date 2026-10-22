# Proposal

## Why

`userls` already reports account type and group membership, but answering
"who on this host can become root, and through which group?" requires the user
to cross-reference group names by hand against knowledge of which groups grant
privileges. On a real machine the answer is spread across `sudo`, `wheel`,
`docker`, `disk`, `shadow` and similar groups, and a plain member list hides
it. A single read-only view that names each account's privilege level and the
groups that grant it closes that gap without adding data sources or requiring
root.

## What Changes

- Add a `userls perms [NAME|UID]` subcommand that reports a privilege level per
  account.
- Classify every account into exactly one level, first match wins:
  `root` (UID 0), `sudo` (member of `sudo` or `wheel`), `privileged` (member of
  `adm`, `disk`, `docker`, `lxd`, `libvirt`, `shadow` or `systemd-journal`),
  `standard` (none of the above).
- Treat the primary group as a membership for this purpose, matching how
  `userls groups` already resolves memberships.
- List every account with name, UID, account type, privilege level and the
  groups that granted it, ordered by level severity and then UID, with the
  usual summary count.
- Show one account's detail for `userls perms NAME|UID`, including all
  privilege-relevant groups held; unknown account writes an error to stderr and
  exits non-zero.
- Support `--json`, `--csv` and `--no-color` for the new subcommand, plus the
  existing `--type` and `--search` filters on the listing.
- Update fish, bash and zsh completions with the new subcommand and with live
  account completion after `perms`.
- Document the levels and their group mapping in the README and man page, and
  release as 1.2.0.

Out of scope: parsing `/etc/sudoers` or `sudoers.d`, file modes, ACLs, password
or lock status, Linux file capabilities, and any `stat()` of home directories.
Those either need root, contradict the project's no-stat rule, or belong to a
different capability.

## Capabilities

### New Capabilities

- `permission-report`: privilege level classification from group membership,
  the `perms` listing and detail views, and their output formats.

### Modified Capabilities

- `shell-completions`: the subcommand candidate lists and the live account
  completion must include `perms`.

## Impact

- `userls.py`: privilege group map, level classification, `perms` subparser,
  table and detail rendering, JSON/CSV payloads, version bump to 1.2.0.
- `completions/userls.fish`, `completions/userls.bash`, `completions/_userls`:
  new subcommand, description in fish, live accounts after `perms`.
- `tests/`: classification unit tests and CLI tests for listing, detail,
  unknown account, JSON, CSV, filters and completion candidates.
- `README.md`, `man/userls.1`, `debian/changelog`: documented behavior and
  version 1.2.0.
- No new dependencies, no root, no network, no new data sources; enumeration
  stays on the existing NSS path.
