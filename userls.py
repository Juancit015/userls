#!/usr/bin/python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Juan David Rivera Huancas
"""userls - read-only view of local accounts, groups and active sessions."""

from __future__ import annotations

import argparse
import csv
import grp
import json
import os
import pwd
import re
import subprocess
import sys
import unicodedata
from dataclasses import dataclass
from typing import Callable, Iterable, Sequence

__version__ = "1.1.0"
__prog__ = "userls"

SCHEMA_VERSION = 1
COMMAND_TIMEOUT = 5

ACCOUNT_TYPES = ("normal", "service", "system", "unknown")

NON_LOGIN_SHELLS = frozenset(
    {
        "/usr/sbin/nologin",
        "/sbin/nologin",
        "/bin/false",
        "/usr/bin/false",
    }
)

BOGUS_HOMES = frozenset({"", "/", "/nonexistent", "/dev/null"})

TYPE_COLORS = {
    "normal": "32",
    "service": "36",
    "system": "33",
    "unknown": "35",
}

TYPE_COLUMN = 6

WHO_RE = re.compile(
    r"^(?P<user>\S+)\s+(?P<tty>\S+)\s+"
    r"(?P<date>(?:\w{3}\s+\d{1,2})|\d{4}-\d{2}-\d{2})\s+"
    r"(?P<time>\d{1,2}:\d{2})"
    r"(?:\s+\((?P<origin>[^)]*)\))?\s*$"
)

EPILOG = """\
Account types are heuristic. userls classifies an account from its UID range
in /etc/login.defs, its shell, and its home path. It never claims certainty
and it never modifies accounts, passwords or groups.

Examples:
  userls
  userls --type service
  userls --search juan
  userls info 1000
  userls groups juan
  userls sessions
  userls --json
  userls export accounts.csv
"""


@dataclass(frozen=True)
class Account:
    name: str
    uid: int
    gid: int
    gecos: str
    home: str
    shell: str
    primary_group: str
    type: str


@dataclass(frozen=True)
class Group:
    name: str
    gid: int
    members: tuple[str, ...]


@dataclass(frozen=True)
class Session:
    user: str
    tty: str
    login_time: str
    origin: str
    raw: str


@dataclass(frozen=True)
class LoginDefs:
    uid_min: int = 1000
    uid_max: int = 60000
    sys_uid_min: int = 100
    sys_uid_max: int = 999

    def system_range_label(self) -> str:
        return f"{self.sys_uid_min}-{self.sys_uid_max}"


class UserlsError(Exception):
    """A runtime failure with the exit code it should produce."""

    def __init__(self, message: str, exit_code: int = 1) -> None:
        super().__init__(message)
        self.message = message
        self.exit_code = exit_code


class Diagnostics:
    """Collects non-fatal warnings so stdout stays machine-readable."""

    def __init__(self) -> None:
        self.messages: list[str] = []

    def warn(self, message: str) -> None:
        self.messages.append(message)

    def emit(self, stream: object | None = None) -> None:
        target = stream or sys.stderr
        for message in self.messages:
            print(f"{__prog__}: warning: {message}", file=target)


def load_login_defs(
    path: str = "/etc/login.defs",
    diagnostics: Diagnostics | None = None,
) -> LoginDefs:
    """Read UID ranges from login.defs, falling back to documented defaults."""
    diagnostics = diagnostics or Diagnostics()
    values = {
        "UID_MIN": 1000,
        "UID_MAX": 60000,
        "SYS_UID_MIN": 100,
        "SYS_UID_MAX": 999,
    }

    try:
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            lines = handle.readlines()
    except OSError as exc:
        reason = exc.strerror or str(exc)
        diagnostics.warn(
            f"cannot read {path}: {reason}; using default UID ranges "
            "1000-60000 and 100-999"
        )
        return LoginDefs()

    for lineno, raw_line in enumerate(lines, start=1):
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        key, raw_value = parts[0], parts[1]
        if key not in values:
            continue
        try:
            number = int(raw_value, 10)
        except ValueError:
            diagnostics.warn(
                f"{path}:{lineno}: invalid {key} value {raw_value!r}; "
                f"keeping {values[key]}"
            )
            continue
        if not 0 <= number <= 4294967295:
            diagnostics.warn(
                f"{path}:{lineno}: {key}={number} is out of range; "
                f"keeping {values[key]}"
            )
            continue
        values[key] = number

    if values["UID_MIN"] > values["UID_MAX"]:
        diagnostics.warn(
            f"{path}: UID_MIN is greater than UID_MAX; "
            "using the default user range 1000-60000"
        )
        values["UID_MIN"], values["UID_MAX"] = 1000, 60000
    if values["SYS_UID_MIN"] > values["SYS_UID_MAX"]:
        diagnostics.warn(
            f"{path}: SYS_UID_MIN is greater than SYS_UID_MAX; "
            "using the default system range 100-999"
        )
        values["SYS_UID_MIN"], values["SYS_UID_MAX"] = 100, 999

    return LoginDefs(
        uid_min=values["UID_MIN"],
        uid_max=values["UID_MAX"],
        sys_uid_min=values["SYS_UID_MIN"],
        sys_uid_max=values["SYS_UID_MAX"],
    )


