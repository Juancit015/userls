# Proposal

## Why

`userls export` writes RFC 4180 CSV. CSV is machine-oriented and cannot store
cell backgrounds, bold text, or measured column widths, so the human-facing
layout has to be recreated by hand every time the file is opened in a
spreadsheet. The current header `GECOS` is also easy to mistake for a group
list, and raw values such as `juan,,,` or an empty GECOS add noise to the
document.

A styled HTML export gives the same account view real table cells and keeps
the document readable without adding dependencies or changing the
machine-readable CSV contract.

## What Changes

- Add a self-contained HTML account export selected by the target extension:
  `userls export accounts.html` and `accounts.htm` write HTML; `accounts.csv`
  and every other target keep today's CSV behavior.
- Render a semantic table with one cell per value, uppercase header labels, a
  header background, bold account rows, and a colored background on the type
  cell: orange for `system`, dark blue for `service`, green for `normal`, and a
  neutral color for `unknown`.
- Derive each column's width from the maximum display width of its header and
  values, add generous padding, and keep values on one line so long paths and
  names remain legible.
- In the HTML document, label `GECOS` as `FULL NAME` and display the first
  comma-separated GECOS component after trimming; show `NA` when that value is
  empty. Keep `PRIMARY GROUP` as the separate primary-group column.
- Explain the GECOS-versus-groups difference in the README and man page. The
  CSV output keeps its lowercase `gecos` header and raw value for compatibility.
- Escape all text, embed the CSS in the document, and use no JavaScript,
  network assets, or third-party packages.
- Add tests for HTML rendering, extension dispatch, escaping, normalization,
  overwrite behavior, and unchanged CSV output, and document the new format.
- Release as 1.3.0 with a `debian/changelog` entry.

Out of scope: ODS, XLSX or PDF export; a styled CSV; a supplementary `GROUPS`
column; changing the CSV schema; JavaScript; and external stylesheets or
fonts.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `cli-output`: adds HTML file export and its styling contract, selects the
  file format by extension, defines how GECOS is presented in the human-facing
  document, and preserves the existing CSV and JSON contracts.

## Impact

- `userls.py`: HTML renderer, HTML escaping, extension-based export dispatch,
  GECOS display normalization, and a shared overwrite/write path.
- `tests/test_output.py` and `tests/test_commands.py`: renderer and CLI
  coverage, including `.html`/`.htm`, `.csv`, `--force`, filters, escaping, and
  the `juan,,,`/empty-GECOS cases.
- `README.md` and `man/userls.1`: HTML export usage, the format-selection rule,
  the style choices, and the GECOS explanation.
- `__version__` and `debian/changelog`: version 1.3.0.
- No new runtime dependencies, no root, no network, no new data sources, and
  no change to the CSV schema or JSON payloads.
