# Tasks

## 1. Module skeleton and CLI contract

- [x] 1.1 Create `userls.py` with the `#!/usr/bin/python3` shebang, an SPDX
  `GPL-3.0-or-later` header, the `Account`, `Group`, and `Session` dataclasses,
  and a `main(argv)` that returns an exit code. Verify with
  `python3 -c "import userls"` and `python3 userls.py --help`.
- [x] 1.2 Define the argparse surface: root parser with `--type`, `--search`,
  `--json`, `--csv`, `--no-color`, `--version`; subcommands `info`, `groups`,
  `sessions`, `export`; shared flags on a parent parser added to the root and
  each subparser. Verify `userls --help` lists every option and subcommand and
  `userls groups --json` parses.
- [x] 1.3 Add `UserlsError` and the exit code mapping (0 success, 1 runtime or
  source failure, 2 usage) with diagnostics on stderr. Verify tests for an
  unknown option (2) and a forced source failure (1).
- [x] 1.4 Add `tests/test_cli.py` covering help, version, unknown option, and
  error formatting. Verify `python3 -m unittest discover -s tests` passes.

## 2. login.defs and classification

- [x] 2.1 Implement `load_login_defs(path=...)` parsing `UID_MIN`, `UID_MAX`,
  `SYS_UID_MIN`, `SYS_UID_MAX` with defaults 1000/60000/100/999, comment
  stripping, integer and range validation, and warnings. Verify tests for
  missing keys, malformed values, and an unreadable file.
- [x] 2.2 Implement `classify(account, ranges)` with the five ordered rules from
  design D3 and the non-login shell and bogus home lists. Verify the matrix:
  root, regular user, nologin service, legacy UID below `SYS_UID_MIN`,
  `nobody`, out-of-range unknown, and a normal-range account with nologin.
- [x] 2.3 Document the heuristic in the `--help` epilog and `README.md`. Verify
  the explanation appears in both and that `--help` still exits 0.

## 3. Data sources

- [x] 3.1 Implement account and group enumeration through `pwd`/`grp` with a
  `getent` fallback, field-count validation, `LC_ALL=C`, argv lists, and a
  5-second timeout. Verify unit tests with fakes and a simulated native failure
  that falls back to `getent`.
- [x] 3.2 Implement `load_accounts()` and `load_groups()` mapping records to
  dataclasses and resolving primary group names, falling back to the numeric
  GID when no group matches. Verify tests for resolved and unresolved GIDs.
- [x] 3.3 Implement session retrieval through `who` with the lenient parser and
  raw-line fallback from design D6. Verify tests with two sessions for one
  user, an extra column, and malformed output.
- [x] 3.4 Verify a live read-only read on the host:
  `python3 -c "import userls; print(len(userls.load_accounts()))"` reports 34
  accounts and `load_sessions()` returns the current session, without root.

## 4. Output layer

- [x] 4.1 Implement the table renderer with display-width padding using
  `unicodedata.east_asian_width` and combining marks, plus the trailing summary
  line. Verify tests with accented and CJK names keep column alignment.
- [x] 4.2 Implement JSON rendering with `schema_version`, `count`, and the
  command key (`accounts`, `groups`, `sessions`). Verify
  `python3 userls.py --json | python3 -m json.tool` succeeds and tests assert
  the key set.
- [x] 4.3 Implement CSV rendering with the `csv` module, `lineterminator="\n"`,
  and `QUOTE_MINIMAL`. Verify tests for values containing commas, quotes, and
  newlines.
- [x] 4.4 Implement the `export <file>` writer that refuses to overwrite an
  existing file without `--force` and reports unwritable targets with exit 1.
  Verify tests for a new file, an existing file, `--force`, and an unwritable
  directory.
- [x] 4.5 Implement the color policy: TTY detection, `--no-color`, `NO_COLOR`,
  and no ANSI in machine formats. Verify tests with a pipe and a fake TTY.

## 5. Account commands

- [x] 5.1 Wire the default listing with name, UID, GID, primary group, home,
  shell, type, and the summary line. Verify the output includes root, the
  current user, and `nobody` with the expected types.
- [x] 5.2 Implement `--type` filtering for `normal`, `service`, `system`,
  `unknown`, and `all`. Verify tests per type and that `--type all` matches the
  unfiltered count.
