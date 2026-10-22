# Design

## Context

See `proposal.md - Why`. Current constraints that shape the approach:

- `userls` is a single-file Python CLI (`userls.py`) with zero runtime
  dependencies — the package must not gain any.
- The Debian package is built with debhelper + dh-exec; `debian/install`
  already renames `userls.py` to `/usr/bin/userls` and installs the man page.
- Tests are stdlib `unittest` and spawn the CLI as a subprocess; there is no
  CI, shells are not guaranteed to exist in every environment, and local
  machines can have fish, bash and zsh simultaneously (this one does).
- The man page is already packaged; system installs get a man-db index via
  dpkg's triggers, but rootless installs do not (discovered during scoping:
  `whatis userls` failed until `mandb --user-db` ran).

## Goals / Non-Goals

**Goals:**

- Shell completion with the same candidate coverage in all three shells, and
  descriptions wherever the shell can render them.
- Live account completion that stays consistent with the CLI's own
  enumeration and degrades silently.
- Completion available immediately after package install and documented for
  rootless installs.

**Non-Goals:**

- Other shells (PowerShell, nushell) or configurable completion behavior.
- Completing values for `--search` (free-text) and human-formatted values.
- Any change to `userls` CLI flags, output or exit codes.

## Decisions

### Hand-written completion files, no generator

Ship `completions/userls.fish`, `completions/userls.bash` and
`completions/_userls` as static files. A generator (e.g. shtab) would add a
dependency and a build step for a small, stable CLI surface; calling
`userls --help` through a parser at completion time is slow and fragile.

Alternative considered: generating completions from argparse metadata during
build. Rejected — extra moving parts, and human-authored descriptions read
better than auto-derived text.

### Live accounts come from `userls --csv`, not from getent directly

The completion scripts run `userls --csv` (stderr suppressed, exit status
ignored) and derive candidates from: header line skipped, `name` = field 1,
`uid` = field 2, `type` = last field. Naive comma splitting is safe for these
fields because only `gecos` (field 5) may contain commas, so fields 1, 2 and
the last one stay intact.

- Compared to `getent passwd`: stays consistent with the product's NSS-aware
  enumeration and yields the classification `type` used in descriptions.
- Cost is one Python startup (~50 ms) per completion request; interactive
  completion is lazy and asynchronous in fish/zsh and only runs on explicit
  Tab in bash, so this is acceptable.
- Failure (missing binary, enumeration error) yields zero candidates.

### Descriptions per shell

- **fish**: static candidates carry `-d 'description'`; dynamic account
  candidates are returned as `name<TAB>uid N · type` lines, which fish
  parses into word + description.
- **bash**: descriptions are not rendered by bash itself; candidates only.
  The function must not require `bash-completion` helpers to exist.
- **zsh**: `_describe` receives `name:description` items so candidates show
  UID and type.

### Packaging

`debian/install` gains three dh-exec lines targeting the standard vendor
directories:

- `completions/userls.fish => usr/share/fish/vendor_completions.d/userls.fish`
- `completions/userls.bash => usr/share/bash-completion/completions/userls`
- `completions/_userls => usr/share/zsh/vendor-completions/_userls`

No `Depends`/`Recommends` on any shell is added: the files are inert data,
and forcing shell packages onto servers would be wrong.

### Command description via man-db

The packaged man page plus man-db's dpkg trigger makes `man -f userls`
resolve after install with no manual step. Rootless installs document
`mandb --user-db`, which builds the user-side index (verified manually during
scoping). No new artifact is needed for this beyond documentation and
verification.

### Tests

New `tests/test_completions.py`, stdlib `unittest`, same style as existing
tests: syntax checks (`fish --no-execute`, `bash -n`, `zsh -n`) always; one
behavior check per shell driving the real shell non-interactively
(`fish -c "complete -C'userls '"`, a `COMP_WORDS`/`COMPREPLY` harness for
bash, `zsh -f` with a compinit harness for zsh). Each check is guarded with
`unittest.skipUnless(shutil.which(shell))`. Behavior tests also pin the exact
candidate sets, so CLI flag changes fail the suite until completions catch up.

### Versioning

Feature release: `__version__` → `1.1.0`, `debian/changelog` entry
`userls (1.1.0-1)`. No breaking changes.

## Risks / Trade-offs

- [Completions drift when CLI flags change] → behavior tests pin candidate
  sets; a flag change without a completion update fails the suite.
- [Python startup noticeable on repeated Tab] → acceptable at this scale;
  a static cache can be added later without spec changes.
- [CSV parsing assumptions] → only `gecos` can contain commas; a future
  column order change must update the completion parsing (covered by the
  pinned behavior tests).
- [zsh behavior checks are the hardest to keep non-flaky] → syntax check is
  unconditional; the behavior check skips when the shell harness cannot
  initialize.
- [Minimal containers may lack man-db or shells] → completion tests skip
  missing shells; man-db verification runs in the standard container with
  man-db installed.

## Migration Plan

No data migration. Release 1.1.0; rollback is reinstalling `1.0.0-1`, which
removes the completion files. The rootless README steps are additive.

## Open Questions

- Should `--search` also complete account names? Not required by the specs;
  can be added later without affecting this design.
