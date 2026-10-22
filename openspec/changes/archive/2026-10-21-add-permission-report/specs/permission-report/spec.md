# Spec Delta

## Purpose

Reports how privileged each local account is by deriving a privilege level
from its group membership, naming the groups that grant it, without reading
sudoers, file modes, or any source that needs root.

## ADDED Requirements

### Requirement: Privilege level classification

The system SHALL assign every account exactly one privilege level from `root`,
`sudo`, `privileged` or `standard`, evaluating them in that order and stopping
at the first match.

#### Scenario: Root account

- **WHEN** an account has UID 0
- **THEN** its level is `root`, regardless of its groups

#### Scenario: Sudo-capable account

- **WHEN** an account is a member of `sudo` or `wheel`
- **THEN** its level is `sudo`

#### Scenario: Account with other powerful groups

- **WHEN** an account is a member of a privileged group but of neither `sudo`
  nor `wheel`
- **THEN** its level is `privileged`

#### Scenario: Account without privileged groups

- **WHEN** an account is a member of no privilege-relevant group
- **THEN** its level is `standard`

#### Scenario: Several levels apply

- **WHEN** an account is a member of `sudo` and of `docker`
- **THEN** its level is `sudo`, because `sudo` is evaluated before `privileged`

### Requirement: Privilege group mapping

The system SHALL treat membership in `sudo` and `wheel` as granting the `sudo`
level, and membership in `adm`, `disk`, `docker`, `lxd`, `libvirt`, `shadow`
or `systemd-journal` as granting the `privileged` level, matching group names
exactly.

#### Scenario: Primary group grants privilege

- **WHEN** an account's primary group is one of the mapped groups
- **THEN** that membership counts toward its level

#### Scenario: Supplementary group grants privilege

- **WHEN** an account appears in the member list of a mapped group
- **THEN** that membership counts toward its level

#### Scenario: Unmapped group

- **WHEN** an account belongs only to groups outside the mapping
- **THEN** those groups do not raise its level

### Requirement: Permission listing

The system SHALL list accounts with their name, UID, account type, privilege
level and the mapped groups that granted it, ordered by level severity and then
UID, with a trailing summary count.

#### Scenario: Default listing

- **WHEN** the user requests the permission report without an account
- **THEN** every selected account appears once with its level and granting
  groups, and the summary states the row count

#### Scenario: Severity order

- **WHEN** the listing contains accounts at several levels
- **THEN** `root` rows come first, followed by `sudo`, `privileged` and
  `standard`, each ordered by UID

#### Scenario: No privileged accounts

- **WHEN** every selected account is `standard`
- **THEN** all of them are still listed

#### Scenario: Empty selection

- **WHEN** filters exclude every account
- **THEN** the output contains the header and a summary stating zero rows

### Requirement: Permission detail

The system SHALL show one account's privilege level and every mapped group it
holds when given a name or UID, and MUST exit non-zero with an error on stderr
when the account does not exist.

#### Scenario: Account with privileges

- **WHEN** the user requests the permission detail of a privileged account
- **THEN** its level and all mapped groups it holds are displayed

#### Scenario: Account without privileges

- **WHEN** the user requests the permission detail of a `standard` account
- **THEN** the level is shown and the group list is shown as empty

#### Scenario: Unknown account

- **WHEN** the requested name or UID does not exist
- **THEN** an error is written to stderr and the exit status is non-zero

### Requirement: Permission listing filters

The system SHALL apply the shared `--type` and `--search` filters to the
permission listing, and MUST NOT apply them to a single-account report.

#### Scenario: Filter by account type

- **WHEN** the user combines the permission listing with `--type`
- **THEN** only accounts of that type are reported

#### Scenario: Search term

- **WHEN** the user combines the permission listing with `--search`
- **THEN** only matching accounts are reported

#### Scenario: Detail ignores filters

- **WHEN** the user requests the detail of one account together with a filter
- **THEN** that account is reported regardless of the filter

### Requirement: Permission output formats

The system SHALL render the permission report as a table by default and as
JSON or CSV on request, with the same data in every format and diagnostics kept
on stderr.

#### Scenario: JSON report

- **WHEN** JSON output is requested
- **THEN** stdout is valid JSON containing the reported accounts with their
  levels and granting groups

#### Scenario: CSV report

- **WHEN** CSV output is requested
- **THEN** stdout starts with a header row and contains one line per reported
  account

#### Scenario: Color disabled

- **WHEN** JSON or CSV output is requested
- **THEN** no ANSI escape sequences are emitted

### Requirement: Unprivileged permission sources

The system SHALL derive privilege levels only from the account and group data
it already enumerates, and MUST NOT read sudoers, file modes, ACLs, password
status or Linux capabilities, and MUST NOT require root.

#### Scenario: Run as a regular user

- **WHEN** an unprivileged user requests the permission report
- **THEN** it completes without elevation and without attempting privileged
  files

#### Scenario: Group from a non-file backend

- **WHEN** a mapped group is supplied by a non-file NSS backend
- **THEN** its members receive the corresponding level