def classify(uid: int, shell: str, home: str, ranges: LoginDefs) -> str:
    """Return a heuristic account type. First matching rule wins."""
    if uid == 0:
        return "system"
    if shell in NON_LOGIN_SHELLS or home in BOGUS_HOMES:
        return "service"
    if ranges.uid_min <= uid <= ranges.uid_max:
        return "normal"
    if 1 <= uid < ranges.uid_min:
        return "system"
    return "unknown"


def run_command(
    argv: Sequence[str],
    diagnostics: Diagnostics | None = None,
    timeout: int = COMMAND_TIMEOUT,
) -> str:
    """Run a helper without a shell, in the C locale, and return its stdout."""
    env = dict(os.environ)
    env["LC_ALL"] = "C"
    try:
        completed = subprocess.run(
            list(argv),
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
            check=False,
        )
    except FileNotFoundError:
        raise UserlsError(f"{argv[0]}: command not found") from None
    except subprocess.TimeoutExpired:
        raise UserlsError(
            f"{argv[0]}: timed out after {timeout} seconds"
        ) from None
    except OSError as exc:
        raise UserlsError(f"{argv[0]}: {exc.strerror or exc}") from None

    if completed.returncode != 0:
        detail = completed.stderr.strip().splitlines()
        reason = detail[0] if detail else f"exit status {completed.returncode}"
        raise UserlsError(f"{argv[0]}: {reason}")
    return completed.stdout


def parse_passwd_records(
    text: str,
    diagnostics: Diagnostics,
) -> list[tuple[str, int, int, str, str, str]]:
    """Parse getent passwd output into validated tuples."""
    records: list[tuple[str, int, int, str, str, str]] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        fields = line.split(":")
        if len(fields) != 7:
            diagnostics.warn(
                f"getent passwd: skipping malformed line {lineno} "
                f"({len(fields)} fields)"
            )
            continue
        name, _password, raw_uid, raw_gid, gecos, home, shell = fields
        if name.startswith(("+", "-")):
            continue
        try:
            uid = int(raw_uid, 10)
            gid = int(raw_gid, 10)
        except ValueError:
            diagnostics.warn(
                f"getent passwd: skipping line {lineno} with a non-numeric ID"
            )
            continue
        records.append((name, uid, gid, gecos, home, shell))
    return records


def parse_group_records(
    text: str,
    diagnostics: Diagnostics,
) -> list[tuple[str, int, tuple[str, ...]]]:
    """Parse getent group output into validated tuples."""
    records: list[tuple[str, int, tuple[str, ...]]] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        fields = line.split(":")
        if len(fields) != 4:
            diagnostics.warn(
                f"getent group: skipping malformed line {lineno} "
                f"({len(fields)} fields)"
            )
            continue
        name, _password, raw_gid, raw_members = fields
        if name.startswith(("+", "-")):
            continue
        try:
            gid = int(raw_gid, 10)
        except ValueError:
            diagnostics.warn(
                f"getent group: skipping line {lineno} with a non-numeric GID"
            )
            continue
        members = tuple(member for member in raw_members.split(",") if member)
        records.append((name, gid, members))
    return records


def parse_who(
    text: str,
    diagnostics: Diagnostics,
) -> list[Session]:
    """Parse who output, keeping unmatched lines instead of dropping them."""
    sessions: list[Session] = []
    for lineno, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        match = WHO_RE.match(line)
        if match:
            sessions.append(
                Session(
                    user=match.group("user"),
                    tty=match.group("tty"),
                    login_time=f"{match.group('date')} {match.group('time')}",
                    origin=match.group("origin") or "",
                    raw=line,
                )
            )
            continue
        parts = line.split()
        if len(parts) < 2:
            diagnostics.warn(f"who: skipping malformed line {lineno}")
            continue
        diagnostics.warn(
            f"who: line {lineno} did not match the expected format; "
            "keeping the raw record"
        )
        sessions.append(
            Session(
                user=parts[0],
                tty=parts[1],
                login_time=" ".join(parts[2:]),
                origin="",
                raw=line,
            )
        )
    return sessions


