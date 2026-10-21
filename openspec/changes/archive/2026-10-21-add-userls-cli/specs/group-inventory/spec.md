# Spec Delta

## Purpose

Lists the groups known to the system and resolves which groups belong to a
given account, including the primary group.

## ADDED Requirements

### Requirement: Group listing

The system SHALL list every group returned by the enumeration source with its
name, GID, and member names.

#### Scenario: Default group listing

- **WHEN** the user requests the group list
- **THEN** every enumerated group appears once with name, GID, and members

#### Scenario: Group without members

- **WHEN** a group has no supplementary members
- **THEN** it is still listed and its membership is shown as empty

### Requirement: Groups for an account

The system SHALL report the primary group and all supplementary groups of a
named account or UID, deduplicated and ordered by GID, and MUST include the
primary group even when the account is not listed among its members.

#### Scenario: Primary group not listed as a member

- **WHEN** the account's primary group does not list the account in its member
  field
- **THEN** the primary group still appears in the result

#### Scenario: Account in several supplementary groups

- **WHEN** the account is a member of multiple groups
- **THEN** each group appears once, ordered by GID

#### Scenario: Unknown account

- **WHEN** the requested account does not exist
- **THEN** an error is written to stderr and the exit status is non-zero
