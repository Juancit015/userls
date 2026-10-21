import unittest
from types import SimpleNamespace
from unittest import mock

from userls import (
    Diagnostics,
    SystemDataSource,
    parse_group_records,
    parse_passwd_records,
    parse_who,
)


class ParserTests(unittest.TestCase):
    def test_parse_passwd_records(self):
        diagnostics = Diagnostics()
        text = (
            "root:x:0:0:root:/root:/bin/bash\n"
            "bad:x:1:2:three\n"
            "weird:x:abc:0:x:/home:/bin/sh\n"
            "+nis:x:0:0::/:/bin/sh\n"
        )
        records = parse_passwd_records(text, diagnostics)
        self.assertEqual(records, [("root", 0, 0, "root", "/root", "/bin/bash")])
        self.assertEqual(len(diagnostics.messages), 2)

    def test_parse_group_records(self):
        diagnostics = Diagnostics()
        text = "sudo:x:27:juan,alice\nbad:x:1\nempty:x:42:\n"
        records = parse_group_records(text, diagnostics)
        self.assertEqual(
            records,
            [("sudo", 27, ("juan", "alice")), ("empty", 42, ())],
        )
        self.assertEqual(len(diagnostics.messages), 1)

    def test_parse_who_common_and_iso_formats(self):
        diagnostics = Diagnostics()
        text = (
            "juan     seat0        Oct 21 08:27 (:0)\n"
            "alice    pts/1        2026-10-21 09:00 (10.0.0.5)\n"
        )
        sessions = parse_who(text, diagnostics)
        self.assertEqual(len(sessions), 2)
        self.assertEqual(sessions[0].login_time, "Oct 21 08:27")
        self.assertEqual(sessions[0].origin, ":0")
        self.assertEqual(sessions[1].login_time, "2026-10-21 09:00")
        self.assertEqual(sessions[1].origin, "10.0.0.5")
        self.assertEqual(diagnostics.messages, [])

    def test_parse_who_keeps_unmatched_lines(self):
        diagnostics = Diagnostics()
        text = "juan seat0 08:27 (:0) extra\nlonely\n"
        sessions = parse_who(text, diagnostics)
        self.assertEqual(len(sessions), 1)
        self.assertEqual(sessions[0].login_time, "08:27 (:0) extra")
        self.assertEqual(len(diagnostics.messages), 2)


class SystemDataSourceTests(unittest.TestCase):
    def source(self):
        return SystemDataSource(
            login_defs_path="/nonexistent/login.defs",
            diagnostics=Diagnostics(),
        )

    def test_native_enumeration_falls_back_to_getent(self):
        source = self.source()
        passwd = "root:x:0:0:root:/root:/bin/bash\n"
        with mock.patch("userls.pwd.getpwall", side_effect=OSError("boom")):
            with mock.patch("userls.grp.getgrall", return_value=[]):
                with mock.patch("userls.run_command", return_value=passwd):
                    accounts = source.accounts()
        self.assertEqual(len(accounts), 1)
        self.assertEqual(accounts[0].name, "root")
        self.assertEqual(accounts[0].primary_group, "0")
        self.assertTrue(
            any("falling back" in message for message in source.diagnostics.messages)
        )

    def test_primary_group_is_resolved_by_gid(self):
        source = self.source()
        user = SimpleNamespace(
            pw_name="alice",
            pw_uid=1000,
            pw_gid=4242,
            pw_gecos="Alice",
            pw_dir="/home/alice",
            pw_shell="/bin/bash",
        )
        group = SimpleNamespace(gr_name="staff", gr_gid=4242, gr_mem=[])
        with mock.patch("userls.pwd.getpwall", return_value=[user]):
            with mock.patch("userls.grp.getgrall", return_value=[group]):
                accounts = source.accounts()
        self.assertEqual(accounts[0].primary_group, "staff")
        self.assertEqual(accounts[0].type, "normal")

    def test_unresolved_gid_falls_back_to_number(self):
        source = self.source()
        user = SimpleNamespace(
            pw_name="alice",
            pw_uid=1000,
            pw_gid=4242,
            pw_gecos="Alice",
            pw_dir="/home/alice",
            pw_shell="/bin/bash",
        )
        with mock.patch("userls.pwd.getpwall", return_value=[user]):
            with mock.patch("userls.grp.getgrall", return_value=[]):
                accounts = source.accounts()
        self.assertEqual(accounts[0].primary_group, "4242")

    def test_native_group_enumeration_falls_back_to_getent(self):
        source = self.source()
        output = "sudo:x:27:juan\n"
        with mock.patch("userls.grp.getgrall", side_effect=OSError("boom")):
            with mock.patch("userls.run_command", return_value=output):
                groups = source.groups()
        self.assertEqual(groups[0].name, "sudo")
        self.assertEqual(groups[0].members, ("juan",))
        self.assertTrue(
            any("falling back" in message for message in source.diagnostics.messages)
        )


if __name__ == "__main__":
    unittest.main()
