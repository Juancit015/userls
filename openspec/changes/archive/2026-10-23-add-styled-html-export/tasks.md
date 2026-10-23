# Tasks

## 1. HTML rendering primitives

- [x] 1.1 Add a `full_name_for_html(gecos)` helper that takes the first
  comma-separated component, trims whitespace, and returns `NA` when the result
  is empty. Verify unit tests for `juan,,,` → `juan`, empty → `NA`, whitespace
  → `NA`, and `John Doe,Room 1,555-0100,` → `John Doe`:
  `python3 -m unittest tests.test_output -v`.
- [x] 1.2 Add a column-width helper that computes the maximum `display_width`
  of each header and value and adds the documented padding. Verify tests with
  ASCII, East Asian wide glyphs, and combining marks, and assert the HTML
  `<colgroup>` emits one width per column with no wrapping:
  `python3 -m unittest tests.test_output -v`.
- [x] 1.3 Add `render_html(accounts)` with a semantic table, uppercase headers,
  embedded CSS, bold account rows, type-cell classes, zero-row support, and
  `html.escape` for every value. Verify with `html.parser.HTMLParser` that the
  document has one table, the expected header labels and one cell per value,
  escaped `<`, `&`, quotes and apostrophes, no `<script>` or external asset,
  and the type colors for `system`, `service`, `normal` and `unknown`:
  `python3 -m unittest tests.test_output -v`.

## 2. Export dispatch and file writing

- [x] 2.1 Add extension dispatch (`.html` and `.htm`, case-insensitive) and
  keep every other target on CSV. Add an HTML writer that shares the existing
  existence check and `OSError` formatting with `write_csv_file`, without
  changing the CSV helper's API. Verify unit tests for `.html`, `.htm`,
  mixed-case extensions, `.csv`, unknown extensions, existing targets and
  unwritable targets: `python3 -m unittest tests.test_output -v`.
- [x] 2.2 Wire the `export` command to the dispatch and keep the current
  filters, `--force`, diagnostics and CSV output unchanged. Verify CLI tests
  for HTML and CSV targets, `--type`/`--search` filters, the overwrite error,
  `--force`, the lowercase `gecos` header, raw `"juan,,,"` CSV quoting, and no
  ANSI escapes in HTML: `python3 -m unittest tests.test_commands -v`.
- [x] 2.3 Generate an HTML file from the live account view and inspect it with
  a standard-library parser. Verify every account row has eight cells, the
  `TYPE` cell carries exactly one type class, the header is uppercase, and the
  document contains no external references:
  `./userls.py export /tmp/userls-accounts.html`.

## 3. User-facing documentation

- [x] 3.1 Update `README.md` output-format and export sections with the
  `.html`/`.htm` rule, an example, the styling, the column-width behavior, and
  the `FULL NAME`/GECOS explanation. Verify every documented command runs as
  written and `userls export --help` describes CSV and HTML targets:
  `./userls.py export --help`.
- [x] 3.2 Update `man/userls.1` synopsis and export description with the HTML
  format, extension rule, styling, and GECOS distinction. Verify the page
  renders without warnings: `groff -man -Tascii man/userls.1 >/dev/null`.

## 4. Version and packaging

- [x] 4.1 Bump `__version__` to `1.3.0`, add the `userls (1.3.0-1) unstable`
  entry to `debian/changelog`, and update the version references in
  `README.md`, `man/userls.1` and `AGENTS.md`. Verify:
  `./userls.py --version` prints `1.3.0` and
  `dpkg-parsechangelog -SVersion` prints `1.3.0-1`.
- [x] 4.2 Build the package and inspect it. Verify
  `dpkg-buildpackage -us -uc -b` succeeds,
  `dpkg-deb -c ../userls_1.3.0-1_all.deb` lists the script, man page and
  completions, and `lintian --fail-on error ../userls_1.3.0-1_all.deb`
  reports no errors.

## 5. Integration verification

- [x] 5.1 Run the complete suite and the spec contract. Verify
  `python3 -m unittest discover -s tests -v` passes and
  `openspec validate add-styled-html-export --strict` reports a valid change.
- [x] 5.2 Install the built package in a disposable Debian 13 container, run
  both `userls export /tmp/accounts.html` and
  `userls export /tmp/accounts.csv`, confirm the HTML has the styled table and
  the CSV header/value are unchanged, then purge the package and check for
  leftovers. If no container runtime is available, record the skipped check
  and perform the equivalent commands from the source tree.

## Workflow follow-up

- Archive the change after review, syncing the `cli-output` delta into the main
  spec.
- Publish the v1.3.0 release with the `.deb` and `SHA256SUMS` when the release
  is approved.
