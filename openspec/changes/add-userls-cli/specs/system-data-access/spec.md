# Spec Delta

## Purpose

Provides read-only access to account, group, and session data from the host's
configured sources, without elevated privileges or network access.

## ADDED Requirements

### Requirement: NSS-aware enumeration

The system SHALL enumerate accounts and groups through the host's configured
NSS sources, using the native NSS interfaces as the primary source and
`getent` as a fallback. A direct read of `/etc/passwd` or `/etc/group` MUST
NOT be treated as authoritative.

#### Scenario: Account supplied by a non-file backend

- **WHEN** an account is provided by a non-file NSS backend such as
  systemd-userdb
- **THEN** the account appears in the listing with the same attributes as a
  local account

#### Scenario: Primary enumeration fails

- **WHEN** native enumeration raises an error
- **THEN** the system retries through `getent passwd` and reports that the
  fallback was used

### Requirement: UID ranges from login.defs

The system SHALL read `UID_MIN`, `UID_MAX`, `SYS_UID_MIN`, and `SYS_UID_MAX`
from `/etc/login.defs`, and MUST apply documented defaults of 1000/60000 and
100/999 when a key is absent or the file cannot be read.

#### Scenario: System range keys omitted

- **WHEN** `/etc/login.defs` does not define `SYS_UID_MIN` or `SYS_UID_MAX`
- **THEN** the system uses 100 and 999 as the system range

#### Scenario: login.defs unreadable

- **WHEN** `/etc/login.defs` cannot be read
- **THEN** the documented defaults are used and a warning names the file

### Requirement: Unprivileged execution

The system SHALL run external helpers as unprivileged subprocesses with
explicit argument vectors and without a shell, and MUST NOT request or require
root privileges.

#### Scenario: Command arguments are not shell-interpreted

- **WHEN** the system executes an external helper
- **THEN** it passes an argument vector directly and no shell interprets the
  arguments

#### Scenario: Run as a regular user

- **WHEN** an unprivileged user runs an account or group query
- **THEN** the query completes without a privilege escalation prompt

### Requirement: Source failure disclosure

When a data source is unavailable, the system SHALL name the failed source,
MUST NOT present partial results as complete, and MUST NOT invent records.

#### Scenario: Fallback tool missing

- **WHEN** native enumeration fails and `getent` is not installed
- **THEN** the error names `getent` and the command exits with a non-zero
  status

#### Scenario: Session source fails

- **WHEN** `who` exits with a non-zero status
- **THEN** the sessions view reports the failure and exits with a non-zero
  status

### Requirement: Read-only operation

The system MUST NOT create, modify, or delete accounts, passwords, groups, or
system files, and SHALL write only to an explicitly requested export target.

#### Scenario: Listing performs no writes

- **WHEN** any listing or inspection command runs
- **THEN** no account database or system file is modified

#### Scenario: Export writes only its target

- **WHEN** the user requests a CSV export
- **THEN** the only file written is the requested export target
