# Spec Delta

## Purpose

Defines how results are rendered, exported, and reported to the caller,
including machine-readable formats, exit codes, diagnostics, and color.

## ADDED Requirements

### Requirement: Default human output

The system SHALL render results to stdout as an aligned table with a header row
and a trailing summary line stating the number of rows.

#### Scenario: Default table

- **WHEN** a command produces rows
- **THEN** stdout contains a header, one row per result, and a summary count

#### Scenario: Empty result

- **WHEN** a command produces no rows
- **THEN** stdout contains the header and a summary stating zero results

### Requirement: Machine-readable output

The system SHALL support JSON and CSV rendering of the same data, and JSON
output MUST be valid JSON on stdout with no diagnostics mixed in.

#### Scenario: JSON consumed by a parser

- **WHEN** JSON output is requested
- **THEN** stdout parses as JSON and every diagnostic is written to stderr

#### Scenario: CSV on stdout

- **WHEN** CSV output is requested
- **THEN** stdout starts with a header row followed by one line per record

### Requirement: CSV export

The system SHALL write the current result to a user-specified CSV file,
quoting fields that contain commas, quotes, or line breaks according to RFC
4180.

#### Scenario: Field with a comma

- **WHEN** a value contains a comma
- **THEN** the exported field is quoted and the file remains parseable as CSV

#### Scenario: Unwritable target

- **WHEN** the export target cannot be written
- **THEN** an error is written to stderr and the exit status is non-zero

### Requirement: Exit codes

The system SHALL exit 0 on success, 1 on runtime or data-source failure, and 2
on usage error.

#### Scenario: Unknown option

- **WHEN** the user passes an unsupported option
- **THEN** usage is printed to stderr and the exit status is 2

#### Scenario: Source failure

- **WHEN** a required data source is unavailable
- **THEN** the exit status is 1

### Requirement: Diagnostics on stderr

The system SHALL write errors and warnings to stderr and MUST keep stdout
reserved for results.

#### Scenario: Warning during listing

- **WHEN** a non-fatal source warning occurs
- **THEN** the warning goes to stderr and stdout remains a valid result

### Requirement: Color policy

The system SHALL use ANSI color only when stdout is a terminal, SHALL honor
`--no-color` and the `NO_COLOR` environment variable, and MUST NOT emit ANSI
sequences in machine-readable formats.

#### Scenario: Piped output

- **WHEN** stdout is not a terminal
- **THEN** no ANSI escape sequences are emitted

#### Scenario: NO_COLOR set

- **WHEN** `NO_COLOR` is set in the environment
- **THEN** color is disabled even on a terminal
