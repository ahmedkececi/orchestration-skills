"""Helper scripts must start under isolated mode (python3 -I), where the script directory is not on sys.path."""

from pathlib import Path
import subprocess
import sys
import unittest


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "skills" / "update-orchestration-skills" / "scripts"


class IsolatedModeTests(unittest.TestCase):
    def test_every_script_runs_help_under_isolated_mode(self):
        scripts = sorted(SCRIPTS_DIR.glob("*.py"))
        self.assertTrue(scripts)
        for script in scripts:
            with self.subTest(script=script.name):
                result = subprocess.run(
                    [sys.executable, "-I", "-B", str(script), "--help"],
                    capture_output=True,
                    text=True,
                    cwd=str(SCRIPTS_DIR.parent),
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertNotIn("ModuleNotFoundError", result.stderr)


if __name__ == "__main__":
    unittest.main()
