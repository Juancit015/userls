import argparse
import csv
import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from userls import (
    Account,
    Group,
    LoginDefs,
    Session,
    UserlsError,
    accounts_payload,
    color_enabled,
    display_width,
    groups_payload,
    pad,
    render_json,
    render_table,
    sessions_payload,
    type_colorizer,
    write_csv,
    write_csv_file,
)


class TableTests(unittest.TestCase):
    def test_display_width(self):
        self.assertEqual(display_width("juan"), 4)
        self.assertEqual(display_width("josé"), 4)
        self.assertEqual(display_width("日本"), 4)
        self.assertEqual(display_width("e\u0301"), 1)

    def test_pad(self):
        self.assertEqual(pad("José", 6), "José  ")
        self.assertEqual(pad("日本", 6), "日本  ")
        self.assertEqual(pad("longer", 3), "longer")

    def test_render_table_aligns_wide_glyphs(self):
        table = render_table(
            ["NAME", "UID"],
            [["José", "1"], ["日本", "2"]],
            "2 accounts",
        )
        lines = table.splitlines()
        self.assertEqual(lines[0], "NAME  UID")
        first = display_width(lines[1][: lines[1].index("1")])
        second = display_width(lines[2][: lines[2].index("2")])
        self.assertEqual(first, second)
        self.assertEqual(lines[-1], "2 accounts")

    def test_render_table_without_rows(self):
        table = render_table(["NAME", "UID"], [], "0 accounts")
        self.assertIn("NAME", table)
        self.assertIn("0 accounts", table)

    def test_colorizer_only_colors_the_type_column(self):
        colorize = type_colorizer(True)
        colored = colorize(0, 6, "normal  ")
        self.assertIn("\033[32m", colored)
        self.assertTrue(colored.endswith("\033[0m"))
        self.assertEqual(colorize(0, 0, "juan"), "juan")
        self.assertEqual(colorize(0, 6, "other "), "other ")

    def test_disabled_colorizer_is_identity(self):
        colorize = type_colorizer(False)
        self.assertEqual(colorize(0, 6, "normal  "), "normal  ")


class ColorPolicyTests(unittest.TestCase):
    class Tty(io.StringIO):
        def isatty(self):
            return True

    def args(self, **overrides):
        values = {"json": False, "csv": False, "no_color": False}
        values.update(overrides)
        return argparse.Namespace(**values)

    def test_color_on_a_tty(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertTrue(color_enabled(self.args(), self.Tty()))

    def test_machine_formats_disable_color(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertFalse(color_enabled(self.args(json=True), self.Tty()))
            self.assertFalse(color_enabled(self.args(csv=True), self.Tty()))

    def test_no_color_flag_and_environment(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertFalse(color_enabled(self.args(no_color=True), self.Tty()))
        with mock.patch.dict(os.environ, {"NO_COLOR": "1"}, clear=True):
            self.assertFalse(color_enabled(self.args(), self.Tty()))


class SerializationTests(unittest.TestCase):
    def setUp(self):
        self.account = Account(
            "juan", 1000, 1000, "Juan", "/home/juan", "/usr/bin/fish", "juan", "normal"
        )
        self.group = Group("sudo", 27, ("juan", "alice"))
        self.session = Session(
            "juan", "seat0", "Oct 21 08:27", ":0", "juan seat0 Oct 21 08:27 (:0)"
        )

    def test_json_payloads(self):
        accounts = accounts_payload([self.account])
        self.assertEqual(accounts["schema_version"], 1)
        self.assertEqual(accounts["count"], 1)
        self.assertEqual(accounts["accounts"][0]["primary_group"], "juan")

        groups = groups_payload([self.group])
        self.assertEqual(groups["groups"][0]["members"], ["juan", "alice"])

        sessions = sessions_payload([self.session])
        self.assertEqual(sessions["sessions"][0]["tty"], "seat0")

        self.assertIsInstance(render_json(accounts), str)

    def test_csv_quoting_round_trip(self):
        stream = io.StringIO()
        rows = [["a,b", 'he said "hi"', "line\nbreak"]]
        write_csv(stream, ["one", "two", "three"], rows)
        parsed = list(csv.reader(io.StringIO(stream.getvalue())))
        self.assertEqual(parsed, [["one", "two", "three"], *rows])

    def test_write_csv_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "accounts.csv"
            write_csv_file(str(path), ["name"], [["juan"]])
            self.assertEqual(path.read_text(encoding="utf-8"), "name\njuan\n")

            with self.assertRaises(UserlsError):
                write_csv_file(str(path), ["name"], [["alice"]])

            write_csv_file(str(path), ["name"], [["alice"]], force=True)
            self.assertEqual(path.read_text(encoding="utf-8"), "name\nalice\n")

    def test_unwritable_target(self):
        with self.assertRaises(UserlsError):
            write_csv_file("/nonexistent-dir-userls/x.csv", ["name"], [["juan"]])

    def test_unwritable_directory(self):
        if os.geteuid() == 0:
            self.skipTest("root can write to a read-only directory")
        with tempfile.TemporaryDirectory() as tmp:
            os.chmod(tmp, 0o500)
            try:
                with self.assertRaises(UserlsError):
                    write_csv_file(str(Path(tmp) / "x.csv"), ["name"], [["juan"]])
            finally:
                os.chmod(tmp, 0o700)

    def test_info_payload_shape(self):
        payload = {
            "schema_version": 1,
            "account": {"name": self.account.name},
            "system_uid_range": LoginDefs().system_range_label(),
        }
        self.assertEqual(render_json(payload), render_json(payload))
        self.assertEqual(payload["system_uid_range"], "100-999")


if __name__ == "__main__":
    unittest.main()
