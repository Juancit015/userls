# Spec Delta

## MODIFIED Requirements

### Requirement: Fish completion

The system SHALL ship a fish completion for `userls` that offers the
subcommands, the shared options in both accepted positions, and the values of
`--type`, attaching a one-line description to every candidate.

#### Scenario: Subcommand candidates

- **WHEN** the user requests completion at the start of a `userls` argument
- **THEN** `info`, `groups`, `sessions` and `perms` are offered, each
  with a description

#### Scenario: Option candidates

- **WHEN** the user completes `--` before the subcommand or after it
- **THEN** `--json`, `--no-color`, `--type`, `--search` and `--version` are
  offered with descriptions

#### Scenario: Type value candidates

- **WHEN** the user completes the value of `--type`
- **THEN** `all`, `normal`, `service`, `system` and `unknown` are offered with
  descriptions

## REMOVED Requirements

### Requirement: Export file completion

**Reason**: The `export` subcommand is removed, so there is no export target to
complete.

**Migration**: No completion target remains; the command does not write files.