class SystemDataSource:
    """Read-only access to accounts, groups and sessions through NSS."""

    def __init__(
        self,
        login_defs_path: str = "/etc/login.defs",
        diagnostics: Diagnostics | None = None,
    ) -> None:
        self.diagnostics = diagnostics or Diagnostics()
        self.ranges = load_login_defs(login_defs_path, self.diagnostics)
        self._accounts: list[Account] | None = None
        self._groups: list[Group] | None = None

    def accounts(self) -> list[Account]:
        if self._accounts is not None:
            return self._accounts

        records = self._native_accounts()
        if records is None:
            records = self._getent_accounts()

        group_names = {group.gid: group.name for group in self.groups()}
        accounts = [
            Account(
                name=name,
                uid=uid,
                gid=gid,
                gecos=gecos,
                home=home,
                shell=shell,
                primary_group=group_names.get(gid, str(gid)),
                type=classify(uid, shell, home, self.ranges),
            )
            for name, uid, gid, gecos, home, shell in records
        ]
        accounts.sort(key=lambda account: (account.uid, account.name))
        self._accounts = accounts
        return accounts

    def groups(self) -> list[Group]:
        if self._groups is not None:
            return self._groups

        records = self._native_groups()
        if records is None:
            records = self._getent_groups()

        groups = [
            Group(name=name, gid=gid, members=members)
            for name, gid, members in records
        ]
        groups.sort(key=lambda group: (group.gid, group.name))
        self._groups = groups
        return groups

    def sessions(self) -> list[Session]:
        output = run_command(["who"], self.diagnostics)
        return parse_who(output, self.diagnostics)

    def _native_accounts(self) -> list[tuple[str, int, int, str, str, str]] | None:
        try:
            return [
                (
                    entry.pw_name,
                    entry.pw_uid,
                    entry.pw_gid,
                    entry.pw_gecos,
                    entry.pw_dir,
                    entry.pw_shell,
                )
                for entry in pwd.getpwall()
            ]
        except Exception as exc:  # noqa: BLE001 - any failure means fall back
            self.diagnostics.warn(
                f"native account enumeration failed ({exc}); "
                "falling back to getent passwd"
            )
            return None

    def _native_groups(self) -> list[tuple[str, int, tuple[str, ...]]] | None:
        try:
            return [
                (entry.gr_name, entry.gr_gid, tuple(entry.gr_mem))
                for entry in grp.getgrall()
            ]
        except Exception as exc:  # noqa: BLE001 - any failure means fall back
            self.diagnostics.warn(
                f"native group enumeration failed ({exc}); "
                "falling back to getent group"
            )
            return None

    def _getent_accounts(self) -> list[tuple[str, int, int, str, str, str]]:
        output = run_command(["getent", "passwd"], self.diagnostics)
        return parse_passwd_records(output, self.diagnostics)

    def _getent_groups(self) -> list[tuple[str, int, tuple[str, ...]]]:
        output = run_command(["getent", "group"], self.diagnostics)
        return parse_group_records(output, self.diagnostics)


def load_accounts(
    login_defs_path: str = "/etc/login.defs",
    diagnostics: Diagnostics | None = None,
) -> list[Account]:
    return SystemDataSource(login_defs_path, diagnostics).accounts()


def load_groups(
    login_defs_path: str = "/etc/login.defs",
    diagnostics: Diagnostics | None = None,
) -> list[Group]:
    return SystemDataSource(login_defs_path, diagnostics).groups()


def load_sessions(diagnostics: Diagnostics | None = None) -> list[Session]:
    return SystemDataSource(diagnostics=diagnostics).sessions()


def filter_accounts(
    accounts: Iterable[Account],
    account_type: str = "all",
    search: str | None = None,
) -> list[Account]:
    result = list(accounts)
    if account_type != "all":
        result = [account for account in result if account.type == account_type]
    if search:
        term = search.strip()
        if term.isdigit():
            uid = int(term, 10)
            result = [account for account in result if account.uid == uid]
        else:
            folded = term.casefold()
            result = [
                account
                for account in result
                if folded in account.name.casefold()
            ]
    return result


