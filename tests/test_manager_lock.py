"""Tests for manager_lock.py (per-session token, same-label refusal, renewal, heartbeat, release, expiry, force, symlink guard)."""

import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

from test_resolve_lanes import SCRIPTS_DIR

SCRIPT = SCRIPTS_DIR / "manager_lock.py"
T0 = "2026-11-26T10:00:00Z"
T10 = "2026-11-26T10:10:00Z"
T25 = "2026-11-26T10:25:00Z"
T30 = "2026-11-26T10:30:00Z"
T45 = "2026-11-26T10:45:00Z"
TOKEN_LINE_RE = re.compile(r"^token:\s+([0-9a-f]{16})$", re.MULTILINE)


def run(*args):
    return subprocess.run(
        [sys.executable, "-I", "-B", str(SCRIPT), *args],
        capture_output=True,
        text=True,
    )


class ManagerLockTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.ws = Path(self._tmp.name) / "ws"
        self.ws.mkdir()
        self.lock_path = self.ws / ".orchestration" / "manager-lock.json"

    def test_status_unlocked_text_and_json(self):
        res_text = run("status", "--workspace", str(self.ws), "--now", T0)
        self.assertEqual(res_text.returncode, 0, res_text.stderr)
        self.assertIn("unlocked", res_text.stdout)

        res_json = run("status", "--workspace", str(self.ws), "--now", T0, "--format", "json")
        self.assertEqual(res_json.returncode, 0, res_json.stderr)
        data = json.loads(res_json.stdout)
        self.assertEqual(data["state"], "unlocked")
        self.assertFalse(data["active"])
        self.assertIsNone(data["lock"])

    def test_same_label_twice_without_token_is_refused_and_renewal_with_token_succeeds(self):
        # First session claims in text mode: prints token on its own line
        c1 = run("claim", "--who", "opus", "--workspace", str(self.ws), "--now", T0)
        self.assertEqual(c1.returncode, 0, c1.stderr)
        match = TOKEN_LINE_RE.search(c1.stdout)
        self.assertIsNotNone(match, f"Expected 'token: <hex>' line in stdout: {c1.stdout!r}")
        token1 = match.group(1)

        # Lock file persists token; status hides token
        stored = json.loads(self.lock_path.read_text(encoding="utf-8"))
        self.assertEqual(stored["token"], token1)
        st = run("status", "--workspace", str(self.ws), "--now", T10, "--format", "json")
        self.assertEqual(st.returncode, 0, st.stderr)
        st_data = json.loads(st.stdout)
        self.assertEqual(st_data["state"], "active")
        self.assertEqual(st_data["lock"]["holder"], "opus")
        self.assertNotIn("token", st_data["lock"])
        self.assertNotIn(token1, st.stdout)

        # Second session with the SAME --who label without --token is refused (exit 2)
        c_dup = run("claim", "--who", "opus", "--workspace", str(self.ws), "--now", T10)
        self.assertEqual(c_dup.returncode, 2)
        self.assertIn("opus", c_dup.stderr)
        self.assertIn("10.0", c_dup.stderr)
        self.assertNotIn(token1, c_dup.stderr)

        # Claim with a wrong token is also refused (exit 2)
        c_wrong = run("claim", "--who", "opus", "--token", "0000000000000000", "--workspace", str(self.ws), "--now", T10)
        self.assertEqual(c_wrong.returncode, 2)
        self.assertIn("opus", c_wrong.stderr)
        self.assertIn("10.0", c_wrong.stderr)

        # Renewal with matching token succeeds (exit 0), keeps token and claimed_at
        c_renew = run(
            "claim",
            "--who",
            "opus",
            "--token",
            token1,
            "--workspace",
            str(self.ws),
            "--now",
            T25,
            "--format",
            "json",
        )
        self.assertEqual(c_renew.returncode, 0, c_renew.stderr)
        renew_data = json.loads(c_renew.stdout)
        self.assertTrue(renew_data["ok"])
        self.assertTrue(renew_data["renewed"])
        self.assertFalse(renew_data["forced"])
        self.assertEqual(renew_data["token"], token1)
        self.assertEqual(renew_data["lock"]["claimed_at"], T0)
        self.assertEqual(renew_data["lock"]["heartbeat_at"], T25)
        self.assertEqual(renew_data["lock"]["expires_at"], "2026-11-26T10:55:00Z")

    def test_heartbeat_and_release_require_matching_token_and_force_takeover_rotates_token(self):
        # First manager claims lock (JSON)
        c1 = run("claim", "--who", "opus", "--workspace", str(self.ws), "--now", T0, "--format", "json")
        self.assertEqual(c1.returncode, 0, c1.stderr)
        d1 = json.loads(c1.stdout)
        self.assertTrue(d1["ok"])
        token1 = d1["token"]
        self.assertRegex(token1, r"^[0-9a-f]{16}$")
        self.assertEqual(d1["lock"]["holder"], "opus")
        self.assertEqual(d1["lock"]["ttl_minutes"], 30)
        self.assertEqual(d1["lock"]["expires_at"], T30)
        self.assertTrue(self.lock_path.is_file())

        # Second manager claim is refused with exit code 2, naming holder and age
        c2 = run("claim", "--who", "sol", "--workspace", str(self.ws), "--now", T10)
        self.assertEqual(c2.returncode, 2)
        self.assertIn("opus", c2.stderr)
        self.assertIn("10.0", c2.stderr)

        # Second manager JSON refusal also returns exit code 2 without leaking token
        c2_json = run("claim", "--who", "sol", "--workspace", str(self.ws), "--now", T10, "--format", "json")
        self.assertEqual(c2_json.returncode, 2)
        c2_data = json.loads(c2_json.stdout)
        self.assertFalse(c2_data["ok"])
        self.assertTrue(c2_data["refused"])
        self.assertEqual(c2_data["lock"]["holder"], "opus")
        self.assertNotIn("token", c2_data["lock"])

        # Heartbeat with missing token or wrong token is refused (exit 2), naming holder and age
        hb_missing = run("heartbeat", "--who", "opus", "--workspace", str(self.ws), "--now", T10)
        self.assertEqual(hb_missing.returncode, 2)
        self.assertIn("opus", hb_missing.stderr)
        self.assertIn("10.0", hb_missing.stderr)

        hb_wrong = run("heartbeat", "--who", "opus", "--token", "deadbeefdeadbeef", "--workspace", str(self.ws), "--now", T10)
        self.assertEqual(hb_wrong.returncode, 2)
        self.assertIn("opus", hb_wrong.stderr)
        self.assertIn("10.0", hb_wrong.stderr)

        # Heartbeat with matching token succeeds and extends expires_at while preserving claimed_at
        hb = run("heartbeat", "--who", "opus", "--token", token1, "--workspace", str(self.ws), "--now", T25, "--format", "json")
        self.assertEqual(hb.returncode, 0, hb.stderr)
        hb_data = json.loads(hb.stdout)
        self.assertEqual(hb_data["token"], token1)
        self.assertEqual(hb_data["lock"]["claimed_at"], T0)
        self.assertEqual(hb_data["lock"]["heartbeat_at"], T25)
        self.assertEqual(hb_data["lock"]["expires_at"], "2026-11-26T10:55:00Z")

        # Release with missing token or wrong token is refused (exit 2), naming holder and age
        rel_missing = run("release", "--who", "opus", "--workspace", str(self.ws), "--now", T30)
        self.assertEqual(rel_missing.returncode, 2)
        self.assertIn("opus", rel_missing.stderr)
        self.assertIn("5.0", rel_missing.stderr)
        self.assertTrue(self.lock_path.exists())

        rel_wrong = run("release", "--who", "opus", "--token", "deadbeefdeadbeef", "--workspace", str(self.ws), "--now", T30)
        self.assertEqual(rel_wrong.returncode, 2)
        self.assertIn("opus", rel_wrong.stderr)
        self.assertIn("5.0", rel_wrong.stderr)
        self.assertTrue(self.lock_path.exists())

        # --force takeover succeeds (exit 0) and mints a NEW token distinct from token1
        c_force = run("claim", "--who", "opus", "--force", "--ttl-minutes", "15", "--workspace", str(self.ws), "--now", T30, "--format", "json")
        self.assertEqual(c_force.returncode, 0, c_force.stderr)
        cf_data = json.loads(c_force.stdout)
        self.assertTrue(cf_data["forced"])
        self.assertFalse(cf_data["renewed"])
        self.assertEqual(cf_data["taken_over_from"], "opus")
        token2 = cf_data["token"]
        self.assertRegex(token2, r"^[0-9a-f]{16}$")
        self.assertNotEqual(token2, token1)
        self.assertEqual(cf_data["lock"]["ttl_minutes"], 15)
        self.assertEqual(cf_data["lock"]["expires_at"], T45)

        # Old token1 can no longer heartbeat or release after takeover
        self.assertEqual(run("heartbeat", "--who", "opus", "--token", token1, "--workspace", str(self.ws), "--now", T30).returncode, 2)
        self.assertEqual(run("release", "--who", "opus", "--token", token1, "--workspace", str(self.ws), "--now", T30).returncode, 2)

        # New token2 releases cleanly
        rel = run("release", "--who", "opus", "--token", token2, "--workspace", str(self.ws), "--now", T30)
        self.assertEqual(rel.returncode, 0, rel.stderr)
        self.assertFalse(self.lock_path.exists())

        # Releasing when already unlocked is idempotent
        rel_again = run("release", "--who", "opus", "--token", token2, "--workspace", str(self.ws), "--now", T30)
        self.assertEqual(rel_again.returncode, 0, rel_again.stderr)
        self.assertIn("already unlocked", rel_again.stdout)

    def test_release_force_without_token_is_allowed(self):
        c1 = run("claim", "--who", "opus", "--workspace", str(self.ws), "--now", T0)
        self.assertEqual(c1.returncode, 0, c1.stderr)
        rel_force = run("release", "--who", "sol", "--force", "--workspace", str(self.ws), "--now", T10)
        self.assertEqual(rel_force.returncode, 0, rel_force.stderr)
        self.assertFalse(self.lock_path.exists())

    def test_expired_claim_can_be_claimed_without_token_or_force(self):
        c1 = run("claim", "--who", "opus", "--ttl-minutes", "10", "--workspace", str(self.ws), "--now", T0, "--format", "json")
        self.assertEqual(c1.returncode, 0, c1.stderr)
        token1 = json.loads(c1.stdout)["token"]

        # At exact TTL boundary (T10), lock is expired
        st = run("status", "--workspace", str(self.ws), "--now", T10, "--format", "json")
        self.assertEqual(st.returncode, 0, st.stderr)
        st_data = json.loads(st.stdout)
        self.assertEqual(st_data["state"], "expired")
        self.assertTrue(st_data["expired"])
        self.assertFalse(st_data["active"])

        # Anyone (even with the same or different label) can claim without --token or --force
        c2 = run("claim", "--who", "neon", "--workspace", str(self.ws), "--now", T10, "--format", "json")
        self.assertEqual(c2.returncode, 0, c2.stderr)
        d2 = json.loads(c2.stdout)
        self.assertFalse(d2["forced"])
        self.assertFalse(d2["renewed"])
        self.assertEqual(d2["taken_over_from"], "opus")
        self.assertEqual(d2["lock"]["holder"], "neon")
        self.assertNotEqual(d2["token"], token1)

    def test_heartbeat_without_lock_and_symlink_guards(self):
        hb_missing = run("heartbeat", "--who", "opus", "--token", "aaaaaaaaaaaaaaaa", "--workspace", str(self.ws), "--now", T0)
        self.assertEqual(hb_missing.returncode, 1)

        # Symlink lock file refused
        (self.ws / ".orchestration").mkdir(parents=True, exist_ok=True)
        real = Path(self._tmp.name) / "outside.json"
        real.write_text("{}", encoding="utf-8")
        self.lock_path.symlink_to(real)

        st_sym = run("status", "--workspace", str(self.ws), "--now", T0)
        self.assertEqual(st_sym.returncode, 1)
        self.assertIn("symlink", st_sym.stderr.lower())

        c_sym = run("claim", "--who", "opus", "--workspace", str(self.ws), "--now", T0)
        self.assertEqual(c_sym.returncode, 1)
        self.assertIn("symlink", c_sym.stderr.lower())
        self.assertEqual(real.read_text(encoding="utf-8"), "{}")

    def test_rejects_invalid_who_and_ttl(self):
        bad_ttl = run("claim", "--who", "opus", "--ttl-minutes", "0", "--workspace", str(self.ws), "--now", T0)
        self.assertNotEqual(bad_ttl.returncode, 0)
        bad_who = run("claim", "--who", "   ", "--workspace", str(self.ws), "--now", T0)
        self.assertEqual(bad_who.returncode, 1)


if __name__ == "__main__":
    unittest.main()
