import unittest

import contextlib
import csv
import io
import json
from unittest import mock

import userls
from userls import (
    Account,
    Group,
    PRIVILEGE_GROUPS,
    PRIVILEGE_LEVELS,
    membership_index,
    permission_for,
    privilege_groups,
    privilege_level,
    privilege_report,
)


def make_account(name="alice", uid=1000, primary_group=None, account_type="normal"):
    return Account(
        name,
        uid,
        uid if primary_group is None else 0,
        "",
        f"/home/{name}",
        "/bin/bash",
        primary_group or name,
        account_type,
    )


def make_group(name, gid=1000, members=()):
    return Group(name, gid, tuple(members))


class PrivilegeLevelTests(unittest.TestCase):
    def test_root_wins_over_groups(self):
        self.assertEqual(privilege_level(0, {"docker", "sudo"}), "root")

    def test_sudo_group(self):
        self.assertEqual(privilege_level(1000, {"sudo"}), "sudo")

    def test_wheel_group(self):
        self.assertEqual(privilege_level(1000, {"wheel"}), "sudo")

    def test_sudo_wins_over_privileged(self):
        self.assertEqual(privilege_level(1000, {"docker", "sudo"}), "sudo")

    def test_each_privileged_group(self):
        for name in PRIVILEGE_GROUPS["privileged"]:
            with self.subTest(group=name):
                self.assertEqual(privilege_level(1000, {name}), "privileged")

    def test_unmapped_groups_stay_standard(self):
        self.assertEqual(privilege_level(1000, {"audio", "users"}), "standard")

    def test_no_groups_is_standard(self):
        self.assertEqual(privilege_level(1000, set()), "standard")

    def test_levels_are_ordered_by_severity(self):
        self.assertEqual(
            PRIVILEGE_LEVELS, ("root", "sudo", "privileged", "standard")
        )


class PrivilegeGroupsTests(unittest.TestCase):
    def test_mapping_is_explicit(self):
        self.assertEqual(PRIVILEGE_GROUPS["sudo"], ("sudo", "wheel"))
        self.assertEqual(
            set(PRIVILEGE_GROUPS["privileged"]),
            {"adm", "disk", "docker", "lxd", "libvirt", "shadow", "systemd-journal"},
        )

    def test_only_mapped_groups_are_reported(self):
        self.assertEqual(
            privilege_groups({"audio", "docker", "sudo"}), ("sudo", "docker")
        )

    def test_empty_when_none_held(self):
        self.assertEqual(privilege_groups({"audio"}), ())


class MembershipTests(unittest.TestCase):
    def test_index_maps_members_to_groups(self):
        index = membership_index(
            [make_group("sudo", 27, ("juan",)), make_group("docker", 998, ("ana", "juan"))]
        )
        self.assertEqual(index["juan"], {"sudo", "docker"})
        self.assertEqual(index["ana"], {"docker"})

    def test_primary_group_grants_level(self):
        permission = permission_for(make_account(primary_group="sudo"), [])
        self.assertEqual(permission.level, "sudo")
        self.assertEqual(permission.groups, ("sudo",))

    def test_supplementary_group_grants_level(self):
        permission = permission_for(
            make_account(), [make_group("docker", 998, ("alice",))]
        )
        self.assertEqual(permission.level, "privileged")
        self.assertEqual(permission.groups, ("docker",))

    def test_account_without_mapped_groups(self):
        permission = permission_for(
            make_account(), [make_group("audio", 29, ("alice",))]
        )
        self.assertEqual(permission.level, "standard")
        self.assertEqual(permission.groups, ())
        self.assertEqual(permission.account_type, "normal")


class ReportOrderTests(unittest.TestCase):
    def test_severity_then_uid_then_name(self):
        accounts = [
            make_account("carol", 1000),
            make_account("bob", 1001),
            make_account("alice", 1002),
            make_account("root", 0, primary_group="root", account_type="system"),
        ]
        groups = [
            make_group("sudo", 27, ("alice",)),
            make_group("docker", 998, ("bob",)),
        ]
        report = privilege_report(accounts, groups)
        self.assertEqual(
            [(item.name, item.level) for item in report],
            [
                ("root", "root"),
                ("alice", "sudo"),
                ("bob", "privileged"),
                ("carol", "standard"),
            ],
        )

    def test_same_level_ordered_by_uid(self):
        accounts = [make_account("zed", 1005), make_account("amy", 1003)]
        report = privilege_report(accounts, [])
        self.assertEqual([item.name for item in report], ["amy", "zed"])

    def test_primary_group_counts_in_batch_report(self):
        accounts = [make_account("ops", 1000, primary_group="sudo")]
        report = privilege_report(accounts, [make_group("sudo", 27)])
        self.assertEqual(report[0].level, "sudo")


ACCOUNTS = [
    Account("root", 0, 0, "root", "/root", "/bin/bash", "root", "system"),
    Account("alice", 1000, 1000, "", "/home/alice", "/bin/bash", "alice", "normal"),
    Account("bob", 1001, 1001, "", "/home/bob", "/usr/sbin/nologin", "bob", "service"),
    Account("carol", 1002, 1002, "", "/home/carol", "/bin/bash", "carol", "normal"),
]

GROUPS = [
    Group("root", 0, ()),
    Group("alice", 1000, ()),
    Group("bob", 1001, ()),
    Group("carol", 1002, ()),
    Group("sudo", 27, ("alice",)),
    Group("docker", 998, ("carol",)),
]


class FakeSource:
    def __init__(self, *args, **kwargs):
        self.ranges = userls.LoginDefs()

    def accounts(self):
        return list(ACCOUNTS)

    def groups(self):
        return list(GROUPS)


