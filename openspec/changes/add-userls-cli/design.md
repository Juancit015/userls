# Design

## Context

Greenfield repository: only `README.md`, `LICENSE` (GPL-3.0-or-later) and
`.gitignore` exist. See `proposal.md` for motivation and the spec deltas under
`specs/` for the behavioral contract.

Constraints that shape the approach:

- Target is Debian 13 (trixie) with Python 3.13, but the package must also
  install on Debian 12 (bookworm, Python 3.11). No syntax newer than 3.11.
- The development host uses NSS with `passwd: files systemd` and has 34
  accounts and 62 groups, 28 of them with `/usr/sbin/nologin`. Other hosts may
  use LDAP or SSSD, so enumeration must go through NSS.
- `/etc/login.defs` on this host defines `UID_MIN=1000`, `UID_MAX=60000`,
  `GID_MIN=1000`, `GID_MAX=60000`, and does not define `SYS_UID_MIN` or
  `SYS_UID_MAX`.
- No third-party Python packages, no root, no network, no writes outside an
  explicit export target.
- `lslogins` 2.41 exists and covers much of the data. Differentiation is
  classification driven by `login.defs`, JSON/CSV output, and active sessions.

## Goals / Non-Goals

**Goals:**

- A single-file, dependency-free CLI that installs as `Architecture: all`.
- Deterministic, testable classification with documented heuristics.
- Stable machine-readable output that scripts can rely on.
- A packaging layout that can be built locally and later uploaded to Debian
  without restructuring.

**Non-Goals:**

- Replacing `lslogins` or patching util-linux.
- Translations/gettext, shell completion, and an APT repository in this change.
- Any operation that modifies accounts, groups, or passwords.
- Reading `/etc/shadow` or reporting password state.

## Decisions

### D1: Python 3.11+ standard library, single module

Use one importable module, `userls.py`, with `argparse`, `pwd`, `grp`,
`subprocess`, `json`, `csv`, `dataclasses`, and `unicodedata`.

Alternatives considered:

- **Go**: static binary and 3 ms startup, but `Architecture: all` is lost and
  the Debian package needs one build per architecture with a `golang`
  build-dependency.
- **Rust**: same per-architecture cost plus `debcargo` and vendored crates.
- **Shell + awk**: smallest package, but fragile CSV/JSON handling and no
  usable unit tests.

Python wins because `Architecture: all` keeps the archive and GitHub artifacts
identical across architectures, and the NSS interfaces are already in the
standard library. A single module keeps `debian/rules` at `dh $@` and lets
tests import the code directly.

### D2: NSS-first data layer with a getent fallback

`pwd.getpwall()` and `grp.getgrall()` are the primary source because they go
through NSS. If either raises, fall back to `getent passwd` / `getent group`,
parsed as colon-separated records with field-count validation.

- `/etc/passwd` and `/etc/group` are never parsed directly: they only describe
  one NSS backend and would silently hide LDAP or userdb accounts.
- Subprocesses run with `LC_ALL=C`, an argv list, no shell, and a 5-second
  timeout. A timeout or non-zero exit is a source failure, not an empty result.
- Malformed `getent` lines are skipped and counted in a warning on stderr.

`getent` is not a cure for backends with enumeration disabled (SSSD with
`enumerate = false`): both paths will return only what NSS exposes. This is a
documented limitation, not something the tool can detect or invent around.

### D3: Classification rules

Ordered evaluation, first match wins:

| Order | Condition | Type |
|-------|-----------|------|
| 1 | UID 0 | `system` |
| 2 | Shell is a non-login shell, or home is a bogus path | `service` |
| 3 | `UID_MIN <= UID <= UID_MAX` | `normal` |
| 4 | `1 <= UID < UID_MIN` | `system` |
| 5 | Anything else | `unknown` |

- Non-login shells: `/usr/sbin/nologin`, `/sbin/nologin`, `/bin/false`,
  `/usr/bin/false`.
- Bogus home paths: empty, `/`, `/nonexistent`, `/dev/null`. Home directories
  are **not** `stat()`ed: an autofs or NFS home can block for seconds, and a
  listing command must never hang on a dead mount. The trade-off is that a
  deleted home is not detected; the shell evidence still covers most service
  accounts.
- `SYS_UID_MIN` and `SYS_UID_MAX` are read and validated, and are reported in
  the `info` view as the configured system allocation band. They do not
  override classification because Debian ships legacy system accounts below
  `SYS_UID_MIN` (`bin`=2, `sync`=4), which the `1 <= UID < UID_MIN` rule
  classifies correctly.
- `nobody` (65534, `nologin`) lands in `service` by rule 2, which matches the
  intent even though its UID is outside every configured range.
- Documented in `--help` epilog and README: the type is a heuristic.

### D4: Command surface

`argparse` with a default action and explicit subcommands:

```
userls [--type TYPE] [--search TEXT] [--json|--csv] [--no-color]
userls info <name|uid>
userls groups [name|uid]
userls sessions
userls export <file> [--force]
```

- No subcommand means list accounts.
- `--type` accepts `normal`, `service`, `system`, `unknown`, `all` (default).
- `--search` matches name case-insensitively by substring, or UID exactly.
- `--json` and `--csv` render the current result to stdout; `export` always
  writes CSV to a file.
- `export` refuses to overwrite an existing file unless `--force` is given,
  which prevents accidental data loss without a prompt.
- Shared flags are defined on a parent parser added to the root parser and to
  each subparser, so both `userls --json groups` and `userls groups --json`
  work.
- Errors raise a `UserlsError` handled once in `main()`, which prints
  `userls: <message>` to stderr and returns the exit code. `argparse` keeps
  ownership of usage errors and exits 2.

