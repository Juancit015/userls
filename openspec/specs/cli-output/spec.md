# cli-output Specification

## Purpose

Defines how results are rendered, exported, and reported to the caller,
including machine-readable formats, exit codes, diagnostics, and color.

## Requirements

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

### Requirement: Export format selection

`userls export FILE` SHALL select the output format from the filename extension:
`.html` and `.htm` (case-insensitive) select HTML, while `.csv` and every other
name keep the existing CSV output. Both formats SHALL preserve the existing
refusal to overwrite without `--force` and the existing write-error reporting.

#### Scenario: HTML target

- **WHEN** the user runs `userls export accounts.html` or `userls export accounts.htm`
- **THEN** an HTML document is written to that target and no CSV file is written

#### Scenario: CSV or other target

- **WHEN** the target ends in `.csv` or in any extension other than `.html` or `.htm`
- **THEN** the existing CSV output is written

#### Scenario: Existing target without force

- **WHEN** the target exists and `--force` is not given
- **THEN** an error is written to stderr, the command exits non-zero, and the file is not overwritten

#### Scenario: Unwritable HTML target

- **WHEN** the HTML target cannot be written
- **THEN** an error is written to stderr and the command exits non-zero

### Requirement: Styled HTML account document

The HTML export SHALL be a self-contained UTF-8 HTML document with one semantic
table, one cell per value, uppercase headers for `NAME`, `UID`, `GID`,
`PRIMARY GROUP`, `FULL NAME`, `HOME`, `SHELL` and `TYPE`, a distinct header
background, bold account rows, and a colored background on each `TYPE` cell.
The CSS MUST be embedded; the document MUST NOT contain scripts, external
assets, ANSI escapes, or unescaped field text.

#### Scenario: Table structure

- **WHEN** the HTML export contains N accounts
- **THEN** the document has one table, one header row, N account rows, and every value occupies its own cell

#### Scenario: Visual contract

- **WHEN** the document is rendered
- **THEN** the header is uppercase with a background, account rows are bold, and the type cell is orange for `system`, dark blue for `service`, green for `normal`, and neutral for `unknown`

#### Scenario: Text safety

- **WHEN** a name, path, shell or full name contains `<`, `>`, `&`, `"` or `'`
- **THEN** the value is escaped and rendered as text rather than markup

#### Scenario: Self-contained document

- **WHEN** the HTML is inspected
- **THEN** its CSS is embedded and it contains no script, external stylesheet, image, font or other network reference

#### Scenario: Empty account view

- **WHEN** the export contains no accounts
- **THEN** the document still contains the complete header row and no account rows

### Requirement: HTML column sizing

The HTML export SHALL derive each column width from the maximum display width of
its header and values, add horizontal padding, and keep cell content on one
line.

#### Scenario: Longest value sets the width

- **WHEN** a value is longer than the header and every other value in its column
- **THEN** that column is wide enough for the value plus its padding and does not wrap it

#### Scenario: Wide and combining characters

- **WHEN** values contain East Asian wide glyphs or combining marks
- **THEN** widths are measured by display width rather than code-point count

### Requirement: HTML full-name display

The HTML export SHALL label the GECOS value as `FULL NAME`, display the first
comma-separated GECOS component after trimming whitespace, and use `NA` when
that component is empty. `PRIMARY GROUP` MUST remain a separate column. CSV
output MUST keep its existing lowercase `gecos` header and raw value.

#### Scenario: Empty GECOS components

- **WHEN** the GECOS value is `juan,,,`
- **THEN** the HTML document shows `juan` in `FULL NAME`

#### Scenario: Blank GECOS

- **WHEN** the GECOS value is empty or contains only whitespace
- **THEN** the HTML document shows `NA` in `FULL NAME`

#### Scenario: GECOS with extra fields

- **WHEN** the GECOS value is `John Doe,Room 1,555-0100,`
- **THEN** the HTML document shows `John Doe` in `FULL NAME`

#### Scenario: CSV remains unchanged

- **WHEN** the target is a CSV file
- **THEN** its header remains `gecos` and the value is written raw with RFC 4180 quoting
