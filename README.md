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

Download `userls_1.0.0-1_all.deb` and `SHA256SUMS` from the
[Releases page](https://github.com/Juancit015/userls/releases), verify the
checksum, then install:

```sh
sha256sum -c SHA256SUMS
sudo apt install ./userls_1.0.0-1_all.deb
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

### Build the Debian package

```sh
sudo apt install debhelper
dpkg-buildpackage -us -uc -b
ls ../userls_1.0.0-1_all.deb
```

## Usage

```
userls [--type TYPE] [--search TEXT] [--json|--csv] [--no-color]
userls info <name|uid>
userls groups [name|uid]
userls sessions
userls export <file> [--force]
```

Listing accounts, the default action:

```console
$ userls
NAME   UID   GID   GROUP  HOME        SHELL          TYPE
root   0     0     root   /root       /bin/bash      system
...
juan   1000  1000  juan   /home/juan  /usr/bin/fish  normal

34 accounts
```

Filter and search:

```console
$ userls --type service
$ userls --type all
$ userls --search juan
$ userls --search 1000
```

Inspect one account by name or UID:

```console
$ userls info juan
$ userls info 1000
```

Groups and sessions:

```console
$ userls groups
$ userls groups juan
$ userls sessions
```

Machine-readable output:

```console
$ userls --json
$ userls --csv
$ userls --type service --json
$ userls groups juan --json
```

Shared flags work before or after the subcommand, so `userls --json groups`
and `userls groups --json` are equivalent.

Export the current account view to a CSV file. `userls` refuses to overwrite
an existing file unless `--force` is given:

```console
$ userls export accounts.csv
$ userls --type service export service-accounts.csv
$ userls export accounts.csv --force
```

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

## Output formats

- **Table** (default): aligned columns with a trailing count line, colored by
  account type only when stdout is a TTY and neither `--no-color` nor the
  `NO_COLOR` environment variable is set.
- **JSON** (`--json`): one object on stdout, no diagnostics mixed in. Warnings
  always go to stderr.
- **CSV** (`--csv`): RFC 4180 quoting via the `csv` module, `\n` line endings.
  `export` writes the same CSV to a file.

### JSON schema

`schema_version` is `1`. It only changes on breaking output changes. The
command key is `accounts`, `groups` or `sessions`:

```json
{
  "schema_version": 1,
  "count": 1,
  "accounts": [
    {
      "name": "juan",
      "uid": 1000,
      "gid": 1000,
      "primary_group": "juan",
      "gecos": "Juan David",
      "home": "/home/juan",
      "shell": "/usr/bin/fish",
      "type": "normal"
    }
  ]
}
```

`groups` entries carry `name`, `gid` and `members` (a list). `sessions`
entries carry `user`, `tty`, `login_time`, `origin` and the `raw` `who` line.
`info --json` returns `schema_version`, the `account` object and the
configured `system_uid_range`.

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

The OpenSpec change that specifies this tool lives in
`openspec/changes/add-userls-cli/`; validate it with
`openspec validate add-userls-cli --strict`.

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
