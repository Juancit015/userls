import contextlib
import io
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

import userls

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "userls.py"


def run_cli(*args):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )


class CliTests(unittest.TestCase):
    def test_help_lists_options_and_commands(self):
        result = run_cli("--help")
        self.assertEqual(result.returncode, 0)
        for token in (
            "--type",
            "--search",
            "--json",
            "--csv",
            "--no-color",
            "--version",
            "info",
            "groups",
            "sessions",
            "export",
        ):
            self.assertIn(token, result.stdout)

    def test_version(self):
        result = run_cli("--version")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), f"userls {userls.__version__}")

    def test_unknown_option_is_usage_error(self):
        result = run_cli("--does-not-exist")
        self.assertEqual(result.returncode, 2)
        self.assertIn("usage:", result.stderr.lower())

    def test_unknown_subcommand_is_usage_error(self):
        result = run_cli("frobnicate")
        self.assertEqual(result.returncode, 2)

    def test_shared_flags_parse_before_and_after_subcommand(self):
        parser = userls.build_parser()
        before = parser.parse_args(["--json", "groups", "juan"])
        after = parser.parse_args(["groups", "juan", "--json"])
        self.assertTrue(before.json)
        self.assertTrue(after.json)

    def test_error_formatting(self):
        stderr = io.StringIO()
        stdout = io.StringIO()
        with mock.patch.object(
            userls.SystemDataSource,
            "sessions",
            side_effect=userls.UserlsError("who: boom"),
        ):
            with contextlib.redirect_stdout(stdout):
                with contextlib.redirect_stderr(stderr):
                    code = userls.main(["sessions"])
        self.assertEqual(code, 1)
        self.assertEqual(stdout.getvalue(), "")
        self.assertEqual(stderr.getvalue(), "userls: who: boom\n")


if __name__ == "__main__":
    unittest.main()
