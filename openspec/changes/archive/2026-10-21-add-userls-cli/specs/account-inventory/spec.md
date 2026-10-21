# Spec Delta

## Purpose

Presents the accounts known to the system with their core attributes and a
heuristic type, and supports filtering, searching, and inspecting individual
accounts.

## ADDED Requirements

### Requirement: Account listing

The system SHALL list every account returned by the enumeration source,
showing name, UID, GID, primary group name, home directory, shell, and account
type.

#### Scenario: Default listing

- **WHEN** the user runs the command without filters
- **THEN** every enumerated account appears once with all listed attributes

#### Scenario: Account with unresolved primary GID

- **WHEN** an account's GID has no matching group entry
- **THEN** the primary group is shown as the numeric GID

### Requirement: Heuristic account classification

The system SHALL classify each account as `normal`, `service`, `system`, or
`unknown` from UID ranges, shell, and home directory indicators, and MUST
present the result as heuristic rather than authoritative.

#### Scenario: Regular login account

- **WHEN** an account has a UID inside the user range, a login shell, and an
  existing home directory
- **THEN** it is classified as `normal`

#### Scenario: Non-login account

- **WHEN** an account uses a non-login shell or has a nonexistent home
  directory
- **THEN** it is classified as `service`

#### Scenario: System account with a usable shell

- **WHEN** an account has UID 0, or a UID inside the system range with a
  usable shell
- **THEN** it is classified as `system`

#### Scenario: Account outside every configured range

- **WHEN** an account has a UID outside the system and user ranges and does not
  match the service indicators
- **THEN** it is classified as `unknown`

### Requirement: Type filter

The system SHALL filter the listing by `normal`, `service`, `system`,
`unknown`, or `all`, defaulting to `all`, and MUST NOT reclassify accounts when
a filter is applied.

#### Scenario: Filter by service

- **WHEN** the user selects the service type
- **THEN** only accounts classified as service are listed

#### Scenario: Filter with no matches

- **WHEN** no account matches the selected type
- **THEN** the result is empty and the exit status is zero

### Requirement: Search by name or UID

The system SHALL search accounts by name using a case-insensitive substring
match and by UID using an exact numeric match, and MUST return an empty result
with a zero exit status when nothing matches.

#### Scenario: Search by name

- **WHEN** the user searches for `jua`
- **THEN** accounts whose name contains that text, regardless of case, are
  listed

#### Scenario: Search by UID

- **WHEN** the user searches for `1000`
- **THEN** the account with UID 1000 is listed

#### Scenario: No match

- **WHEN** the search term matches no account
- **THEN** no rows are shown and the exit status is zero

### Requirement: Account detail

The system SHALL show a single account's full record, including name, UID,
GID, primary group, GECOS, home directory, shell, and type, and MUST exit
non-zero with an error when the account does not exist.

#### Scenario: Existing account

- **WHEN** the user requests details for an existing name or UID
- **THEN** the full record is displayed

#### Scenario: Unknown account

- **WHEN** the requested name or UID does not exist
- **THEN** an error is written to stderr and the exit status is non-zero
