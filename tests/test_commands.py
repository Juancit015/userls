import contextlib
import io
import json
import unittest
from unittest import mock

import userls
from userls import Account, Group, LoginDefs, Session, UserlsError

ACCOUNTS = [
    Account("root", 0, 0, "root", "/root", "/bin/bash", "root", "system"),
    Account(
        "daemon",
        1,
        1,
        "daemon",
        "/usr/sbin",
        "/usr/sbin/nologin",
        "daemon",
        "service",
    ),
    Account(
        "juan",
        1000,
        1000,
        "juan,,,",
        "/home/juan",
        "/usr/bin/fish",
        "juan",
        "normal",
    ),
    Account(
        "nobody",
        65534,
        65534,
        "nobody",
        "/nonexistent",
        "/usr/sbin/nologin",
        "nogroup",
        "service",
    ),
    Account("weird", 70000, 70000, "weird", "/home/weird", "/bin/bash", "weird", "unknown"),
]

GROUPS = [
    Group("root", 0, ()),
    Group("daemon", 1, ()),
    Group("sudo", 27, ("juan",)),
    Group("audio", 29, ("juan", "pulse")),
    Group("juan", 1000, ()),
]

SESSIONS = [
    Session("juan", "seat0", "Oct 21 08:27", ":0", "juan seat0 Oct 21 08:27 (:0)")
]


class FakeSource:
    def __init__(self, *args, **kwargs):
        self.ranges = LoginDefs()

    def accounts(self):
        return list(ACCOUNTS)

    def groups(self):
        return list(GROUPS)

    def sessions(self):
        return list(SESSIONS)


def run_main(argv):
    stdout = io.StringIO()
    stderr = io.StringIO()
    with mock.patch("userls.SystemDataSource", FakeSource):
        with contextlib.redirect_stdout(stdout):
            with contextlib.redirect_stderr(stderr):
                code = userls.main(argv)
    return code, stdout.getvalue(), stderr.getvalue()


class CommandTests(unittest.TestCase):
    def test_default_listing(self):
        code, out, err = run_main([])
        self.assertEqual(code, 0)
        self.assertEqual(err, "")
        self.assertIn("NAME", out)
        self.assertIn("root", out)
        self.assertIn("nobody", out)
        self.assertIn("5 accounts", out)

    def test_listing_types(self):
        code, out, _ = run_main(["--json"])
        self.assertEqual(code, 0)
        types = {account["name"]: account["type"] for account in json.loads(out)["accounts"]}
        self.assertEqual(types["root"], "system")
        self.assertEqual(types["juan"], "normal")
        self.assertEqual(types["nobody"], "service")

    def test_type_filter(self):
        expected = {
            "normal": ["juan"],
            "service": ["daemon", "nobody"],
            "system": ["root"],
            "unknown": ["weird"],
        }
        for account_type, names in expected.items():
            code, out, _ = run_main(["--type", account_type, "--json"])
            self.assertEqual(code, 0)
            payload = json.loads(out)
            self.assertEqual(
                sorted(account["name"] for account in payload["accounts"]), names
            )

        _, unfiltered, _ = run_main(["--json"])
        _, everything, _ = run_main(["--type", "all", "--json"])
        self.assertEqual(
            json.loads(unfiltered)["count"], json.loads(everything)["count"]
        )

    def test_search_by_name_and_uid(self):
        _, by_name, _ = run_main(["--search", "jua", "--json"])
        self.assertEqual(json.loads(by_name)["count"], 1)
        _, by_uid, _ = run_main(["--search", "1000", "--json"])
        self.assertEqual(json.loads(by_uid)["accounts"][0]["name"], "juan")
        _, empty, _ = run_main(["--search", "zzz", "--json"])
        self.assertEqual(json.loads(empty)["count"], 0)

    def test_info_by_name_and_uid(self):
        for term in ("juan", "1000"):
            code, out, _ = run_main(["info", term])
            self.assertEqual(code, 0)
            self.assertIn("Primary group:", out)
            self.assertIn("/usr/bin/fish", out)
            self.assertIn("100-999", out)

    def test_info_unknown_account(self):
        code, out, err = run_main(["info", "nope"])
        self.assertEqual(code, 1)
        self.assertEqual(out, "")
        self.assertIn("userls: account not found: nope", err)

    def test_groups_listing(self):
        code, out, _ = run_main(["groups"])
        self.assertEqual(code, 0)
        self.assertIn("5 groups", out)
        self.assertIn("sudo", out)
        self.assertRegex(out, r"root\s+0\s+-")

    def test_groups_for_account(self):
        code, out, _ = run_main(["groups", "juan"])
        self.assertEqual(code, 0)
        self.assertIn("3 groups for juan", out)
        self.assertIn("sudo", out)
        self.assertIn("audio", out)

    def test_groups_unknown_account(self):
        code, out, err = run_main(["groups", "nope"])
        self.assertEqual(code, 1)
        self.assertEqual(out, "")
        self.assertIn("userls: account not found: nope", err)

    def test_groups_json(self):
        code, out, _ = run_main(["groups", "juan", "--json"])
        self.assertEqual(code, 0)
        payload = json.loads(out)
        self.assertEqual(payload["count"], 3)
        self.assertEqual(payload["account"], "juan")
        self.assertEqual([group["gid"] for group in payload["groups"]], [27, 29, 1000])

    def test_sessions_listing(self):
        code, out, _ = run_main(["sessions"])
        self.assertEqual(code, 0)
        self.assertIn("juan", out)
        self.assertIn("seat0", out)
        self.assertIn("1 session", out)

    def test_sessions_json(self):
        code, out, _ = run_main(["sessions", "--json"])
        payload = json.loads(out)
        self.assertEqual(code, 0)
        self.assertEqual(payload["sessions"][0]["origin"], ":0")

    def test_empty_sessions_exit_zero(self):
        with mock.patch.object(FakeSource, "sessions", return_value=[]):
            code, out, err = run_main(["sessions"])
        self.assertEqual((code, err), (0, ""))
        self.assertIn("USER", out)
        self.assertIn("0 sessions", out)

    def test_multiple_sessions(self):
        extra = Session("alice", "pts/1", "Oct 21 09:00", "10.0.0.5", "raw")
        with mock.patch.object(FakeSource, "sessions", return_value=SESSIONS + [extra]):
            code, out, _ = run_main(["sessions"])
        self.assertEqual(code, 0)
        self.assertIn("2 sessions", out)
        self.assertIn("alice", out)

    def test_source_failure_exits_one(self):
        with mock.patch.object(
            FakeSource, "sessions", side_effect=UserlsError("who: boom")
        ):
            code, out, err = run_main(["sessions"])
        self.assertEqual(code, 1)
        self.assertEqual(out, "")
        self.assertIn("userls: who: boom", err)


if __name__ == "__main__":
    unittest.main()
