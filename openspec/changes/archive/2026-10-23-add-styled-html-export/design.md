# Design

## Context

`userls export FILE` currently calls `write_csv_file` with lowercase headers and
raw GECOS values; the filename extension is ignored. The account view already
has the display-width helper used by the terminal table, but CSV cannot carry
the header background, type colors, bold rows, or padded columns the
human-facing document needs. The reference `/home/juan/prueba.csv` confirms two
data details: `juan` has the literal GECOS value `juan,,,`, and `carlitos` has
an empty GECOS value. Neither is a CSV corruption; CSV quoting keeps each value
in one field.

See `proposal.md` for the motivation and `specs/cli-output/spec.md` for the
behavior contract.

## Goals / Non-Goals

**Goals:**

- Add a self-contained, readable HTML account document without changing the
  CSV contract or adding runtime dependencies.
- Make the document look like the requested spreadsheet: real cells, uppercase
  header, colored type cells, bold rows, and content-sized columns.
- Present GECOS as a clear `FULL NAME` value and remove the noise from empty
  comma components.
- Keep the implementation small enough for the single-module, stdlib-only
  project.

**Non-Goals:**

- ODS, XLSX, PDF or any binary spreadsheet/container format.
- A styled CSV, a new CSV header schema, or a supplementary `GROUPS` column.
- JavaScript, external CSS/fonts/images, or network access.
- Changing the account, group or session data model.

## Decisions

### D1: Emit HTML rather than ODS or XLSX

HTML is the only target that provides semantic cells, CSS backgrounds, bold
text and content-based sizing while staying within the Python standard
library. It opens directly in a browser and LibreOffice Calc can import it with
the styling intact. ODS/XLSX would require either a new dependency or a
hand-written ZIP/XML package, which is disproportionate for a single table.
The user selected HTML and chose to keep CSV.

Alternative considered: a companion spreadsheet template plus CSV. It would
still require the user to import and reapply formatting, and the template would
be another shipped asset.

### D2: Select the format by extension

`os.path.splitext(path)[1].lower()` selects HTML for `.html` and `.htm`; every
other filename keeps the existing CSV path. This is backward compatible for
`.csv`, arbitrary filenames and scripts that already call `export`. It also
mirrors common document-tool behavior without adding a new required flag. The
existing `--force`, filtering, diagnostics and error handling apply to both
formats. The existing `--json`/`--csv` flags remain accepted on `export` for
parser compatibility but do not select the file format; the filename does.

Alternative considered: a `--format html` flag. It would be explicit but adds a
second selector and an extra failure mode; the user chose extension-based
selection.

### D3: Semantic table with embedded CSS

The document is:

- `<!DOCTYPE html>`, `<html lang="en">`, UTF-8 meta, viewport meta and a
  `<title>`.
- One `<table>` with a `<thead>` and `<tbody>`; every header uses
  `<th scope="col">`.
- Columns in order: `NAME`, `UID`, `GID`, `PRIMARY GROUP`, `FULL NAME`, `HOME`,
  `SHELL`, `TYPE`.
- One `<tr>` per account and one `<td>` per value.
- An embedded `<style>` block; no `<script>`, `<link>`, `<img>`, `@import` or
  web fonts.

The visual system keeps the type text readable and uses color as a secondary
cue, not the only cue:

| Element | Background | Text |
|---|---|---|
| Header | `#0f172a` | `#f8fafc` |
| `system` type cell | `#f97316` | `#111827` |
| `service` type cell | `#1e3a8a` | `#ffffff` |
| `normal` type cell | `#15803d` | `#ffffff` |
| `unknown` type cell | `#4b5563` | `#ffffff` |
| Table body | `#ffffff` | `#111827` |

The header is uppercase, bold and letter-spaced. All `tbody` rows use
`font-weight: 700`; the type cell is the only cell with a type background,
matching the terminal's type-color behavior rather than tinting the whole row.
Cells use `border: 1px solid #cbd5e1`, `padding: 0.55rem 1rem`,
`white-space: nowrap`, and a system sans-serif stack. A wrapper with
`overflow-x: auto` keeps very wide tables usable on narrow screens. Every value
is passed through `html.escape(..., quote=True)`.

