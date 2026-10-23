# userls

Read-only CLI to inspect local user accounts, groups and active sessions.

`userls` answers the everyday administration questions — which accounts are
real people, which are service accounts, what groups a user belongs to, who is
logged in — as readable tables and as machine-readable JSON or CSV. It never
modifies accounts, passwords, groups or any system file.

**Status:** 1.0.0, packaged for Debian 12 (bookworm) and newer. The canonical
repository is <https://github.com/Juancit015/userls>.

## Why not `getent` or `lslogins`?

The raw sources are precise but not friendly. `getent passwd` prints
colon-separated records, and `lslogins` (util-linux) covers a lot of ground but
hard-codes the 101–999 system UID range, uses cryptic column names, and has no
JSON output.

`userls` adds:

- classification as `normal`, `service`, `system` or `unknown`, driven by the
  actual `UID_MIN`, `UID_MAX`, `SYS_UID_MIN` and `SYS_UID_MAX` values in
  `/etc/login.defs`, plus shell and home-path indicators
- groups, memberships and active sessions in the same tool
- `--json` and `--csv` output with a versioned schema
- Python standard library only: no third-party packages, no root

Classification is heuristic by nature. `userls` reports it as such and never
claims certainty; see [Account types](#account-types).

## Requirements

- Linux with NSS (tested on Debian 13 trixie; Debian 12 bookworm supported)
- Python 3.11 or newer (Debian 12 ships 3.11, Debian 13 ships 3.13)
- No root privileges, no network access, no third-party Python packages

`userls` reads account data through NSS (`pwd`/`grp`, with a `getent`
fallback), UID ranges from `/etc/login.defs`, and sessions from `who`. The
only file it ever writes is the target you name with `userls export`.

## Install

### From the `.deb` (GitHub releases)

Download `userls_1.3.0-1_all.deb` and `SHA256SUMS` from the
[Releases page](https://github.com/Juancit015/userls/releases), verify the
checksum, then install:

```sh
sha256sum -c SHA256SUMS
sudo apt install ./userls_1.3.0-1_all.deb
```

Remove it with `sudo apt remove userls`. The package ships no conffiles, no
maintainer scripts and no residual state.

### From source

```sh
git clone https://github.com/Juancit015/userls.git
cd userls
sudo install -m 0755 userls.py /usr/bin/userls
sudo install -m 0644 man/userls.1 /usr/share/man/man1/userls.1
```

Or install without root, in your user path:

```sh
install -Dm755 userls.py ~/.local/bin/userls
```

### Shell completions

The `.deb` installs fish, bash and zsh completions. For a rootless install,
copy the file for your shell from the clone:

```sh
# fish
install -Dm644 completions/userls.fish ~/.config/fish/completions/userls.fish
# bash
install -Dm644 completions/userls.bash ~/.local/share/bash-completion/completions/userls
# zsh
install -Dm644 completions/_userls ~/.local/share/zsh/site-functions/_userls
```

zsh only reads `~/.local/share/zsh/site-functions` when it is on `fpath`; add
`fpath=(~/.local/share/zsh/site-functions $fpath)` to `~/.zshrc` before
`compinit` runs.

The completions list subcommands, shared options and `--type` values; `info`
and `groups` also complete real account names, described with UID and type
where the shell displays descriptions. That listing is skipped silently when
`userls` is not on `PATH`.

A rootless man page install has no indexed database, so the one-line command
description that completion menus show (`userls (command)`) stays missing
until the index is built:

```sh
install -Dm644 man/userls.1 ~/.local/share/man/man1/userls.1
mandb --user-db
```

### Build the Debian package

```sh
sudo apt install debhelper
dpkg-buildpackage -us -uc -b
ls ../userls_1.3.0-1_all.deb
```

## Usage

```
userls [--type TYPE] [--search TEXT] [--json|--csv] [--no-color]
userls info <name|uid>
userls groups [name|uid]
userls perms [name|uid]
userls sessions
userls export <file> [--force]
```

Listing accounts, the default action:

```console
$ userls
NAME      UID   GID   GROUP     HOME            SHELL          TYPE
root      0     0     root      /root           /bin/bash      system
...
username  1000  1000  username  /home/username  /usr/bin/fish  normal

34 accounts
```

Filter and search:

```console
$ userls --type service
$ userls --type all
$ userls --search username
$ userls --search 1000
```

Inspect one account by name or UID:

```console
$ userls info username
$ userls info 1000
```

Groups and sessions:

```console
$ userls groups
$ userls groups username
$ userls sessions
```

Privilege levels:

```console
$ userls perms
$ userls perms username
$ userls perms 1000
```

Machine-readable output:

```console
$ userls --json
$ userls --csv
$ userls --type service --json
$ userls groups username --json
```

Shared flags work before or after the subcommand, so `userls --json groups`
and `userls groups --json` are equivalent.

Export the current account view to CSV or a styled HTML document. The target
extension selects the format: `.html` and `.htm` write HTML; `.csv` and every
other name write CSV. `userls` refuses to overwrite an existing file unless
`--force` is given:

```console
$ userls export accounts.csv
$ userls export accounts.html
$ userls --type service export service-accounts.csv
$ userls export accounts.html --force
```

The HTML document is self-contained and meant for reading or printing. Every
value is in its own table cell; headers are uppercase on a dark background;
account rows are bold; and the `TYPE` cell carries a background color: orange
for `system`, dark blue for `service`, green for `normal`, and gray for
`unknown`. Column widths follow the longest header or value and include
padding, so paths and names stay on one line. Long tables scroll horizontally
instead of squeezing the text.

The HTML header `FULL NAME` contains the first comma-separated GECOS component
with surrounding whitespace removed. An empty result is shown as `NA`, so
`juan,,,` becomes `juan` and a blank GECOS becomes `NA`. `PRIMARY GROUP` is a
separate column, not a group list. CSV keeps the lowercase `gecos` header and
the raw value, including the literal `"juan,,,"` field.

Disable color when piping through a pager that does not strip ANSI sequences.
Colors are only emitted when stdout is a terminal, so pipes are already clean:

```console
$ userls --no-color
```

## Account types

Classification is a heuristic, not an authoritative statement. Rules are
evaluated in order and the first match wins:

| Order | Condition | Type |
|-------|-----------|------|
| 1 | UID 0 | `system` |
| 2 | Shell is `/usr/sbin/nologin`, `/sbin/nologin`, `/bin/false` or `/usr/bin/false`, or the home path is empty, `/`, `/nonexistent` or `/dev/null` | `service` |
| 3 | `UID_MIN <= UID <= UID_MAX` from `/etc/login.defs` | `normal` |
| 4 | `1 <= UID < UID_MIN` | `system` |
| 5 | Anything else | `unknown` |

Consequences worth knowing:

- `nobody` (65534, `nologin`) is a `service` account by rule 2, even though its
  UID is outside every configured range.
- Debian ships legacy system accounts below `SYS_UID_MIN` (`bin` = 2,
  `sync` = 4); rule 4 classifies them as `system`.
- A real user whose shell is `/usr/sbin/nologin` is labeled `service`. Use
  `--type unknown` and `--json` to spot anomalies, and treat the type as a hint.

Home directories are deliberately **not** `stat()`ed: an autofs or NFS home
can block for seconds, and a listing command must never hang on a dead mount.

## Privilege levels

`userls perms` derives a privilege level from group membership. It is a
group-based hint, not an audit of sudoers, file modes or ACLs. Levels are
evaluated in order and the first match wins:

| Order | Condition | Level |
|-------|-----------|-------|
| 1 | UID 0 | `root` |
| 2 | Member of `sudo` or `wheel` | `sudo` |
| 3 | Member of `adm`, `disk`, `docker`, `lxd`, `libvirt`, `shadow` or `systemd-journal` | `privileged` |
| 4 | Anything else | `standard` |

The primary group counts as a membership, and only the mapped groups are shown,
so the output explains why an account received its level:

```console
$ userls perms
NAME      UID   TYPE    LEVEL  GROUPS
root      0     system  root   -
username  1000  normal  sudo   sudo, docker

34 accounts
```

Rows are ordered by level severity and then UID. `userls perms username` reports
one account with its level and every mapped group it holds, and exits 1 for an
unknown name or UID. `--type` and `--search` filter the listing, while
`--json`, `--csv` and `--no-color` behave as in the other commands.

## Output formats

- **Table** (default): aligned columns with a trailing count line, colored by
  account type only when stdout is a TTY and neither `--no-color` nor the
  `NO_COLOR` environment variable is set.
- **JSON** (`--json`): one object on stdout, no diagnostics mixed in. Warnings
  always go to stderr.
- **CSV** (`--csv`): RFC 4180 quoting via the `csv` module, `\n` line endings.
  `export` writes the same CSV when the target is `.csv` or any extension other
  than `.html`/`.htm`.
- **HTML** (`.html`/`.htm` export): a self-contained table with embedded CSS,
  uppercase headers, bold rows, account-type backgrounds, measured column
  widths and escaped values. It is a human-facing document; use CSV or JSON for
  data interchange.

### JSON schema

`schema_version` is `1`. It only changes on breaking output changes. The
command key is `accounts`, `groups`, `sessions` or `permissions`:

```json
{
  "schema_version": 1,
  "count": 1,
  "accounts": [
    {
      "name": "username",
      "uid": 1000,
      "gid": 1000,
      "primary_group": "username",
      "gecos": "User Name",
      "home": "/home/username",
      "shell": "/usr/bin/fish",
      "type": "normal"
    }
  ]
}
```

`groups` entries carry `name`, `gid` and `members` (a list). `sessions`
entries carry `user`, `tty`, `login_time`, `origin` and the `raw` `who` line.
`permissions` entries carry `name`, `uid`, `type`, `level` and `groups` (a
list of the mapped groups held). `info --json` returns `schema_version`, the
`account` object and the configured `system_uid_range`; `perms NAME --json`
returns `schema_version`, the `account` object and a `permission` object with
`level` and `groups`.

## Exit status

- `0` — success, including searches that match nothing
- `1` — runtime failure (account not found, unwritable export target, `who`
  failed, malformed source)
- `2` — usage error (unknown option or subcommand), reported by `argparse`

## Limitations

- **Enumeration is NSS-bound.** Backends that do not enumerate (for example
  SSSD with `enumerate = false`) are invisible to both `pwd`/`grp` and
  `getent`; `userls` cannot see what NSS does not expose.
- **Types are heuristic.** Service infrastructure occasionally uses real
  shells, and humans occasionally have `nologin`.
- **Privilege levels are group-based.** `userls perms` maps a closed set of
  groups to levels; it does not read sudoers, ACLs or file modes, and it cannot
  see indirect escalation paths.
- **Deleted homes are not detected** on purpose (no `stat()`; see above).
- **Sessions come from `who`.** Containers and SSH setups without utmp records
  may show nothing. The raw `who` line is preserved in the output.
- **Session times are C-locale** (`LC_ALL=C`), stable for scripts but not
  localized.
- **`/etc/login.defs` missing or malformed** falls back to the documented
  defaults (1000/60000/100/999) with a warning on stderr.

## Development

Run the test suite (standard library `unittest` only):

```sh
python3 -m unittest discover -s tests -v
```

Render the manual page locally:

```sh
man --local-file man/userls.1
groff -man -Tascii man/userls.1 >/dev/null
```

The behavioral specs live in `openspec/specs/`; the change that built the
tool is archived under `openspec/changes/archive/`. Validate the specs with
`openspec validate --all --strict`.

## Release process

1. Bump `__version__` in `userls.py` and add a `debian/changelog` entry
   (`userls (X.Y.Z-1) unstable`). The changelog is the single source of truth
   for the package version; `userls --version` prints the upstream version.
2. Commit and tag `vX.Y.Z`.
3. Build from a clean tree:
   `dpkg-buildpackage -us -uc -b` (source format `3.0 (quilt)`).
4. Generate and verify checksums:
   `sha256sum ../userls_X.Y.Z-1_all.deb > SHA256SUMS` and
   `sha256sum -c SHA256SUMS`.
5. Attach the `.deb` and `SHA256SUMS` to the GitHub release. Debian revisions
   (`-2`, `-3`, …) are for packaging-only fixes; archive builds are signed by
   Debian and are the authoritative artifact.

## License

GPL-3.0-or-later. See [LICENSE](LICENSE).
