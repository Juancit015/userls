# userls

A friendly CLI to inspect local user accounts, groups and active sessions on
Debian.

**Status:** pre-alpha. Design phase, nothing runnable yet.

## Why

`getent passwd` and `lslogins` expose the raw data, but not a readable answer.
`userls` aims to provide:

- account classification as normal, service or system, based on the ranges in
  `/etc/login.defs` plus shell and home directory heuristics
- groups and active sessions in the same place
- `--json` and `--csv` output for scripting
- no third-party dependencies: Python 3 standard library only

Classification is heuristic by nature. `userls` reports it as such and never
claims certainty.

## Requirements

- Debian 12 (bookworm) or newer
- Python 3.11+

`userls` is read-only. It never creates, modifies or deletes accounts.

## Install

Not released yet.

## Roadmap

- [ ] CLI implementation
- [ ] test suite
- [ ] Debian packaging (`debian/`, man page, autopkgtest)
- [ ] `.deb` releases on GitHub
- [ ] ITP and upload to the Debian archive

## License

GPL-3.0-or-later. See [LICENSE](LICENSE).