def run_main(argv):
    stdout = io.StringIO()
    stderr = io.StringIO()
    with mock.patch("userls.SystemDataSource", FakeSource):
        with contextlib.redirect_stdout(stdout):
            with contextlib.redirect_stderr(stderr):
                code = userls.main(argv)
    return code, stdout.getvalue(), stderr.getvalue()


class PermissionCommandTests(unittest.TestCase):
    def test_listing_table(self):
        code, out, err = run_main(["perms"])
        self.assertEqual(code, 0)
        self.assertEqual(err, "")
        lines = out.splitlines()
        self.assertEqual(lines[0].split(), ["NAME", "UID", "TYPE", "LEVEL", "GROUPS"])
        self.assertEqual(
            [line.split()[0] for line in lines[1:5]],
            ["root", "alice", "carol", "bob"],
        )
        self.assertEqual(lines[1].split(), ["root", "0", "system", "root", "-"])
        self.assertEqual(
            lines[2].split(), ["alice", "1000", "normal", "sudo", "sudo"]
        )
        self.assertEqual(
            lines[3].split(), ["carol", "1002", "normal", "privileged", "docker"]
        )
        self.assertEqual(lines[4].split(), ["bob", "1001", "service", "standard", "-"])
        self.assertEqual(lines[-1], "4 accounts")

    def test_listing_without_privileged_accounts(self):
        code, out, _err = run_main(["perms", "--search", "bob"])
        self.assertEqual(code, 0)
        self.assertEqual(out.splitlines()[-1], "1 account")
        self.assertIn("bob", out)
        self.assertIn("standard", out)

    def test_empty_selection_keeps_header(self):
        code, out, _err = run_main(["perms", "--type", "unknown"])
        self.assertEqual(code, 0)
        self.assertEqual(out.splitlines()[0].split()[0], "NAME")
        self.assertEqual(out.splitlines()[-1], "0 accounts")

    def test_detail_shows_level_and_groups(self):
        code, out, err = run_main(["perms", "alice"])
        self.assertEqual(code, 0)
        self.assertEqual(err, "")
        self.assertRegex(out, r"Level:\s+sudo")
        self.assertRegex(out, r"Privileged groups:\s+sudo")
        self.assertRegex(out, r"Type:\s+normal")

    def test_detail_without_privileges_uses_dash(self):
        code, out, _err = run_main(["perms", "bob"])
        self.assertEqual(code, 0)
        self.assertRegex(out, r"Level:\s+standard")
        self.assertRegex(out, r"Privileged groups:\s+-")

    def test_unknown_account(self):
        code, out, err = run_main(["perms", "nope"])
        self.assertEqual(code, 1)
        self.assertEqual(out, "")
        self.assertIn("account not found: nope", err)

    def test_json_listing(self):
        code, out, _err = run_main(["perms", "--json"])
        self.assertEqual(code, 0)
        payload = json.loads(out)
        self.assertEqual(payload["schema_version"], 1)
        self.assertEqual(payload["count"], 4)
        self.assertEqual(
            payload["permissions"][0],
            {
                "name": "root",
                "uid": 0,
                "type": "system",
                "level": "root",
                "groups": [],
            },
        )
        self.assertEqual(payload["permissions"][1]["groups"], ["sudo"])

    def test_json_detail(self):
        code, out, _err = run_main(["perms", "carol", "--json"])
        self.assertEqual(code, 0)
        payload = json.loads(out)
        self.assertEqual(payload["schema_version"], 1)
        self.assertEqual(payload["account"]["name"], "carol")
        self.assertEqual(
            payload["permission"], {"level": "privileged", "groups": ["docker"]}
        )

    def test_csv_listing(self):
        code, out, _err = run_main(["perms", "--csv"])
        self.assertEqual(code, 0)
        rows = list(csv.reader(io.StringIO(out)))
        self.assertEqual(rows[0], ["name", "uid", "type", "level", "groups"])
        self.assertEqual(
            [row[0] for row in rows[1:]], ["root", "alice", "carol", "bob"]
        )
        self.assertEqual(rows[2][4], "sudo")
        self.assertEqual(rows[4][4], "")

    def test_csv_detail(self):
        code, out, _err = run_main(["perms", "carol", "--csv"])
        self.assertEqual(code, 0)
        rows = list(csv.reader(io.StringIO(out)))
        self.assertEqual(rows[0], ["name", "uid", "type", "level", "groups"])
        self.assertEqual(
            rows[1], ["carol", "1002", "normal", "privileged", "docker"]
        )

    def test_machine_formats_have_no_ansi(self):
        for flag in ("--json", "--csv"):
            with self.subTest(flag=flag):
                _code, out, _err = run_main(["perms", flag])
                self.assertNotIn("\x1b", out)

    def test_type_filter(self):
        code, out, _err = run_main(["perms", "--type", "normal"])
        self.assertEqual(code, 0)
        self.assertIn("alice", out)
        self.assertIn("carol", out)
        self.assertNotIn("bob", out)
        self.assertNotIn("root", out)

    def test_search_filter(self):
        code, out, _err = run_main(["perms", "--search", "ali"])
        self.assertEqual(code, 0)
        self.assertIn("alice", out)
        self.assertNotIn("carol", out)

    def test_detail_ignores_filters(self):
        code, out, _err = run_main(["perms", "bob", "--type", "normal"])
        self.assertEqual(code, 0)
        self.assertIn("bob", out)
        self.assertRegex(out, r"Level:\s+standard")


if __name__ == "__main__":
    unittest.main()