def resolve_account(accounts: Iterable[Account], term: str) -> Account:
    cleaned = term.strip()
    if cleaned.isdigit():
        uid = int(cleaned, 10)
        for account in accounts:
            if account.uid == uid:
                return account
    else:
        for account in accounts:
            if account.name == cleaned:
                return account
    raise UserlsError(f"account not found: {term}")


def groups_for_account(source: SystemDataSource, term: str) -> list[Group]:
    account = resolve_account(source.accounts(), term)
    groups = [
        group
        for group in source.groups()
        if group.gid == account.gid or account.name in group.members
    ]

    by_gid: dict[int, Group] = {}
    for group in groups:
        by_gid.setdefault(group.gid, group)
    if account.gid not in by_gid:
        by_gid[account.gid] = Group(
            name=account.primary_group,
            gid=account.gid,
            members=(),
        )
    return [by_gid[gid] for gid in sorted(by_gid)]


def display_width(text: str) -> int:
    """Terminal display width, counting wide glyphs as two cells."""
    width = 0
    for char in text:
        if unicodedata.combining(char):
            continue
        width += 2 if unicodedata.east_asian_width(char) in ("W", "F") else 1
    return width


def pad(text: str, width: int) -> str:
    return text + " " * max(0, width - display_width(text))


def render_table(
    headers: Sequence[str],
    rows: Sequence[Sequence[str]],
    summary: str,
    color: Callable[[int, int, str], str] | None = None,
) -> str:
    color = color or (lambda _row, _column, value: value)
    widths = [
        max([display_width(header)] + [display_width(row[i]) for row in rows])
        for i, header in enumerate(headers)
    ]
    lines = [
        "  ".join(pad(header, widths[i]) for i, header in enumerate(headers)).rstrip()
    ]
    for row_index, row in enumerate(rows):
        padded = [pad(str(value), widths[i]) for i, value in enumerate(row)]
        colored = [
            color(row_index, column_index, value)
            for column_index, value in enumerate(padded)
        ]
        lines.append("  ".join(colored).rstrip())
    lines.extend(["", summary])
    return "\n".join(lines) + "\n"


def render_json(payload: object) -> str:
    return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"


def write_csv(
    stream: object,
    headers: Sequence[str],
    rows: Sequence[Sequence[object]],
) -> None:
    writer = csv.writer(stream, lineterminator="\n", quoting=csv.QUOTE_MINIMAL)
    writer.writerow(headers)
    writer.writerows(rows)


def write_csv_file(
    path: str,
    headers: Sequence[str],
    rows: Sequence[Sequence[object]],
    force: bool = False,
) -> None:
    if os.path.exists(path) and not force:
        raise UserlsError(f"{path} already exists; use --force to overwrite")
    try:
        with open(path, "w", encoding="utf-8", newline="") as handle:
            write_csv(handle, headers, rows)
    except OSError as exc:
        raise UserlsError(
            f"cannot write {path}: {exc.strerror or exc}"
        ) from None


def account_dict(account: Account) -> dict[str, object]:
    return {
        "name": account.name,
        "uid": account.uid,
        "gid": account.gid,
        "primary_group": account.primary_group,
        "gecos": account.gecos,
        "home": account.home,
        "shell": account.shell,
        "type": account.type,
    }


def accounts_payload(accounts: Sequence[Account]) -> dict[str, object]:
    return {
        "schema_version": SCHEMA_VERSION,
        "count": len(accounts),
        "accounts": [account_dict(account) for account in accounts],
    }


def groups_payload(groups: Sequence[Group]) -> dict[str, object]:
    return {
        "schema_version": SCHEMA_VERSION,
        "count": len(groups),
        "groups": [
            {"name": group.name, "gid": group.gid, "members": list(group.members)}
            for group in groups
        ],
    }


def sessions_payload(sessions: Sequence[Session]) -> dict[str, object]:
    return {
        "schema_version": SCHEMA_VERSION,
        "count": len(sessions),
        "sessions": [
            {
                "user": session.user,
                "tty": session.tty,
                "login_time": session.login_time,
                "origin": session.origin,
                "raw": session.raw,
            }
            for session in sessions
        ],
    }


