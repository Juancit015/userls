# AGENTS.md

`userls` is a read-only CLI that inspects local accounts, groups and active
sessions. It ships as a Debian package (`userls`) and GitHub releases, and is
aimed at the Debian archive. All repo content — code, docs, specs, commits —
is English.

## Layout

- `userls.py` — the entire CLI: argparse, NSS access (`pwd`/`grp`, `getent`
  fallback), `who` sessions, table/JSON rendering. Installed as
  `/usr/bin/userls`.
- `tests/` — stdlib `unittest` only; no fixtures, no services, no CI. Run
  from the repo root: tests `import userls` and spawn `userls.py`. Shell
  completion behavior is pinned in `tests/test_completions.py` (skipped when
  a shell is missing).
- `completions/` — hand-written completions: `userls.fish`, `userls.bash`
  and `_userls` (zsh). Packaged into the shells' vendor completion
  directories via `debian/install`; keep candidate sets in sync with the CLI
  and with `openspec/specs/shell-completions`.
- `debian/` — debhelper packaging. `debian/changelog` is the package-version
  source of truth. `debian/install` is a dh-exec script (`userls.py =>
  usr/bin/userls`); keep the `#!/usr/bin/dh-exec` shebang.
- `man/userls.1`, `README.md` — user docs; keep them in sync with CLI changes.
- `openspec/specs/` — the behavioral contract (6 capabilities). Completed
  changes live under `openspec/changes/archive/`.

## Commands

```sh
python3 -m unittest discover -s tests -v     # full suite (109 tests)
python3 -m unittest tests.test_classify -v   # single module
openspec validate --all --strict             # spec contract check
dpkg-buildpackage -us -uc -b                 # .deb lands in the PARENT dir
lintian --fail-on error ../userls_2.0.0-1_all.deb
groff -man -Tascii man/userls.1 >/dev/null   # man page renders
```

## Hard constraints

- Python 3.11+ standard library only. Never add third-party dependencies.
- Read-only: no files are written; output is stdout only. No root, no
  network.
- Do not `stat()` home directories — deliberate; NFS/autofs homes can hang a
  listing. Do not "fix" this.
- Classification is first-match-wins (UID 0 → system; non-login shell or
  bogus home → service; `UID_MIN..UID_MAX` → normal; `1..UID_MIN-1` →
  system; else unknown). Rule changes must update `userls.py`, the README
  table, tests and `openspec/specs/account-inventory` together.
- Session times come from `who` with `LC_ALL=C` for script stability.

## Workflow

- Non-trivial behavior changes go through OpenSpec: `/opsx-propose` →
  `/opsx-apply` → `/opsx-archive` (see `.opencode/commands/` and
  `.opencode/skills/`). Artifacts are English (openspec config).
- A release bumps two versions: `__version__` in `userls.py` and a new
  `debian/changelog` entry. Build/release artifacts land in the parent dir
  and in the gitignored `dist/`.
- `dpkg-buildpackage` fills `debian/` with gitignored outputs; clean with
  `debian/rules clean`. The build re-runs the unit suite (`dh_auto_test`).
