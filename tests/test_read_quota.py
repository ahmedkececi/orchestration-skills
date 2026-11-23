"""Tests for read_quota.py using temporary Codex homes and workspaces only (never the real ~/.codex)."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from test_resolve_lanes import SCRIPTS_DIR, resolve_lanes  # noqa: F401  (adds SCRIPTS_DIR to sys.path)

import read_quota  # noqa: E402

SCRIPT = SCRIPTS_DIR / "read_quota.py"
NOW = "2026-11-23T14:00:00Z"
FIVE_RESET = 1795453698  # 2026-11-23T17:08:18Z, after NOW
WEEK_RESET = 1795635272  # 2026-11-25T19:34:32Z, after NOW


def event(timestamp, *, limit_id="codex", primary=(300, 2.0, FIVE_RESET), secondary=(10080, 90.0, WEEK_RESET)):
    limits = {"limit_id": limit_id}
    for name, spec in (("primary", primary), ("secondary", secondary)):
        if spec is not None:
            limits[name] = {"window_minutes": spec[0], "used_percent": spec[1], "resets_at": spec[2]}
    return {"timestamp": timestamp, "type": "event_msg", "payload": {"type": "token_count", "rate_limits": limits}}


def write_log(home, relpath, events, mtime=None):
    path = Path(home) / "sessions" / relpath
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(e if isinstance(e, str) else json.dumps(e) for e in events) + "\n", encoding="utf-8")
    if mtime is not None:
        os.utime(path, (mtime, mtime))
    return path


def run(*args):
    return subprocess.run([sys.executable, "-I", "-B", str(SCRIPT), *args], capture_output=True, text=True)


class ReadQuotaTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.home = Path(self._tmp.name) / "codex"
        self.ws = Path(self._tmp.name) / "ws"
        (self.ws / ".orchestration").mkdir(parents=True)
        self.state = self.ws / ".orchestration" / "provider-state.json"

    def read_json_output(self, *extra):
        result = run("--codex-home", str(self.home), "--format", "json", "--now", NOW, *extra)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_parses_last_codex_record_and_reports_both_times(self):
        write_log(
            self.home,
            "2026/11/23/a.jsonl",
            [
                event("2026-11-23T10:00:00.000Z", primary=(300, 50.0, FIVE_RESET)),
                "not json {\"rate_limits\"",
                event("2026-11-23T11:00:00.000Z", limit_id="other", primary=(300, 99.0, FIVE_RESET)),
                event("2026-11-23T12:09:25.934Z"),
                {"timestamp": "2026-11-23T12:10:00Z", "payload": {"rate_limits": None}},
            ],
        )
        reading = self.read_json_output()
        self.assertEqual(reading["five_hour_pct"], 2.0)
        self.assertEqual(reading["weekly_pct"], 90.0)
        self.assertEqual(reading["source_time"], "2026-11-23T12:09:25Z")
        self.assertEqual(reading["observed_at"], NOW)
        self.assertEqual(reading["five_hour_resets_at"], "2026-11-23T17:08:18Z")
        self.assertEqual(reading["resets_at"], "2026-11-23T17:08:18Z")

    def test_windows_match_by_minutes_not_position(self):
        write_log(
            self.home,
            "a.jsonl",
            [event("2026-11-23T12:00:00Z", primary=(10080, 77.0, WEEK_RESET), secondary=(300, 11.0, FIVE_RESET))],
        )
        reading = self.read_json_output()
        self.assertEqual(reading["five_hour_pct"], 11.0)
        self.assertEqual(reading["weekly_pct"], 77.0)

    def test_newest_file_wins_and_older_file_is_fallback(self):
        write_log(self.home, "old.jsonl", [event("2026-11-22T12:00:00Z", primary=(300, 40.0, FIVE_RESET))], mtime=1_000_000)
        write_log(self.home, "new.jsonl", [event("2026-11-23T12:00:00Z", primary=(300, 6.0, FIVE_RESET))], mtime=2_000_000)
        self.assertEqual(self.read_json_output()["five_hour_pct"], 6.0)
        write_log(self.home, "newest.jsonl", [{"type": "session_meta"}], mtime=3_000_000)
        self.assertEqual(self.read_json_output()["five_hour_pct"], 6.0)

    def test_expired_window_reports_unknown_percentage(self):
        write_log(self.home, "a.jsonl", [event("2026-11-23T01:00:00Z", primary=(300, 88.0, 1795400000))])
        reading = self.read_json_output()
        self.assertIsNone(reading["five_hour_pct"])
        self.assertEqual(reading["weekly_pct"], 90.0)
        self.assertEqual(reading["resets_at"], "2026-11-25T19:34:32Z")
        self.assertTrue(reading["warnings"])

    def test_default_output_is_one_line(self):
        write_log(self.home, "a.jsonl", [event("2026-11-23T12:09:25Z")])
        result = run("--codex-home", str(self.home), "--now", NOW)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(result.stdout.strip().splitlines()), 1)
        self.assertIn("5h 2%", result.stdout)
        self.assertIn("weekly 90%", result.stdout)

    def test_write_updates_only_codex_fields_and_keeps_everything_else(self):
        write_log(self.home, "a.jsonl", [event("2026-11-23T12:09:25Z")])
        original = {
            "claude": {"status": "up", "five_hour_pct": 10, "observed_at": "2026-11-23T13:59:00Z"},
            "codex": {
                "status": "up",
                "down_until": None,
                "limit": None,
                "five_hour_pct": 70,
                "weekly_pct": 80,
                "resets_at": None,
                "observed_at": "2026-11-20T00:00:00Z",
                "note": "manual hint · codex log 2026-11-20T00:00:00Z · plan plus",
            },
            "_calibration": {"version": 1, "lanes": {"x": {"samples": 3}}},
        }
        self.state.write_text(json.dumps(original), encoding="utf-8")
        result = run("--codex-home", str(self.home), "--workspace", str(self.ws), "--write", "--now", NOW)
        self.assertEqual(result.returncode, 0, result.stderr)
        state = json.loads(self.state.read_text(encoding="utf-8"))
        self.assertEqual(state["claude"], original["claude"])
        self.assertEqual(state["_calibration"], original["_calibration"])
        codex = state["codex"]
        self.assertEqual(codex["five_hour_pct"], 2.0)
        self.assertEqual(codex["weekly_pct"], 90.0)
        self.assertEqual(codex["resets_at"], "2026-11-23T17:08:18Z")
        self.assertEqual(codex["observed_at"], NOW)
        self.assertEqual(codex["status"], "up")
        self.assertEqual(codex["note"], "manual hint · plan plus · codex log 2026-11-23T12:09:25Z")
        # Second run replaces the fragment instead of stacking it.
        run("--codex-home", str(self.home), "--workspace", str(self.ws), "--write", "--now", NOW)
        again = json.loads(self.state.read_text(encoding="utf-8"))["codex"]["note"]
        self.assertEqual(again.count("codex log "), 1)

    def test_write_creates_codex_entry_when_missing(self):
        write_log(self.home, "a.jsonl", [event("2026-11-23T12:09:25Z")])
        self.state.write_text(json.dumps({"claude": {"status": "up"}}), encoding="utf-8")
        result = run("--codex-home", str(self.home), "--workspace", str(self.ws), "--write", "--now", NOW)
        self.assertEqual(result.returncode, 0, result.stderr)
        state = json.loads(self.state.read_text(encoding="utf-8"))
        self.assertEqual(state["codex"]["status"], "up")
        self.assertEqual(state["codex"]["note"], "codex log 2026-11-23T12:09:25Z")
        self.assertEqual(state["claude"], {"status": "up"})

    def test_written_reading_is_fresh_for_the_resolver(self):
        write_log(self.home, "a.jsonl", [event("2026-11-20T12:00:00Z")])
        self.state.write_text("{}", encoding="utf-8")
        run("--codex-home", str(self.home), "--workspace", str(self.ws), "--write", "--now", NOW)
        raw = json.loads(self.state.read_text(encoding="utf-8"))
        states, _warnings = resolve_lanes.parse_provider_state(raw, resolve_lanes.parse_iso_utc(NOW), 5)
        self.assertFalse(states["codex"]["stale"])

    def test_write_without_existing_file_exits_1_and_creates_nothing(self):
        write_log(self.home, "a.jsonl", [event("2026-11-23T12:09:25Z")])
        result = run("--codex-home", str(self.home), "--workspace", str(self.ws), "--write", "--now", NOW)
        self.assertEqual(result.returncode, 1)
        self.assertIn("does not exist", result.stderr)
        self.assertFalse(self.state.exists())

    def test_write_refuses_symlinked_state_file(self):
        write_log(self.home, "a.jsonl", [event("2026-11-23T12:09:25Z")])
        target = Path(self._tmp.name) / "real.json"
        target.write_text("{}", encoding="utf-8")
        self.state.symlink_to(target)
        result = run("--codex-home", str(self.home), "--workspace", str(self.ws), "--write", "--now", NOW)
        self.assertEqual(result.returncode, 1)
        self.assertIn("symlink", result.stderr)
        self.assertEqual(target.read_text(encoding="utf-8"), "{}")

    def test_missing_record_exits_1_and_leaves_file_untouched(self):
        write_log(self.home, "a.jsonl", [event("2026-11-23T12:09:25Z", limit_id="other")])
        before = json.dumps({"codex": {"status": "up", "five_hour_pct": 5}})
        self.state.write_text(before, encoding="utf-8")
        result = run("--codex-home", str(self.home), "--workspace", str(self.ws), "--write", "--now", NOW)
        self.assertEqual(result.returncode, 1)
        self.assertIn("rate_limits", result.stderr)
        self.assertEqual(self.state.read_text(encoding="utf-8"), before)

    def test_missing_sessions_directory_exits_1(self):
        result = run("--codex-home", str(self.home), "--now", NOW)
        self.assertEqual(result.returncode, 1)
        self.assertIn("sessions", result.stderr)

    def test_isolated_help_exits_0(self):
        result = run("--help")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("ChatGPT web", result.stdout)

    def test_merge_note_helper(self):
        self.assertEqual(read_quota.merge_note(None, "T"), "codex log T")
        self.assertEqual(read_quota.merge_note("a · codex log X", "T"), "a · codex log T")


if __name__ == "__main__":
    unittest.main()
