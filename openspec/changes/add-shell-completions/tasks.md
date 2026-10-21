# Tasks

## 1. Fish completion

- [x] 1.1 Create `completions/userls.fish`: subcommands (`info`, `groups`,
      `sessions`, `export`) with descriptions; shared options in both accepted
      positions; `--type` values (`all`, `normal`, `service`, `system`,
      `unknown`) with descriptions; live account candidates for `info`/`groups`
      from `userls --csv` (name + `uid N · type`, silent on failure, options
      win when the argument starts with `-`); files after `export`.
      Verify: `fish --no-execute completions/userls.fish` exits 0 and
      `fish -c "complete -C'userls '"` lists the four subcommands.
- [x] 1.2 Add `tests/test_completions.py` with fish syntax and behavior tests
      (guarded by `unittest.skipUnless(shutil.which("fish"))`), pinning the
      subcommand, option and `--type` candidate sets and the live-account
      format. Verify: `python3 -m unittest tests.test_completions -v` passes.

## 2. Bash completion

- [x] 2.1 Create `completions/userls.bash` without requiring
      `bash-completion` helpers: subcommands, shared options in both
      positions, `--type` values, live accounts after `info`/`groups`, files
      after `export`; sourcing must be harmless when `userls` is absent.
      Verify: `bash -n completions/userls.bash` exits 0 and
      `bash -c 'source completions/userls.bash; COMP_WORDS=(userls ""); COMP_CWORD=1; _userls; printf "%s\n" "${COMPREPLY[@]}"'`
      lists `info`, `groups`, `sessions` and `export`.
- [x] 2.2 Extend `tests/test_completions.py` with bash syntax and behavior
      tests. Verify: `python3 -m unittest tests.test_completions -v` passes.

## 3. Zsh completion

- [x] 3.1 Create `completions/_userls` (`#compdef userls`) using `_arguments`,
      `_describe` with `name:description` items (accounts described with UID
      and type) and `_files` for `export`. Verify:
      `zsh -n completions/_userls` exits 0 and a `zsh -f` harness with
      compinit offers `info`, `groups`, `sessions` and `export`.
- [x] 3.2 Extend `tests/test_completions.py` with zsh syntax and behavior
      tests (behavior check skips if the compinit harness cannot initialize).
      Verify: `python3 -m unittest tests.test_completions -v` passes.

## 4. Packaging and versioning

- [x] 4.1 Add the three dh-exec lines to `debian/install` mapping
      `completions/userls.fish`, `completions/userls.bash` and
      `completions/_userls` to the fish, bash-completion and zsh vendor
      directories. Verify: `dpkg-buildpackage -us -uc -b` succeeds and
      `dpkg -c ../userls_1.1.0-1_all.deb` lists the three vendor paths.
- [x] 4.2 Bump `__version__` in `userls.py` to `1.1.0` and add the
      `debian/changelog` entry `userls (1.1.0-1) unstable`. Verify:
      `./userls.py --version` prints `1.1.0` and
      `dpkg-parsechangelog -SVersion` prints `1.1.0-1`.
- [x] 4.3 Extend `debian/tests/smoke` to assert the three completion files
      exist at their vendor paths, and run
      `lintian --fail-on error ../userls_1.1.0-1_all.deb`. Verify: the smoke
      script passes inside the package container and lintian reports 0
      errors.

## 5. Documentation

- [x] 5.1 Add a "Shell completions" section to `README.md` with the per-shell
      rootless destinations (fish `~/.config/fish/completions/`, bash
      `~/.local/share/bash-completion/completions/`, zsh
      `~/.local/share/zsh/site-functions/` including the `fpath` note) and
      the rootless `mandb --user-db` step for the command description.
      Verify: run each documented install line against a scratch `HOME` and
      confirm the file lands at the documented path.
- [x] 5.2 Add `completions/` to the layout section of `AGENTS.md`. Verify:
      the file lists the directory and `git status` shows only intended
      changes.

## 6. Integration verification and release

- [x] 6.1 Run the full test suite on both Pythons: system `python3` and the
      uv-managed 3.11. Verify: `python3 -m unittest discover -s tests -v` and
      the 3.11 interpreter run both pass with the new tests included.
- [x] 6.2 End-to-end check in a disposable Debian container: install the
      built `.deb`, confirm the three vendor files, run a fish completion
      query for `userls`, confirm `man -f userls` resolves, then remove the
      package and confirm no leftovers. Verify: all checks pass inside the
      container and no container or volume is left behind.
- [x] 6.3 Build the release artifacts: `dist/userls_1.1.0-1_all.deb` and
      `dist/SHA256SUMS`. Verify: `sha256sum -c dist/SHA256SUMS` passes.
- [ ] 6.4 Publish the GitHub release `v1.1.0` with the `.deb` and
      `SHA256SUMS`, and verify the published asset: download it and confirm
      the checksum matches. Verify: release page lists both assets and the
      downloaded checksum passes.

## Workflow follow-up

- Archive the change with `/opsx-archive` once the release is reviewed.
- The Debian ITP and sponsorship remain a separate future change.
