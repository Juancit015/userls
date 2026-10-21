import tempfile
import unittest
from pathlib import Path

from userls import Diagnostics, LoginDefs, load_login_defs


class LoginDefsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "login.defs"

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, text):
        self.path.write_text(text, encoding="utf-8")

    def test_defaults_when_missing(self):
        diagnostics = Diagnostics()
        result = load_login_defs(str(self.path), diagnostics)
        self.assertEqual(result, LoginDefs())
        self.assertTrue(diagnostics.messages)

    def test_missing_system_keys_use_defaults(self):
        self.write("UID_MIN 5000\nUID_MAX 9000\n")
        result = load_login_defs(str(self.path))
        self.assertEqual((result.uid_min, result.uid_max), (5000, 9000))
        self.assertEqual((result.sys_uid_min, result.sys_uid_max), (100, 999))

    def test_valid_values_and_comments(self):
        self.write(
            "# a comment\n"
            "UID_MIN 2000\n"
            "UID_MAX 8000   # trailing comment\n"
            "SYS_UID_MIN 200\n"
            "SYS_UID_MAX 998\n"
        )
        result = load_login_defs(str(self.path))
        self.assertEqual(result, LoginDefs(2000, 8000, 200, 998))

    def test_malformed_value_keeps_default(self):
        self.write("UID_MIN nope\n")
        diagnostics = Diagnostics()
        result = load_login_defs(str(self.path), diagnostics)
        self.assertEqual(result.uid_min, 1000)
        self.assertTrue(any("invalid UID_MIN" in message for message in diagnostics.messages))

    def test_out_of_range_value_keeps_default(self):
        self.write("UID_MAX -5\n")
        diagnostics = Diagnostics()
        result = load_login_defs(str(self.path), diagnostics)
        self.assertEqual(result.uid_max, 60000)
        self.assertTrue(any("out of range" in message for message in diagnostics.messages))

    def test_inverted_ranges_fall_back(self):
        self.write(
            "UID_MIN 9000\nUID_MAX 1000\nSYS_UID_MIN 900\nSYS_UID_MAX 100\n"
        )
        diagnostics = Diagnostics()
        result = load_login_defs(str(self.path), diagnostics)
        self.assertEqual(result, LoginDefs())
        self.assertEqual(len(diagnostics.messages), 2)


if __name__ == "__main__":
    unittest.main()