def color_enabled(args: argparse.Namespace, stream: object | None = None) -> bool:
    target = stream or sys.stdout
    if getattr(args, "json", False) or getattr(args, "csv", False):
        return False
    if getattr(args, "no_color", False):
        return False
    if "NO_COLOR" in os.environ:
        return False
    return bool(getattr(target, "isatty", lambda: False)())


def type_colorizer(enabled: bool) -> Callable[[int, int, str], str]:
    if not enabled:
        return lambda _row, _column, value: value

    def colorize(_row: int, column: int, value: str) -> str:
        if column != TYPE_COLUMN:
            return value
        code = TYPE_COLORS.get(value.strip())
        return f"\033[{code}m{value}\033[0m" if code else value

    return colorize


def count_label(count: int, singular: str) -> str:
    return f"{count} {singular}{'' if count == 1 else 's'}"


def print_accounts(accounts: Sequence[Account], args: argparse.Namespace) -> None:
    headers = ["NAME", "UID", "GID", "GROUP", "HOME", "SHELL", "TYPE"]
    rows = [
        [
            account.name,
            str(account.uid),
            str(account.gid),
            account.primary_group,
            account.home,
            account.shell,
            account.type,
        ]
        for account in accounts
    ]

    if getattr(args, "json", False):
        sys.stdout.write(render_json(accounts_payload(accounts)))
        return
    if getattr(args, "csv", False):
        write_csv(
            sys.stdout,
            ["name", "uid", "gid", "primary_group", "gecos", "home", "shell", "type"],
            [
                [
                    account.name,
                    account.uid,
                    account.gid,
                    account.primary_group,
                    account.gecos,
                    account.home,
                    account.shell,
                    account.type,
                ]
                for account in accounts
            ],
        )
        return
    sys.stdout.write(
        render_table(
            headers,
            rows,
            count_label(len(accounts), "account"),
            type_colorizer(color_enabled(args)),
        )
    )


def print_groups(
    groups: Sequence[Group],
    args: argparse.Namespace,
    owner: str | None = None,
) -> None:
    headers = ["NAME", "GID", "MEMBERS"]
    rows = [
        [group.name, str(group.gid), ", ".join(group.members) or "-"]
        for group in groups
    ]
    summary = count_label(len(groups), "group")
    if owner is not None:
        summary = f"{summary} for {owner}"

    if getattr(args, "json", False):
        payload = groups_payload(groups)
        if owner is not None:
            payload["account"] = owner
        sys.stdout.write(render_json(payload))
        return
    if getattr(args, "csv", False):
        write_csv(
            sys.stdout,
            ["name", "gid", "members"],
            [[group.name, group.gid, ",".join(group.members)] for group in groups],
        )
        return
    sys.stdout.write(render_table(headers, rows, summary))


def print_sessions(sessions: Sequence[Session], args: argparse.Namespace) -> None:
    headers = ["USER", "TTY", "LOGIN", "ORIGIN"]
    rows = [
        [session.user, session.tty, session.login_time, session.origin or "-"]
        for session in sessions
    ]

    if getattr(args, "json", False):
        sys.stdout.write(render_json(sessions_payload(sessions)))
        return
    if getattr(args, "csv", False):
        write_csv(
            sys.stdout,
            ["user", "tty", "login_time", "origin", "raw"],
            [
                [session.user, session.tty, session.login_time, session.origin, session.raw]
                for session in sessions
            ],
        )
        return
    sys.stdout.write(
        render_table(headers, rows, count_label(len(sessions), "session"))
    )


def print_info(
    account: Account,
    ranges: LoginDefs,
    args: argparse.Namespace,
) -> None:
    record = account_dict(account)
    record["system_uid_range"] = ranges.system_range_label()

    if getattr(args, "json", False):
        sys.stdout.write(
            render_json(
                {
                    "schema_version": SCHEMA_VERSION,
                    "account": account_dict(account),
                    "system_uid_range": ranges.system_range_label(),
                }
            )
        )
        return
    if getattr(args, "csv", False):
        headers = list(record)
        write_csv(sys.stdout, headers, [[record[key] for key in headers]])
        return

    labels = [
        ("Name", account.name),
        ("UID", str(account.uid)),
        ("GID", str(account.gid)),
        ("Primary group", account.primary_group),
        ("GECOS", account.gecos),
        ("Home", account.home),
        ("Shell", account.shell),
        ("Type", account.type),
        ("System UID range", ranges.system_range_label()),
    ]
    width = max(display_width(label) for label, _value in labels) + 2
    for label, value in labels:
        sys.stdout.write(f"{pad(label + ':', width)}{value}\n")


