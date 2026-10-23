"""Shell completion tests.

Syntax and candidate behavior for the hand-written completions in
``completions/``.  Each shell section is skipped when the shell is not
installed.  The dynamic completions call ``userls`` from PATH, so the tests
run against a shim that points at the repository CLI instead of whatever
version happens to be installed.
"""

from __future__ import annotations

import contextlib
import os
import pwd
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "userls.py"
FISH_COMPLETION = ROOT / "completions" / "userls.fish"
BASH_COMPLETION = ROOT / "completions" / "userls.bash"
ZSH_COMPLETION = ROOT / "completions" / "_userls"

# Runs the repository completion file through a real zsh completion setup
# (compinit + autoload of the #compdef file) with the match-producing layer
# stubbed so candidates can be captured from a plain, non-interactive shell.
ZSH_HARNESS = r"""
fpath=("$USERLS_FPATH" $fpath)
autoload -Uz compinit && compinit -u -d "$USERLS_ZDUMP" || { print -r -- COMPINIT-FAILED; exit 2 }
_describe() { local -a items; items=(${(P)${argv[-1]}}); print -r -- "${(j:|:)items}" }
_arguments() { printf '%s\n' "$@" }
words=(${=1}); CURRENT=$2
_userls
"""


@contextlib.contextmanager
def userls_path(body=None):
    """A PATH whose first ``userls`` is a shim.

    Default shim: the repository CLI.  Pass ``body`` for a deliberately
    broken command.
    """
    with tempfile.TemporaryDirectory() as tmp:
        shim = Path(tmp) / "userls"
        if body is None:
            body = f'#!/bin/sh\nexec "{sys.executable}" "{SCRIPT}" "$@"\n'
        shim.write_text(body)
        shim.chmod(0o755)
        env = os.environ.copy()
        env["PATH"] = tmp + os.pathsep + env.get("PATH", "")
        yield env


def run(cmd, env=None):
    return subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT, env=env)


def parse_candidates(stdout):
    """Turn ``token<TAB>description`` lines into a mapping."""
    candidates = {}
    for line in stdout.splitlines():
        token, _, description = line.partition("\t")
        if token:
            candidates[token] = description
    return candidates


@unittest.skipUnless(shutil.which("fish"), "fish is not installed")
class FishCompletionTests(unittest.TestCase):
    def complete(self, line, env):
        script = (
            f"source '{FISH_COMPLETION}'; "
            f"set fish_complete_path '{FISH_COMPLETION.parent}'; "
            f"complete -C'{line}'"
        )
        result = run([shutil.which("fish"), "-c", script], env=env)
        self.assertEqual(result.returncode, 0, result.stderr)
        return parse_candidates(result.stdout)

    def test_syntax(self):
        result = run([shutil.which("fish"), "--no-execute", str(FISH_COMPLETION)])
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_subcommands_have_descriptions(self):
        with userls_path() as env:
            candidates = self.complete("userls ", env)
        self.assertEqual(
            set(candidates), {"info", "groups", "perms", "sessions"}
        )
        for token, description in candidates.items():
            self.assertTrue(description, f"{token} has no description")

    def test_option_candidates_before_and_after_subcommand(self):
        expected = (
            "--json",
            "--no-color",
            "--type",
            "--search",
            "--version",
            "--help",
        )
        with userls_path() as env:
            for line in ("userls --", "userls info --", "userls info --json --"):
                candidates = self.complete(line, env)
                self.assertEqual(set(expected) - set(candidates), set(), line)
                for token in expected:
                    self.assertTrue(candidates[token], f"{token} has no description")

    def test_options_win_over_accounts(self):
        with userls_path() as env:
            candidates = self.complete("userls info -", env)
            self.assertIn("-h", candidates)
        self.assertTrue(all(token.startswith("-") for token in candidates))
        self.assertNotIn("root", candidates)

    def test_type_values_have_descriptions(self):
        with userls_path() as env:
            candidates = self.complete("userls --type ", env)
        self.assertEqual(
            set(candidates), {"all", "normal", "service", "system", "unknown"}
        )
        for token, description in candidates.items():
            self.assertTrue(description, f"{token} has no description")

    def test_type_option_keeps_its_own_description(self):
        with userls_path() as env:
            candidates = self.complete("userls --ty", env)
        self.assertEqual(candidates.get("--type"), "filter accounts by type")

    def test_accounts_are_described_with_uid_and_type(self):
        user = pwd.getpwuid(os.getuid()).pw_name
        with userls_path() as env:
            for subcommand in ("info", "groups", "perms"):
                candidates = self.complete(f"userls {subcommand} ", env)
                self.assertIn(user, candidates, subcommand)
                self.assertRegex(
                    candidates[user],
                    r"^uid \d+ · (normal|service|system|unknown)$",
                )
                self.assertIn("root", candidates, subcommand)
                self.assertNotIn("name", candidates, subcommand)  # no header row

    def test_silent_when_userls_fails(self):
        with userls_path("#!/bin/sh\nexit 1\n") as env:
            script = (
                f"source '{FISH_COMPLETION}'; "
                f"set fish_complete_path '{FISH_COMPLETION.parent}'; "
                "complete -C'userls info '"
            )
            result = run([shutil.which("fish"), "-c", script], env=env)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")


