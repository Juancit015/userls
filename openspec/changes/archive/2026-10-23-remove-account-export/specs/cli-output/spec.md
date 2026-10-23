# Spec Delta

## REMOVED Requirements

### Requirement: Machine-readable output

**Reason**: CSV rendering is removed from stdout, so JSON is the only
machine-readable format.

**Migration**: Use `--json` and parse stdout as JSON. There is no CSV output.

### Requirement: CSV export

**Reason**: The `userls export` subcommand and CSV file writing are removed.

**Migration**: Use `--json` for structured data. If a file is required, the
caller can redirect JSON to a file with the shell.

### Requirement: Export format selection

**Reason**: Removing `userls export` removes extension-based format dispatch
and the `--force` overwrite path.

**Migration**: Use the table or `--json`; no command writes a file.

### Requirement: Styled HTML account document

**Reason**: HTML file export is removed; no HTML document is produced.

**Migration**: Use the default table or `--json` for account output.

### Requirement: HTML column sizing

**Reason**: HTML export is removed, so there are no HTML columns to size.

**Migration**: Use the default terminal table for tabular output.

### Requirement: HTML full-name display

**Reason**: The HTML-specific `FULL NAME` presentation is removed with HTML
export. No CSV output remains either.

**Migration**: Use `--json` when the raw account fields are needed; there is no
styled replacement.

## ADDED Requirements

### Requirement: JSON output

The system SHALL support JSON rendering of the same data, and JSON output MUST
be valid JSON on stdout with no diagnostics mixed in.

#### Scenario: JSON consumed by a parser

- **WHEN** JSON output is requested
- **THEN** stdout parses as JSON and every diagnostic is written to stderr
