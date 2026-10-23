# Tasks

## 1. Remove export and CSV from the CLI and renderers

- [x] 1.1 Remove the `export` subparser, its `--force` option and the export examples from `EPILOG`/`build_parser()`; verify `python3 userls.py --help` contains neither `export` nor `--force`, and `python3 userls.py export /tmp/userls-check.json` exits `2`.
- [x] 1.2 Remove the `--csv` option, its mutually-exclusive group wrapper and every `getattr(args, "csv", ...)` branch from `print_accounts()`, `print_groups()`, `print_sessions()`, `print_info()`, `print_permissions()` and `print_permission()`; update `color_enabled()` to check only `json`; verify `python3 userls.py --csv` exits `2`, the default table still renders, and `python3 userls.py --json | python3 -m json.tool >/dev/null` succeeds.
- [x] 1.3 Remove the `export` branch from `run()` and delete `write_csv()`, `write_csv_file()`, `write_html_file()`, `_check_target()`, `_write_target()`, `export_format()`, `render_html()`, the HTML constants and the HTML-only helpers; remove the now-unused `csv`, `html` and `TextIO` imports; verify `python3 -m compileall -q userls.py` succeeds and `grep -nE 'write_csv|render_html|export_format|full_name_for_html|html_column_widths|HTML_|import csv|import html' userls.py` returns no matches.
- [x] 1.4 Remove the export, HTML and CSV tests and the HTML parser test helper from `tests/test_commands.py`, `tests/test_output.py` and `tests/test_permissions.py`, while retaining table and JSON coverage; verify `python3 -m unittest tests.test_commands tests.test_output tests.test_permissions -v` passes.
- [x] 1.5 Update `tests/test_cli.py` so the help assertions omit `export`, `--force` and `--csv`, and add regressions confirming both `userls export` and `userls --csv` exit `2`; verify `python3 -m unittest tests.test_cli -v` passes.

## 2. Move shell completions to JSON

- [x] 2.1 Update `completions/userls.fish`, `completions/userls.bash` and `completions/_userls`: remove the `export` candidate, `--force`, `--csv` and file-path completion; replace the `userls --csv` account enumeration with `userls --json` parsed by a small embedded `python3` snippet that emits `name`, UID and type; verify `grep -RniE '\\bexport\\b|--force|--csv' completions/` returns no matches and each shell's syntax check passes.
- [x] 2.2 Update `tests/test_completions.py`: expect `info`, `groups`, `perms` and `sessions` only, remove the export/file/force cases and `--csv` from option expectations, update the CSV-header comments, and keep the live account tests against the JSON parser; verify `python3 -m unittest tests.test_completions -v` passes and the silent-failure cases still emit no candidates or shell errors.

## 3. Update documentation and the release version

- [x] 3.1 Update `README.md`: remove `userls export`, `--csv`, `--force` and HTML/CSV format documentation; change usage and examples to table plus `--json`; state that `userls` writes no files; update the `.deb` version references and the migration note to `--json`; verify `grep -nE -- '--csv|userls export|--force|HTML|CSV' README.md` returns no matches.
- [x] 3.2 Update `man/userls.1`: remove the export synopsis, command, `--force` and `--csv` options, HTML/CSV output descriptions, export exit-status text and export examples; update the documented version and date; verify `groff -man -Tascii man/userls.1 >/dev/null` succeeds and `grep -nE -- '--csv|export|--force|HTML|CSV' man/userls.1` returns no matches.
- [x] 3.3 Update `AGENTS.md` so the layout says table/JSON rendering, the read-only constraint says no files are written, and the test command reflects the final suite size; verify `grep -nE 'CSV|export|only file it ever writes' AGENTS.md` returns no matches and the stated count matches `python3 -m unittest discover -s tests -v`.
- [x] 3.4 Set `__version__` to `2.0.0` and add a `2.0.0-1` entry to `debian/changelog` that names the breaking removals and the `--json` migration; verify `python3 userls.py --version` prints `userls 2.0.0` and `head -n 5 debian/changelog` shows the new entry.

## 4. Integration verification

- [x] 4.1 Run `python3 -m unittest discover -s tests -v` and confirm every test passes and the count matches the value recorded in `AGENTS.md`.
- [x] 4.2 Run `openspec validate remove-account-export --strict` and `openspec validate --all --strict`; confirm both exit successfully with no spec errors.
- [x] 4.3 Build the package with `dpkg-buildpackage -us -uc -b` and run `lintian --fail-on error ../userls_2.0.0-1_all.deb`; confirm the package and checksum inputs are produced without lintian errors.
- [x] 4.4 Smoke-test the finished CLI: `python3 userls.py --help` omits `export`, `--force` and `--csv`; the default table renders; `--json` parses; `python3 userls.py --csv` and `python3 userls.py export /tmp/userls-check.json` both exit `2`; and `grep -RniE -- '--csv|userls export|--force|write_csv|render_html' userls.py completions README.md man AGENTS.md` finds no stale references.
- [x] 4.5 Confirm no new dependency or import was added: `grep -nE '^(import|from) ' userls.py` contains only standard-library modules still used, and `python3 -m compileall -q userls.py tests` succeeds.

## Workflow follow-up

- Archive the change with `openspec archive remove-account-export` after review so the main `cli-output`, `shell-completions` and `system-data-access` specs drop the export and CSV requirements.
- Verify the archived specs no longer contain `CSV export`, `Machine-readable output`, `Export format selection`, the HTML export requirements or `Export file completion`.
- Commit and publish `2.0.0` only when a separate release step is requested; attach the `.deb` and `SHA256SUMS` to the release.
