# shell-completions Specification

## Purpose

Makes `userls` complete itself in fish, bash and zsh — subcommands, options,
option values and live account names — with descriptions where the shell
displays them, and keeps the command's one-line description resolvable so
shells can show it.

## Requirements

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

### Requirement: Bash completion

The system SHALL ship a bash completion for `userls` that offers the
subcommands, the shared options in both accepted positions, and the values of
`--type`.

#### Scenario: Candidates after the command

- **WHEN** the user asks for completion after `userls`
- **THEN** subcommands and options are offered

#### Scenario: Candidates after a subcommand

- **WHEN** the user asks for completion after a subcommand
- **THEN** options and, where defined, value candidates are offered

### Requirement: Zsh completion

The system SHALL ship a zsh completion for `userls` that offers the
subcommands, the shared options in both accepted positions, and the values of
`--type`, with descriptions.

#### Scenario: Candidates with descriptions

- **WHEN** the user completes a subcommand, an option or a `--type` value
- **THEN** the candidate list matches fish's coverage and carries descriptions

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

### Requirement: Export file completion

The system SHALL complete filesystem paths for the `export` target argument.

#### Scenario: Path candidates

- **WHEN** the user completes the argument after `userls export`
- **THEN** existing file and directory paths are offered

### Requirement: Package installation

The Debian package SHALL install the completion files into the standard vendor
directories of each shell, so completion is available after installation
without further configuration and without adding package dependencies.

#### Scenario: Fresh package install

- **WHEN** the package is installed on a clean Debian system with fish, bash
  or zsh present
- **THEN** after a new shell session, `userls` completion works in that shell
  with no extra steps

#### Scenario: Dependencies unchanged

- **WHEN** the built package's dependencies are inspected
- **THEN** no shell package was added as a dependency

### Requirement: Command description lookup

The system SHALL keep the `userls` one-line description resolvable through the
manual-page database so shells can display it, and SHALL document the extra
step rootless installations need to build the user-side index.

#### Scenario: Packaged install

- **WHEN** the package is installed on a Debian system with man-db
- **THEN** `man -f userls` resolves the description without running `mandb`
  manually

#### Scenario: Rootless install

- **WHEN** a user follows the documented rootless installation
- **THEN** the documented `mandb` step makes `man -f userls` resolve

### Requirement: Rootless completions documented

The README SHALL document, per shell, where to install each completion file
without root so completion works from a source checkout.

#### Scenario: Documented paths work

- **WHEN** a user installs each completion file at its documented destination
- **THEN** completion works in that shell without the Debian package