- [x] 5.3 Implement `--search` with case-insensitive name substring matching and
  exact UID matching. Verify tests for name, UID, and a no-match search that
  exits 0 with zero rows.
- [x] 5.4 Implement `info <name|uid>` with the full record and a non-zero exit
  for unknown accounts. Verify tests for both lookup forms and the error path.
- [x] 5.5 Add usage examples for listing, filtering, searching, and `info` to
  `README.md`. Verify each documented command runs as written.

## 6. Group and session commands

- [x] 6.1 Implement the `groups` listing with name, GID, members, and explicit
  empty membership. Verify a group without members is still listed.
- [x] 6.2 Implement `groups <name|uid>` including the primary group even when
  the account is not listed as a member, deduplicated and ordered by GID.
  Verify tests for the primary-group case, multiple groups, and unknown user.
- [x] 6.3 Implement `sessions` rendering user, terminal, login time, and origin,
  with an empty result exiting 0. Verify tests for empty and multi-session
  output.
- [x] 6.4 Implement `who` failure reporting with exit 1 and no invented rows.
  Verify a test that simulates the failure and asserts stderr and the exit code.

## 7. Manual page and documentation

- [x] 7.1 Write `man/userls.1` covering synopsis, options, subcommands, exit
  codes, the heuristic classification, and the read-only/no-root guarantees.
  Verify `groff -man -Tascii man/userls.1` exits 0 and renders without warnings.
- [x] 7.2 Update `README.md` with requirements, install, usage, the JSON schema
  version, and the limitations from design D2 and D3. Verify links and that
  every documented command is valid.

## 8. Debian packaging

- [x] 8.1 Create `debian/control` with `debhelper-compat (= 13)`,
  `Architecture: all`, `Depends: python3 (>= 3.11)`, `Section: admin`,
  `Priority: optional`, `Rules-Requires-Root: no`, `Standards-Version: 4.7.4`.
  Verify `dpkg-checkbuilddeps` passes after installing `debhelper`.
- [x] 8.2 Create `debian/rules`, `debian/install` (script installed as
  `usr/bin/userls`, man page as `usr/share/man/man1/userls.1`),
  `debian/changelog` (`unstable`, version `1.0.0-1`), `debian/copyright`
  (DEP-5, `GPL-3+`, `Files: debian/*`), and `debian/watch` for GitHub tags.
  Verify `dpkg-buildpackage -us -uc -b` produces
  `userls_1.0.0-1_all.deb`.
- [x] 8.3 Add `debian/tests/control` and the smoke test script. Verify the
  script runs directly and `autopkgtest . -- null` passes when autopkgtest is
  available.
- [x] 8.4 Run `lintian` on the built package and fix every error. Verify
  `lintian --fail-on error` returns 0 and triage the remaining warnings.
- [x] 8.5 Verify the package contents with `dpkg-deb -c` and `dpkg-deb -I`
  (script mode 0755, man page present, no extra files). Install it in a
  disposable container or on the host only with explicit approval, then check
  `userls --version`, `man userls`, and that `apt remove userls` leaves no
  files behind.

## 9. Release artifacts

- [x] 9.1 Build the GitHub release `.deb` from the same source and generate
  `SHA256SUMS`. Verify `sha256sum -c SHA256SUMS` passes and the artifact name
  matches `userls_1.0.0-1_all.deb`.
- [x] 9.2 Document the release steps and the `3.0 (quilt)` version mapping in
  `README.md`. Verify the steps reproduce the artifact from a clean clone.

## 10. Integration checks

- [x] 10.1 Run `python3 -m unittest discover -s tests -v` and confirm every test
  passes on Python 3.11 and 3.13.
- [x] 10.2 Run `openspec validate add-userls-cli --strict` and confirm there are
  no errors or warnings.
- [x] 10.3 Manual acceptance pass on Debian 13: listing, each type filter,
  search by name and UID, `info`, `groups`, `groups <user>`, `sessions`, JSON,
  CSV, `export`, unknown user, and `--no-color`. Record the observed exit codes.

## Workflow follow-up

- Archive the change after review.
- Open the ITP and seek a sponsor in a separate change.