def build_parser() -> argparse.ArgumentParser:
    output = argparse.ArgumentParser(add_help=False)
    output_group = output.add_mutually_exclusive_group()
    output_group.add_argument(
        "--json",
        action="store_true",
        default=argparse.SUPPRESS,
        help="render the result as JSON on stdout",
    )
    output_group.add_argument(
        "--csv",
        action="store_true",
        default=argparse.SUPPRESS,
        help="render the result as CSV on stdout",
    )
    output.add_argument(
        "--no-color",
        action="store_true",
        default=argparse.SUPPRESS,
        help="disable ANSI color",
    )

    filters = argparse.ArgumentParser(add_help=False)
    filters.add_argument(
        "--type",
        dest="account_type",
        choices=("all",) + ACCOUNT_TYPES,
        default=argparse.SUPPRESS,
        metavar="TYPE",
        help="filter accounts by type: all, normal, service, system, unknown",
    )
    filters.add_argument(
        "--search",
        metavar="TEXT",
        default=argparse.SUPPRESS,
        help="search accounts by name (substring) or UID (exact)",
    )

    parser = argparse.ArgumentParser(
        prog=__prog__,
        description="Read-only view of local accounts, groups and active sessions.",
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        parents=[output, filters],
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    subparsers = parser.add_subparsers(dest="command", metavar="COMMAND")

    info = subparsers.add_parser(
        "info",
        parents=[output],
        help="show one account",
        description="Show the full record of one account by name or UID.",
    )
    info.add_argument("account", metavar="NAME|UID")

    groups = subparsers.add_parser(
        "groups",
        parents=[output],
        help="list groups or the groups of one account",
        description=(
            "List every group, or the groups that belong to one account, "
            "including the primary group."
        ),
    )
    groups.add_argument("account", nargs="?", metavar="NAME|UID")

    subparsers.add_parser(
        "sessions",
        parents=[output],
        help="list active login sessions",
        description="List the sessions reported by who.",
    )

    export = subparsers.add_parser(
        "export",
        parents=[output, filters],
        help="export the account list to a CSV file",
        description=(
            "Write the current account view to a CSV file. Refuses to "
            "overwrite an existing file unless --force is given."
        ),
    )
    export.add_argument("file", metavar="FILE")
    export.add_argument(
        "--force",
        action="store_true",
        help="overwrite the target file if it already exists",
    )

    return parser


def run(args: argparse.Namespace, diagnostics: Diagnostics) -> int:
    source = SystemDataSource(diagnostics=diagnostics)

    if args.command == "sessions":
        print_sessions(source.sessions(), args)
        return 0

    if args.command == "groups":
        if args.account:
            print_groups(
                groups_for_account(source, args.account),
                args,
                owner=args.account,
            )
        else:
            print_groups(source.groups(), args)
        return 0

    if args.command == "info":
        account = resolve_account(source.accounts(), args.account)
        print_info(account, source.ranges, args)
        return 0

    accounts = filter_accounts(
        source.accounts(),
        getattr(args, "account_type", "all"),
        getattr(args, "search", None),
    )

    if args.command == "export":
        headers = [
            "name",
            "uid",
            "gid",
            "primary_group",
            "gecos",
            "home",
            "shell",
            "type",
        ]
        rows = [
            [
                account.name,
                account.uid,
                account.gid,
                account.primary_group,
                account.gecos,
                account.home,
                account.shell,
                account.type,
            ]
            for account in accounts
        ]
        write_csv_file(args.file, headers, rows, force=args.force)
        return 0

    print_accounts(accounts, args)
    return 0


def configure_streams() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8")
            except (ValueError, OSError):
                pass


def main(argv: Sequence[str] | None = None) -> int:
    configure_streams()
    parser = build_parser()
    args = parser.parse_args(argv)
    diagnostics = Diagnostics()

    try:
        code = run(args, diagnostics)
    except UserlsError as exc:
        diagnostics.emit()
        print(f"{__prog__}: {exc.message}", file=sys.stderr)
        return exc.exit_code
    except BrokenPipeError:
        try:
            devnull = os.open(os.devnull, os.O_WRONLY)
            os.dup2(devnull, sys.stdout.fileno())
        except OSError:
            pass
        return 0

    diagnostics.emit()
    return code


if __name__ == "__main__":
    sys.exit(main())
