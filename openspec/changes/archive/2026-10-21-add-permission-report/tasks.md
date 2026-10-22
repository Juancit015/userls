# Tasks

## 1. Privilege model

- [x] 1.1 Add `PRIVILEGE_LEVELS`, `PRIVILEGE_GROUPS` and a first-match
      `privilege_level()` to `userls.py`, with `Permission` records carrying
      name, UID, account type, level and granting groups. Verify: unit tests
      cover UID 0 winning over groups, `sudo` winning over `privileged`, and an
      account with no mapped group ending as `standard`.
- [x] 1.2 Add a batch membership index that unions each account's primary
      group with the groups listing it as a member. Verify: unit tests cover a
      primary-group-only grant, a supplementary grant, and an account in no
      mapped group.
- [x] 1.3 Order the report by level rank then UID then name. Verify: a unit
      test with mixed levels asserts the exact output order.

## 2. `perms` command

- [x] 2.1 Add the `perms` subparser with an optional `NAME|UID`, sharing the
      output and filter option groups, and dispatch it in `run()`. Verify:
      `./userls.py perms --help` exits 0 and
      `./userls.py perms --json | python3 -m json.tool` exits 0.
- [x] 2.2 Render the listing table with name, UID, type, level, granting
      groups and the trailing summary count, and the single-account detail with
      the same `Label: value` layout as `info`. Verify: CLI tests assert the
      header, the row order and the `-` placeholder for an empty group list.
- [x] 2.3 Emit the listing and detail payloads for `--json` and `--csv`,
      keeping `schema_version` at 1 and diagnostics on stderr. Verify: tests
      parse the JSON payload and the CSV header, and confirm no ANSI escapes.
- [x] 2.4 Handle the error and filter paths: unknown name or UID exits 1 with
      a stderr message, `--type` and `--search` narrow the listing, and a
      single-account report ignores them. Verify: CLI tests assert the exit
      status, the stderr text and the filtered row sets.
- [x] 2.5 Document `perms` in `README.md` and `man/userls.1`: synopsis, the
      level table with its group mapping, the format flags and the filters.
      Verify: `groff -man -Tascii man/userls.1 >/dev/null` succeeds and every
      documented command runs as written.

## 3. Shell completions

- [x] 3.1 Add `perms` to `completions/userls.fish` with a one-line description
      and extend the live-account condition to `info`, `groups` and `perms`.
      Verify: `fish --no-execute completions/userls.fish` exits 0 and
      `fish -c "complete -C'userls '"` lists `perms`.
- [x] 3.2 Add `perms` to the subcommand and section lists in
      `completions/userls.bash`. Verify: `bash -n completions/userls.bash`
      exits 0 and the existing completion harness lists `perms`.
- [x] 3.3 Add `perms` to the subcommand list and account-completion condition
      in `completions/_userls`. Verify: `zsh -n completions/_userls` exits 0
      and the `zsh -f` harness offers `perms`.
- [x] 3.4 Update the expectations in `tests/test_completions.py` for the new
      subcommand and for account completion after `perms`. Verify:
      `python3 -m unittest tests.test_completions -v` passes with every
      available shell.

## 4. Packaging and release

- [x] 4.1 Bump `__version__` to `1.2.0`, add the `debian/changelog` entry
      `userls (1.2.0-1) unstable`, and update the version references in
      `README.md` and `AGENTS.md`. Verify: `./userls.py --version` prints
      `1.2.0` and `dpkg-parsechangelog -SVersion` prints `1.2.0-1`.
- [x] 4.2 Build the package and inspect it. Verify:
      `dpkg-buildpackage -us -uc -b` succeeds, `dpkg -c
      ../userls_1.2.0-1_all.deb` lists the three completion files, and
      `lintian --fail-on error ../userls_1.2.0-1_all.deb` reports 0 errors.

## 5. Integration verification

- [x] 5.1 Run the full suite and the spec contract. Verify:
      `python3 -m unittest discover -s tests -v` passes on Python 3.11 and the
      system Python, and `openspec validate --all --strict` reports 0 failures.
- [x] 5.2 Exercise the package on a clean `debian:13` container: install it,
      confirm `userls perms` lists levels and `userls perms root --json` parses,
      confirm `man -f userls` resolves, then purge and check for leftovers.

## Workflow follow-up

- Archive the change after review, syncing the `permission-report` spec and the
  `shell-completions` delta into the main specs.
- Commit, push, and publish the v1.2.0 GitHub release with the `.deb` and
  `SHA256SUMS` when the release is approved.
