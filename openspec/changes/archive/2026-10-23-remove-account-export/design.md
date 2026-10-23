# Design

## Context

`userls.py` currently combines two output paths and a file-export subsystem.
`build_parser()` exposes `--csv`, the `export` subcommand and `--force`;
`run()` dispatches export to `write_csv_file()` or `write_html_file()`; and the
module contains HTML constants, an HTML renderer, extension dispatch and
target-writing helpers. `write_csv()` feeds `--csv` from every human report
(`accounts`, `groups`, `sessions`, `info` and `permissions`), so removing CSV
touches those renderers as well. The shell completions also call
`userls --csv` to enumerate account names, which means the flag cannot simply
disappear without replacing that discovery mechanism. See `proposal.md` for the
motivation and `specs/` for the behavioral requirements.

## Goals / Non-Goals

**Goals:**

- Remove the `export` command, `--csv`, and every code path that writes a file
  or renders CSV.
- Preserve the default table and `--json` behavior.
- Keep shell account completion working after CSV is gone, without `jq` or a
  new package dependency.
- Make the documented model accurate: `userls` produces stdout only and writes
  no files.
- Update specs, completions, tests and documentation in the same change so no
  export or CSV surface remains.

**Non-Goals:**

- Removing `--json` or the default table.
- Replacing CSV or HTML with another file format or adding a conversion
  utility.
- Changing account classification, NSS access, session parsing or permission
  reporting.
- Adding a deprecation window inside `2.0.0`; the removals are immediate and
  documented as breaking.

## Decisions

### Remove the command instead of hiding it

Delete the `export` subparser, its `--force` option and the corresponding
`run()` branch. After the change `userls export ...` is an unknown subcommand,
so argparse exits with usage status `2`, consistent with any other invalid
command. A hidden compatibility command was rejected because it would keep the
write path, its error handling and its tests alive for no product benefit.

### Remove CSV completely, keep JSON as the structured format

Remove the `--csv` argument, every `getattr(args, "csv", ...)` branch,
`write_csv()`, `write_csv_file()`, `write_html_file()`, `_check_target()`,
`_write_target()`, `export_format()`, `render_html()`, the HTML constants and
the HTML-only helpers. Remove the `csv`, `html` and `TextIO` imports that become
unused. This applies the requested scope literally: no CSV output remains, not
just no CSV file.

The alternatives were considered and rejected: keeping `--csv` would leave the
CSV surface the removal is meant to eliminate; keeping only file CSV would keep
the write layer; replacing CSV with XLSX would add a dependency and more code
to a stdlib-only tool. JSON is already implemented, versioned and tested, so it
becomes the only machine-readable format.

### Keep the table as the human default

The default table, summaries, colors and filters are unrelated to export and
remain as they are. `--json` keeps its existing payloads and schema version.
Removing CSV does not alter account data or filtering.

### Source completion accounts from JSON

The fish, bash and zsh completions currently parse `userls --csv`. Replace that
with `userls --json` piped through a small embedded Python parser that reads the
`accounts` array and emits the shell's expected candidate format. Python is
already a hard requirement of `userls`, so this adds no package dependency and
avoids `jq`. Shell-native JSON parsing was rejected as brittle; parsing the
default table was rejected because display widths and summaries are not a
stable machine interface; adding a private `--names` flag was rejected because
it expands the CLI to work around a removed flag.

The completion functions must keep their current failure behavior: suppress
stderr, produce no candidates when `userls` or JSON parsing fails, and never
emit a shell error.

### Treat this as a major release

The command, a flag and both CSV output paths disappear, so the next release is
`2.0.0` rather than a patch. The changelog will call out the removals and the
JSON migration. Keeping a `1.x` version would misrepresent the compatibility
impact to scripts, completions and package consumers.

### Update every surface in one change

Remove `export`, `--force` and `--csv` from the fish, bash and zsh completion
candidates. Update the README usage, examples, output-format section and
read-only statement; update the man page synopsis, command description,
options, output formats, exit status and examples; update `AGENTS.md` so it
describes table/JSON output and no file writes. Remove export, HTML and CSV
tests, add CLI regressions proving `export` and `--csv` are rejected, and keep
the table and JSON coverage.

## Risks / Trade-offs

- **CSV consumers break immediately** → Ship as `2.0.0`, document `--json` as
  the structured replacement and note that CSV conversion is the caller's
  responsibility.
- **Export users lose their only file path** → State clearly that there is no
  replacement for `userls export`; callers can redirect `userls --json` or use
  the table.
- **Shell completion breaks when it stops using CSV** → Parse the existing
  versioned JSON payload with the already-required Python interpreter, keep
  failures silent, and run the fish/bash/zsh completion tests.
- **The table or JSON path is accidentally damaged** → Remove CSV branches
  individually, retain existing table/JSON tests and add CLI regressions for
  the removed flags.
- **Completions or docs still advertise removed surface** → Update all three
  completion files and the README/man page in the same task, then grep the
  repository for `--csv`, `export` and `--force` before building.
- **Unused imports or helpers remain** → Remove CSV and HTML as units, then run
  the test suite, a compile check and an import check.

## Migration Plan

1. Implement the removal on a `2.0.0` development line, including code, specs,
   tests, completions and documentation.
2. Run the full unit suite, `openspec validate --all --strict`, the man-page
   render check and `dpkg-buildpackage`; fix any stale CSV or export references
   before release.
3. Publish `2.0.0`, documenting `userls --json` as the only structured output.
   There is no in-place data migration because `userls` stores no state.
4. Roll back by reverting to the `1.3.0` release if a consumer cannot accept the
   removals; no account data is affected either way.
