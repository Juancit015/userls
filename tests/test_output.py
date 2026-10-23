import argparse
import csv
import io
import os
import tempfile
import unittest
from html.parser import HTMLParser
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
    export_format,
    full_name_for_html,
    groups_payload,
    html_column_widths,
    pad,
    render_html,
    render_json,
    render_table,
    sessions_payload,
    type_colorizer,
    write_csv,
    write_csv_file,
    write_html_file,
)


class HtmlExportParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.table_count = 0
        self.rows = []
        self.external_tags = []
        self._row = None
        self._cell = None
        self._cell_class = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "table":
            self.table_count += 1
        if tag in {"script", "link", "img"}:
            self.external_tags.append(tag)
        if tag == "tr":
            self._row = []
        elif tag in {"th", "td"}:
            self._cell = []
            self._cell_class = attrs.get("class")

    def handle_data(self, data):
        if self._cell is not None:
            self._cell.append(data)

    def handle_endtag(self, tag):
        if tag in {"th", "td"} and self._cell is not None:
            if self._row is None:
                self._row = []
            self._row.append(
                {
                    "tag": tag,
                    "class": self._cell_class,
                    "text": "".join(self._cell),
                }
            )
            self._cell = None
            self._cell_class = None
        elif tag == "tr" and self._row is not None:
            self.rows.append(self._row)
            self._row = None


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


class HtmlTests(unittest.TestCase):
    def test_full_name_for_html(self):
        self.assertEqual(full_name_for_html("juan,,,"), "juan")
        self.assertEqual(full_name_for_html(""), "NA")
        self.assertEqual(full_name_for_html("   "), "NA")
        self.assertEqual(
            full_name_for_html("John Doe,Room 1,555-0100,"), "John Doe"
        )
        self.assertEqual(full_name_for_html("  Juan David  ,Room 1"), "Juan David")

    def test_html_column_widths(self):
        widths = html_column_widths(
            ["NAME", "UID", "TEXT"],
            [["José", "1", "日本"], ["e\u0301", "22", "x"]],
        )
        self.assertEqual(widths, [8, 7, 8])
        self.assertEqual(
            html_column_widths(["NAME", "UID"], []),
            [8, 7],
        )

    def test_render_html_structure_and_styles(self):
        accounts = [
            Account("root", 0, 0, "root", "/root", "/bin/bash", "root", "system"),
            Account(
                "daemon",
                1,
                1,
                "Daemon User",
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
                "weird",
                70000,
                70000,
                "",
                "/home/weird",
                "/bin/bash",
                "nogroup",
                "unknown",
            ),
        ]
        document = render_html(accounts)
        self.assertTrue(document.startswith("<!DOCTYPE html>"))
        self.assertIn('<html lang="en">', document)
        self.assertIn('<meta charset="utf-8">', document)

        parser = HtmlExportParser()
        parser.feed(document)
        self.assertEqual(parser.table_count, 1)
        self.assertEqual(parser.external_tags, [])
        self.assertEqual(len(parser.rows), 5)
        self.assertEqual(
            [cell["text"] for cell in parser.rows[0]],
            [
                "NAME",
                "UID",
                "GID",
                "PRIMARY GROUP",
                "FULL NAME",
                "HOME",
                "SHELL",
                "TYPE",
            ],
        )
        self.assertTrue(all(cell["tag"] == "th" for cell in parser.rows[0]))
        for row in parser.rows[1:]:
            self.assertEqual(len(row), 8)
            self.assertTrue(all(cell["tag"] == "td" for cell in row))
            self.assertTrue(all(cell["class"] is None for cell in row[:7]))
            self.assertRegex(
                row[7]["class"],
                r"^type-(system|service|normal|unknown)$",
            )

        self.assertEqual(document.count('<col style="width: '), 8)
        self.assertIn("tbody { font-weight: 700; }", document)
        self.assertIn("background: #0f172a", document)
        for color in ("#f97316", "#1e3a8a", "#15803d", "#4b5563"):
            self.assertIn(color, document)
        self.assertIn("white-space: nowrap", document)
        self.assertIn("overflow-x: auto", document)
        self.assertIn("table-layout: auto", document)
        self.assertNotIn("<script", document)
        self.assertNotIn("<link", document)
        self.assertNotIn("<img", document)
        self.assertNotIn("@import", document)
        self.assertNotIn("url(", document)

    def test_render_html_escapes_values(self):
        account = Account(
            "n<&'\"",
            1,
            2,
            'A&B"<\'',
            "/home/a&b",
            "/bin/<sh>",
            "g<&",
            "normal",
        )
        document = render_html([account])
        for token in ("&lt;", "&amp;", "&quot;", "&#x27;"):
            self.assertIn(token, document)

        parser = HtmlExportParser()
        parser.feed(document)
        body = parser.rows[1]
        self.assertEqual(body[0]["text"], "n<&'\"")
        self.assertEqual(body[3]["text"], "g<&")
        self.assertEqual(body[4]["text"], "A&B\"<'")
        self.assertEqual(body[5]["text"], "/home/a&b")
        self.assertEqual(body[6]["text"], "/bin/<sh>")

    def test_render_html_full_name_and_na(self):
        accounts = [
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
                "carlitos",
                1001,
                1001,
                "",
                "/home/carlitos",
                "/usr/bin/bash",
                "carlitos",
                "normal",
            ),
        ]
        parser = HtmlExportParser()
        parser.feed(render_html(accounts))
        self.assertEqual(parser.rows[1][3]["text"], "juan")
        self.assertEqual(parser.rows[1][4]["text"], "juan")
        self.assertEqual(parser.rows[2][3]["text"], "carlitos")
        self.assertEqual(parser.rows[2][4]["text"], "NA")

    def test_render_html_empty_view(self):
        parser = HtmlExportParser()
        parser.feed(render_html([]))
        self.assertEqual(len(parser.rows), 1)
        self.assertEqual(len(parser.rows[0]), 8)
        self.assertTrue(all(cell["tag"] == "th" for cell in parser.rows[0]))

    def test_export_format_by_extension(self):
        self.assertEqual(export_format("accounts.html"), "html")
        self.assertEqual(export_format("accounts.HTM"), "html")
        self.assertEqual(export_format("accounts.htm"), "html")
        self.assertEqual(export_format("accounts.csv"), "csv")
        self.assertEqual(export_format("accounts.CSV"), "csv")
        self.assertEqual(export_format("accounts.txt"), "csv")
        self.assertEqual(export_format("accounts"), "csv")

    def test_write_html_file_and_force(self):
        account = Account(
            "juan",
            1000,
            1000,
            "juan,,,",
            "/home/juan",
            "/usr/bin/fish",
            "juan",
            "normal",
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "accounts.html"
            write_html_file(str(path), [account])
            document = path.read_text(encoding="utf-8")
            self.assertTrue(document.startswith("<!DOCTYPE html>"))
            self.assertIn(">juan<", document)
            self.assertIn(">FULL NAME<", document)

            with self.assertRaises(UserlsError) as raised:
                write_html_file(str(path), [account])
            self.assertIn("use --force", str(raised.exception))

            replacement = Account(
                "alice",
                1001,
                1001,
                "",
                "/home/alice",
                "/bin/bash",
                "alice",
                "normal",
            )
            write_html_file(str(path), [replacement], force=True)
            self.assertIn(">alice<", path.read_text(encoding="utf-8"))
            self.assertNotIn(">juan<", path.read_text(encoding="utf-8"))

    def test_write_html_file_unwritable_target(self):
        with self.assertRaises(UserlsError):
            write_html_file("/nonexistent-dir-userls/x.html", [])


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