### D5: Output model and renderers

Three dataclasses (`Account`, `Group`, `Session`) are rendered by independent
functions; no renderer knows about the data source.

- **Table**: width-aware padding using `unicodedata.east_asian_width` and
  zero-width combining marks, so accented and CJK names do not break columns.
  A trailing summary line states the row count.
- **JSON**: one object per command with `schema_version`, `count`, and a
  command-specific key (`accounts`, `groups`, `sessions`). `schema_version` is
  `1` and changes only on breaking output changes.
- **CSV**: the `csv` module with `lineterminator="\n"` and `QUOTE_MINIMAL`;
  this is the only writer used for both stdout and `export`, so quoting is
  consistent.
- **Color**: only the type column is colored, and only when stdout is a TTY,
  `--no-color` is absent, and `NO_COLOR` is unset. Machine formats never emit
  ANSI sequences.

### D6: Session parsing

`who` has no machine-readable mode. Run it with `LC_ALL=C` and parse leniently:

```
^(?P<user>\S+)\s+(?P<tty>\S+)\s+(?P<date>\S+)\s+(?P<time>\S+)(?:\s+\((?P<origin>[^)]*)\))?
```

If the regex does not match a line (extra columns, unexpected format), keep the
first two tokens as user and terminal and store the remainder as a raw string
instead of dropping the session. JSON exposes the C-locale login time and the
raw line, so consumers are not forced to re-parse a localized date.

### D7: login.defs parsing

Read line by line, strip comments, split on whitespace, and accept only
non-negative integers within the 32-bit UID range. Malformed values produce a
warning and fall back to the documented default for that key. Defaults:
`UID_MIN=1000`, `UID_MAX=60000`, `SYS_UID_MIN=100`, `SYS_UID_MAX=999`.
The file is read once per process and cached.

### D8: Testing strategy

`unittest` only, no pytest, so the build dependency stays at `python3`.

- Pure functions (parsing, classification, rendering) are tested directly with
  fixture data.
- Data access is injected as a small object with `accounts()`, `groups()`,
  and `sessions()` methods; tests pass fakes and never read the host's real
  account database.
- CLI smoke tests run the module as a subprocess with `--help`, `--version`,
  and JSON output, asserting exit codes and that stdout is parseable.
- The classification matrix covers: root, regular user, service with nologin,
  legacy UID below `SYS_UID_MIN`, `nobody`, an out-of-range UID, and a
  normal-range account with a non-login shell.

### D9: Packaging layout

- `debian/` with `debhelper-compat (= 13)`, source format `3.0 (quilt)`,
  `Architecture: all`, `Depends: python3 (>= 3.11)`,
  `Rules-Requires-Root: no`, `Standards-Version: 4.7.4.1`.
- `debian/install` renames the script while installing:
  `userls.py usr/bin/userls`, and installs the man page to
  `usr/share/man/man1/userls.1`.
- `debian/watch` tracks GitHub tags; `debian/copyright` is DEP-5 with
  `License: GPL-3+` and a `Files: debian/*` stanza.
- `debian/tests/control` runs a smoke test: `userls --version`,
  `userls --json`, and JSON validation.
- The GitHub `.deb` is built from the same source with
  `dpkg-buildpackage -us -uc -b` and attached to the release with a
  `SHA256SUMS` file. It is never committed to git.
- Local builds need `debhelper` (13.24 is available in trixie), which is not
  currently installed.

### D10: Version and release flow

Upstream versions are tagged `vX.Y.Z` on GitHub. Debian revisions use
`X.Y.Z-1`, `X.Y.Z-2` for packaging-only fixes. The changelog is the single
source of truth for the package version; `userls --version` prints the
upstream version only.

## Risks / Trade-offs

- **Heuristic misclassification** (a service account with a real shell, or a
  human account with nologin) → the type is documented as heuristic, `--json`
  exposes the raw shell/home/UID, and `--type unknown` makes anomalies visible.
- **NSS backends that do not enumerate** (SSSD `enumerate = false`) → the tool
  cannot see them; `getent` fallback does not help. Documented in README and
  the man page, never silently treated as "no accounts".
- **`who` format drift or localization** → `LC_ALL=C`, lenient parser, raw
  line preserved, and a clear failure when the command itself fails.
- **No `stat()` on home directories** → a deleted home is not detected;
  avoids hangs on dead autofs/NFS mounts. Documented as a deliberate
  trade-off.
- **Python startup (~40 ms)** → acceptable for an interactive admin command;
  not suitable for a hot loop, which is out of scope.
- **GitHub `.deb` is unsigned** → publish `SHA256SUMS` plus a detached GPG
  signature; archive builds are signed by Debian and are the authoritative
  artifact.
- **Package name collision in Debian** → `userls` is absent from trixie and
  from the package index consulted during exploration, but the name must be
  re-checked against `sid` and WNPP before filing the ITP.
- **`debhelper` missing locally** → `Build-Depends` declares it; the first
  build requires installing it. No other build tooling is needed.

## Migration Plan

Greenfield, so there is no data or compatibility migration.

1. Build: `dpkg-buildpackage -us -uc -b`.
2. Install locally: `apt install ./userls_<version>_all.deb`.
3. Remove: `apt remove userls` (no conffiles, no maintainer scripts, no
   residual state).
4. Rollback after a bad release: install the previous `.deb`; there is no
   on-disk state to revert.

The Debian archive upload (ITP, sponsorship, NEW queue) is a separate change
and is not part of this design.

## Open Questions

- Whether to add shell completion and gettext translations after the first
  release. Both are additive and do not change the specs.
- Whether to publish an APT repository for automatic updates. Deferred until
  there is a release cadence worth automating.