### D4: Derive column widths from display width

A helper computes, for each column, the maximum of `display_width(header)` and
`display_width(value)` for every row. Four `ch` units of breathing room are
added, and a `<colgroup>` emits one `<col style="width: {width}ch">` per column.
The table keeps `table-layout: auto`, so a proportional font or an unexpectedly
wide glyph can still expand a column instead of clipping it. This reuses the
existing East Asian/combining-mark handling and satisfies the request that the
longest value in a column define its width.

Alternative considered: rely only on browser auto-layout. It usually works,
but it does not make the sizing rule explicit or testable and can produce
cramped columns under the default padding.

### D5: Normalize GECOS only in the HTML document

GECOS is the passwd general-information field, not a group list. Its
conventional comma-separated components are full name, room, work phone, home
phone and other. `juan,,,` is therefore a full name followed by three empty
components, not a CSV quoting bug. For the HTML view, the renderer takes
`gecos.split(",", 1)[0].strip()` and uses `NA` when the result is empty. Thus
`juan,,,` becomes `juan`, `carlitos` becomes `NA`, and
`John Doe,Room 1,555-0100,` becomes `John Doe`. `PRIMARY GROUP` stays separate.

CSV keeps the raw `gecos` header and value, including `"juan,,,"` as one
RFC 4180 field, so machine consumers see no schema or data change. The README
and man page explain the difference between `PRIMARY GROUP`, `FULL NAME` and
the passwd GECOS field.

Alternative considered: strip trailing commas only. It would clean `juan,,,`
but would keep arbitrary extra components and would not handle a leading empty
full name. Alternative considered: replace GECOS with a `GROUPS` column. That
would answer a different question and is outside this change.

### D6: Keep one write path for both formats

`export` resolves the format, performs the existing existence/`--force` check,
and writes UTF-8 without a BOM using `newline=""`. The existing
`write_csv_file` and its tests stay intact; a new HTML writer shares the
existence and `OSError` formatting so both formats produce the same
`<path> already exists; use --force to overwrite` and
`cannot write <path>: <reason>` messages. No temporary files, permissions or
atomic-rename behavior are introduced.

### D7: Verification and documentation

Unit tests cover escaping, header/type/bold CSS markers, column-width output,
GECOS normalization and `NA`. CLI tests cover `.html`, `.htm`, mixed case,
`.csv`/unknown extensions, filters, `--force`, unwritable targets and the
unchanged CSV header/value. An HTML parser from the standard library can be
used to assert table shape without new dependencies. README and the man page
document the extension rule, the styling and the GECOS explanation. The
feature ships as 1.3.0 with a `debian/changelog` entry and updated version
references.

## Risks / Trade-offs

- **HTML is not a spreadsheet.** Users who expect an editable `.ods`/`.xlsx`
  will not get one. Mitigation: document that HTML is the styled export and CSV
  remains for data interchange; a spreadsheet format can be a separate change.
- **`ch` is an approximation in proportional fonts.** Mitigation: keep
  `table-layout: auto`, `white-space: nowrap`, and enough padding so the
  browser expands rather than clips.
- **Truncating GECOS after the first comma can lose unusual content.** GECOS
  uses commas as component separators, so this is the conventional full-name
  component. Mitigation: document the rule; CSV retains the raw value.
- **Wide tables can overflow.** Mitigation: wrapper with horizontal scrolling;
  no wrapping of paths or shells.
- **Color contrast and color-only meaning.** Mitigation: the type word remains
  visible and the palette uses contrasting foregrounds; color is not the only
  indicator of type.
- **Extension collision.** A user who names a CSV file `.html` gets HTML.
  Mitigation: the extension is the explicit selector; every other extension,
  including `.csv`, keeps CSV.

## Migration Plan

No data migration and no persistent state. Existing `.csv` exports and
`--csv` stdout remain byte-compatible with the current contract. The new format
is opt-in through the target name. Rollback is reverting the source and
packaging changes; existing CSV files are unaffected. Release 1.3.0 after the
tests and package checks pass.