@unittest.skipUnless(shutil.which("bash"), "bash is not installed")
class BashCompletionTests(unittest.TestCase):
    def complete(self, words, cword, env):
        array = " ".join(f"'{word}'" for word in words)
        script = (
            f"source '{BASH_COMPLETION}'; "
            f"COMP_WORDS=({array}); COMP_CWORD={cword}; _userls; "
            'printf "%s\\n" "${COMPREPLY[@]}"'
        )
        result = run([shutil.which("bash"), "-c", script], env=env)
        self.assertEqual(result.returncode, 0, result.stderr)
        return [line for line in result.stdout.splitlines() if line]

    def test_syntax(self):
        result = run([shutil.which("bash"), "-n", str(BASH_COMPLETION)])
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_subcommands(self):
        with userls_path() as env:
            candidates = self.complete(["userls", ""], 1, env)
        self.assertEqual(candidates, ["info", "groups", "perms", "sessions"])

    def test_option_candidates_before_and_after_subcommand(self):
        expected = {
            "--json",
            "--no-color",
            "--type",
            "--search",
            "--version",
            "--help",
        }
        with userls_path() as env:
            for words, cword in (
                (["userls", "-"], 1),
                (["userls", "info", "--"], 2),
                (["userls", "info", "--json", "--"], 3),
            ):
                candidates = set(self.complete(words, cword, env))
                self.assertEqual(expected - candidates, set(), " ".join(words))
            self.assertIn("-h", self.complete(["userls", "-"], 1, env))

    def test_options_win_over_accounts(self):
        with userls_path() as env:
            candidates = self.complete(["userls", "info", "-"], 2, env)
        self.assertTrue(candidates)
        self.assertTrue(all(token.startswith("-") for token in candidates))
        self.assertNotIn("root", candidates)

    def test_type_values(self):
        with userls_path() as env:
            candidates = self.complete(["userls", "--type", ""], 2, env)
        self.assertEqual(
            set(candidates), {"all", "normal", "service", "system", "unknown"}
        )

    def test_accounts_without_header(self):
        user = pwd.getpwuid(os.getuid()).pw_name
        with userls_path() as env:
            for subcommand in ("info", "groups", "perms"):
                candidates = self.complete(["userls", subcommand, ""], 2, env)
                self.assertIn(user, candidates, subcommand)
                self.assertIn("root", candidates, subcommand)
                self.assertNotIn("name", candidates, subcommand)  # no header row

    def test_silent_when_userls_fails(self):
        with userls_path("#!/bin/sh\nexit 1\n") as env:
            candidates = self.complete(["userls", "info", ""], 2, env)
        self.assertEqual(candidates, [])


@unittest.skipUnless(shutil.which("zsh"), "zsh is not installed")
class ZshCompletionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls.harness = Path(cls._tmp.name) / "harness.zsh"
        cls.harness.write_text(ZSH_HARNESS)

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def complete(self, words, cword, env):
        env = dict(env)
        env["USERLS_FPATH"] = str(ROOT / "completions")
        env["USERLS_ZDUMP"] = str(Path(self._tmp.name) / "zcompdump")
        result = run(
            [shutil.which("zsh"), "-f", str(self.harness), words, str(cword)],
            env=env,
        )
        if "COMPINIT-FAILED" in result.stdout:
            self.skipTest("zsh compinit harness cannot initialize")
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def test_syntax(self):
        result = run([shutil.which("zsh"), "-n", str(ZSH_COMPLETION)])
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_commands_have_descriptions(self):
        with userls_path() as env:
            output = self.complete("userls", 2, env)
        for item in (
            "info:show one account",
            "groups:list groups or the groups of one account",
            "perms:show group-derived privilege levels",
            "sessions:list active login sessions",
        ):
            self.assertIn(item, output)

    def test_option_specs_before_and_after_subcommand(self):
        expected = (
            "-h[",
            "--help[",
            "--json[",
            "--no-color[",
            "--type=[",
            "--search=[",
            "--version[",
        )
        with userls_path() as env:
            for words, cword in (("userls --", 2), ("userls info --", 3)):
                output = self.complete(words, cword, env)
                for token in expected:
                    self.assertIn(token, output, f"{words} / {token}")

    def test_type_values(self):
        with userls_path() as env:
            output = self.complete("userls --type", 3, env)
        for item in (
            "all:every account",
            "normal:human account with a login shell and home directory",
            "service:service account (non-login shell or bogus home)",
            "system:system account (root or the system UID range)",
            "unknown:account outside every configured range",
        ):
            self.assertIn(item, output)

    def test_accounts_are_described_with_uid_and_type(self):
        user = pwd.getpwuid(os.getuid()).pw_name
        with userls_path() as env:
            for subcommand in ("info", "groups", "perms"):
                output = self.complete(f"userls {subcommand}", 3, env)
                self.assertRegex(
                    output,
                    rf"{re.escape(user)}:uid \d+ · (normal|service|system|unknown)",
                    subcommand,
                )
                self.assertIn("root:uid 0 · system", output, subcommand)
                self.assertNotIn("name:uid", output, subcommand)  # no header row

    def test_silent_when_userls_fails(self):
        with userls_path("#!/bin/sh\nexit 1\n") as env:
            output = self.complete("userls info", 3, env)
        self.assertEqual(output.strip(), "")
