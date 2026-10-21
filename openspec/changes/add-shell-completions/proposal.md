# Proposal

## Why

`userls` ships no shell completions: typing `userls <TAB>` offers nothing, and
subcommands, options and `--type` values must be recalled from `--help`. Every
packaged CLI is expected to complete itself in the common shells, and fish
users additionally see no description for accounts and values while
completing. Rootless installs also miss a built man-db index, so fish shows no
command description for `userls` until the user builds it manually.

## What Changes

- Add completion definitions for three shells, covering subcommands
  (`info`, `groups`, `sessions`, `export`), shared options (`--json`, `--csv`,
  `--no-color`, `--type`, `--search`, `--version`) in both accepted positions
  (before and after the subcommand), and the values of `--type`:
  - **fish**: every candidate carries a one-line description; `info` and
    `groups` complete live account names described with UID and type;
    `export` keeps file completion.
  - **bash**: same candidate coverage (no descriptions; bash limitation).
  - **zsh**: same candidate coverage as fish, using the native completion
    system.
- Dynamic completion enumerates accounts through `userls` itself and degrades
  silently when enumeration fails, never offering invented names.
- `debian/install` ships the three completion files to the standard vendor
  paths (`/usr/share/fish/vendor_completions.d/`,
  `/usr/share/bash-completion/completions/`, `/usr/share/zsh/vendor-completions/`).
- README documents rootless installation of the completions and running
  `mandb --user-db` so `man`, `whatis` and fish's command description resolve
  without the package.
- Tests: syntax and behavior checks per shell, skipped when the shell is not
  installed.
- Version bump to 1.1.0 with a `debian/changelog` entry.

## Capabilities

### New Capabilities

- `shell-completions`: candidate completion (subcommands, options, option
  values, live account names) with descriptions where the shell supports them,
  for fish, bash and zsh, and the availability of the `userls` command
  description through the manual-page database.

### Modified Capabilities

No requirement changes in existing capabilities: `userls` output, exit codes
and data access keep their current contracts.

## Impact

- New `completions/` directory with three files (`userls.fish`,
  `userls.bash`, `_userls`).
- `debian/install` gains three dh-exec lines; `debian/changelog` gains the
  1.1.0 entry; `__version__` in `userls.py` becomes 1.1.0.
- New test module for completion syntax and behavior.
- README: "Shell completions" section and a rootless man-db note.
- No new runtime dependencies; `userls` behavior itself is unchanged.
