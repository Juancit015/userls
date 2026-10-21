# Proposal

## Why

Debian exposes account information through a fragmented set of tools:
`getent passwd`, `lslogins`, `who`, and direct reads of `/etc/passwd`. Each
requires knowing NSS behavior, column names, and flag combinations before it
answers a simple question ("who is on this machine?"). `lslogins` already
covers much of the data, but it hardcodes the system UID range (101-999),
cannot emit JSON, and uses cryptic column identifiers such as `HOMEDIR`.

A small, read-only CLI that answers that question in one command, classifies
accounts using the host's own `/etc/login.defs`, and offers machine-readable
output is useful enough to package and maintain for Debian.

## What Changes

- Add a `userls` command, written in Python 3 using only the standard library,
  licensed GPL-3.0-or-later and installed at `/usr/bin/userls`.
- Provide a default table of local accounts with name, UID, GID, primary
  group, home directory, shell, and an account type.
- Classify accounts as `normal`, `service`, `system`, or `unknown` using the
  UID ranges in `/etc/login.defs` plus shell and home directory heuristics,
  and state that the classification is heuristic.
- Filter by account type and search by name or UID.
- List groups and show the groups of a given user, including the primary
  group.
- Show active sessions with user, terminal, login time, and origin.
- Emit table, JSON, and CSV output, and export the current view to a CSV file.
- Report data-source failures on stderr with a non-zero exit code, and never
  fabricate data for a source that failed.
- Package the tool as an architecture-independent `.deb` with a man page and
  autopkgtest, suitable for GitHub Releases and for a future Debian upload.

Out of scope: modifying accounts, passwords, or group membership; any GUI;
network access; non-Linux platforms; the ITP and archive upload itself.

## Capabilities

### New Capabilities

- `system-data-access`: NSS-aware account and group enumeration, login.defs
  range parsing with defaults, read-only execution of `getent` and `who`, and
  explicit reporting of unavailable data sources without privilege escalation.
- `account-inventory`: list, classify, filter, search, and inspect local
  accounts, with a documented heuristic for the account type.
- `group-inventory`: list groups and resolve group membership for a user,
  including the primary group.
- `session-inventory`: list active login sessions and report when the session
  source is unavailable.
- `cli-output`: human and machine output formats (table, JSON, CSV), CSV file
  export, exit codes, stderr error reporting, and color policy.

### Modified Capabilities

None. This is a greenfield repository with no existing specs.

## Impact

- New code: `userls.py` (single importable module), `tests/test_userls.py`.
- New packaging: `debian/` (control, rules, changelog, copyright, watch),
  `man/userls.1`, `debian/tests/` for autopkgtest.
- Runtime dependency: `python3` (3.11 or newer). No third-party Python
  packages, therefore no `python3-*` dependencies beyond the interpreter.
- Reads `/etc/passwd` and `/etc/group` through NSS, `/etc/login.defs`, and
  executes `getent` and `who` as unprivileged subprocesses.
- Builds an `Architecture: all` binary package, so one build serves every
  Debian architecture.
- No existing code is modified. The only repository files affected are new
  additions alongside the existing README, LICENSE, and `.gitignore`.
