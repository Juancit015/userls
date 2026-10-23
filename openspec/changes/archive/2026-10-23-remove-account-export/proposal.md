# Proposal

## Why

`userls export` has grown from a small CSV writer into a file-export subsystem
with HTML rendering, extension dispatch, styling rules and a separate set of
write-error paths. The tool also carries a CSV stdout path that duplicates
every report and requires its own tests, completion parsing and documentation.
The read-only inspection tool needs one human format and one machine-readable
format, not a file-export layer and two serialization formats.

## What Changes

- **BREAKING** Remove the `userls export` subcommand and its `--force` flag.
- **BREAKING** Remove `--csv` from every command, including account, group,
  session, info and permission output. JSON remains the only
  machine-readable format.
- Remove all file-export and CSV code: CSV writing, HTML rendering, extension
  dispatch, HTML styling constants and the shared export-target helpers.
- Keep the default table output and `--json` output unchanged in meaning.
- Change shell completion account discovery from `userls --csv` to
  `userls --json`, without adding `jq` or another dependency.
- Remove export- and CSV-related tests, completion candidates and
  documentation.
- Record that `userls` now writes no files at all; it remains read-only and
  unprivileged.
- Bump the release to `2.0.0` because commands, a flag and output formats
  disappear.

Migration: `userls --csv` becomes `userls --json`; consumers that need CSV must
convert the JSON themselves. `userls export FILE` has no direct replacement;
structured data can be redirected from `userls --json`, and human-readable
output remains the default table. There is no HTML replacement.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `cli-output`: remove the CSV stdout requirement, the CSV file-export
  requirement, the export format selection requirement and the three HTML
  export requirements. Keep the table and add a JSON-only machine-readable
  requirement.
- `shell-completions`: remove the `export` subcommand, its filesystem-path
  completion and the `--csv` option candidate. Keep live account completion
  working from the JSON output.
- `system-data-access`: remove the export-target exception from read-only
  operation; every command now performs no file writes.

## Impact

- `userls.py`: argument parser (`--csv` and `export`), `run()` export branch,
  all CSV output branches, `write_csv()`, HTML and CSV file writers, and
  HTML-only helpers.
- `tests/`: remove export, HTML and CSV coverage; update CLI help, permission
  output, shell completion and color-policy expectations.
- `completions/`: remove `export`, `--force` and `--csv` from fish, bash and
  zsh; read account candidates from `--json`.
- `README.md`, `man/userls.1`, `AGENTS.md`: remove export and CSV instructions
  and describe the tool as table/JSON only and never writing files.
- `debian/changelog`, version references: release `2.0.0-1`.
- No new dependencies; the package remains Python standard library only.
