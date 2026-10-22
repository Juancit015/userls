# Spec Delta

## MODIFIED Requirements

### Requirement: Fish completion

The system SHALL ship a fish completion for `userls` that offers the
subcommands, the shared options in both accepted positions, and the values of
`--type`, attaching a one-line description to every candidate.

#### Scenario: Subcommand candidates

- **WHEN** the user requests completion at the start of a `userls` argument
- **THEN** `info`, `groups`, `sessions`, `perms` and `export` are offered, each
  with a description

#### Scenario: Option candidates

- **WHEN** the user completes `--` before the subcommand or after it
- **THEN** `--json`, `--csv`, `--no-color`, `--type`, `--search` and
  `--version` are offered with descriptions

#### Scenario: Type value candidates

- **WHEN** the user completes the value of `--type`
- **THEN** `all`, `normal`, `service`, `system` and `unknown` are offered with
  descriptions

### Requirement: Live account completion

The system SHALL complete account names after `info`, `groups` and `perms`
from the same enumeration `userls` uses, and MUST offer no candidates and no
shell error when enumeration fails.

#### Scenario: Accounts offered

- **WHEN** the user completes an account argument after `info`, `groups` or
  `perms`
- **THEN** every enumerated account name is offered, and shells that display
  descriptions show UID and type per candidate

#### Scenario: Options win over accounts

- **WHEN** the completed argument starts with `-`
- **THEN** option candidates are offered instead of account names

#### Scenario: Enumeration failure

- **WHEN** account enumeration fails during completion
- **THEN** no account candidates are offered and the shell reports no error
