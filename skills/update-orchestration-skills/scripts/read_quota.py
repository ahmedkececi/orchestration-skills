"""Read Codex subscription quota from the local session logs, without the interactive /status."""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys

# Isolated mode (python3 -I) leaves the script directory off sys.path; add it for sibling imports.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from resolve_lanes import (  # noqa: E402
    WORKSPACE_STATE,
    _write_json_atomic,
    format_iso_utc,
    normalize_state_key,
    parse_iso_utc,
)


SOURCES = ("codex",)
FIVE_HOUR_MINUTES = 300
WEEKLY_MINUTES = 10080
NOTE_PREFIX = "codex log "
NOTE_SEPARATOR = " · "
MAX_FILES_TRIED = 50

DESCRIPTION = """Read Codex quota from the newest session log under <codex_home>/sessions/ and print it.

Codex writes a `rate_limits` event after each turn. The newest event whose limit_id is "codex"
gives the five-hour window (window_minutes 300) and the weekly window (10080). Percentages only
change when Codex is used, so the reading is current even when the log event is old; it is
reported with `source_time` (the log event) and `observed_at` (now, the reading time).

Caveat: ChatGPT web usage draws on the same weekly pool but is not written to the Codex log,
so the weekly figure can lag behind the real one. Treat the weekly number as a lower bound.
"""


class QuotaError(Exception):
    """A reading could not be produced or stored."""


def _epoch_to_iso(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    try:
        return format_iso_utc(datetime.fromtimestamp(value, tz=timezone.utc))
    except (OverflowError, OSError, ValueError):
        return None


def _pct(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value != value:
        return None
    if value < 0 or value > 100:
        return None
    return round(float(value), 2)


def _find_rate_limits(obj, depth=0):
    """Return the first dict stored under a `rate_limits` key, searching a few levels deep."""
    if depth > 4 or not isinstance(obj, dict):
        return None
    candidate = obj.get("rate_limits")
    if isinstance(candidate, dict):
        return candidate
    for value in obj.values():
        if isinstance(value, dict):
            found = _find_rate_limits(value, depth + 1)
            if found is not None:
                return found
    return None


def _window_fields(rate_limits):
    """Map windows by window_minutes (never by position) to the 5h and weekly slots."""
    out = {FIVE_HOUR_MINUTES: None, WEEKLY_MINUTES: None}
    for value in rate_limits.values():
        if not isinstance(value, dict):
            continue
        minutes = value.get("window_minutes")
        if isinstance(minutes, bool) or not isinstance(minutes, (int, float)):
            continue
        if int(minutes) in out and out[int(minutes)] is None:
            out[int(minutes)] = value
    return out[FIVE_HOUR_MINUTES], out[WEEKLY_MINUTES]


def _last_codex_record(path):
    """Last JSON line in path with rate_limits.limit_id == 'codex', as (event_time, rate_limits)."""
    found = None
    with open(path, "r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if '"rate_limits"' not in line:
                continue
            try:
                event = json.loads(line)
            except (json.JSONDecodeError, RecursionError):
                continue
            limits = _find_rate_limits(event)
            if limits is None or limits.get("limit_id") != "codex":
                continue
            found = (event.get("timestamp") if isinstance(event, dict) else None, limits)
    return found


def _session_logs(codex_home):
    sessions = Path(codex_home) / "sessions"
    if not sessions.is_dir():
        raise QuotaError(f"No Codex sessions directory at {sessions}.")
    logs = []
    for root, _dirs, files in os.walk(sessions):
        for name in files:
            if name.endswith(".jsonl"):
                full = Path(root) / name
                try:
                    logs.append((full.stat().st_mtime, str(full)))
                except OSError:
                    continue
    if not logs:
        raise QuotaError(f"No *.jsonl session logs under {sessions}.")
    logs.sort(reverse=True)
    return logs


def read_codex(codex_home, now):
    """Return the parsed Codex reading (newest log first; falls back to older logs if a log has no record)."""
    for mtime, path in _session_logs(codex_home)[:MAX_FILES_TRIED]:
        try:
            record = _last_codex_record(path)
        except OSError:
            continue
        if record is None:
            continue
        event_time, limits = record
        try:
            source_time = format_iso_utc(parse_iso_utc(event_time, "timestamp"))
        except ValueError:
            source_time = format_iso_utc(datetime.fromtimestamp(mtime, tz=timezone.utc))
        five, weekly = _window_fields(limits)
        windows = {}
        for key, window in (("five_hour", five), ("weekly", weekly)):
            pct = _pct(window.get("used_percent")) if window else None
            resets = _epoch_to_iso(window.get("resets_at")) if window else None
            expired = bool(resets and parse_iso_utc(resets) <= now)
            windows[key] = {"pct": pct, "resets_at": resets, "expired": expired}
        if windows["five_hour"]["pct"] is None and windows["weekly"]["pct"] is None:
            continue
        future = [w["resets_at"] for w in windows.values() if w["resets_at"] and not w["expired"]]
        warnings = []
        for key, w in windows.items():
            if w["expired"]:
                warnings.append(
                    f"{key} window reset at {w['resets_at']}, after the last log event; "
                    f"its percentage is unknown until Codex is used again."
                )
                w["pct"] = None
        return {
            "source": "codex",
            "five_hour_pct": windows["five_hour"]["pct"],
            "weekly_pct": windows["weekly"]["pct"],
            "five_hour_resets_at": windows["five_hour"]["resets_at"],
            "weekly_resets_at": windows["weekly"]["resets_at"],
            "resets_at": min(future) if future else None,
            "source_time": source_time,
            "observed_at": format_iso_utc(now),
            "log_file": path,
            "warnings": warnings,
        }
    raise QuotaError(f"No Codex rate_limits record (limit_id 'codex') found under {Path(codex_home) / 'sessions'}.")


def render_text(reading):
    def part(label, pct, resets):
        pct_text = f"{pct:g}%" if pct is not None else "unknown"
        return f"{label} {pct_text}" + (f" (resets {resets})" if resets else "")

    return (
        f"{reading['source']}: "
        f"{part('5h', reading['five_hour_pct'], reading['five_hour_resets_at'])} · "
        f"{part('weekly', reading['weekly_pct'], reading['weekly_resets_at'])} · "
        f"log {reading['source_time']} · observed {reading['observed_at']}"
    )


def merge_note(existing, source_time):
    """Replace an earlier 'codex log ...' fragment, keep other fragments, join with ' · '."""
    fragments = []
    if isinstance(existing, str):
        fragments = [f.strip() for f in existing.split(NOTE_SEPARATOR) if f.strip()]
    fragments = [f for f in fragments if not f.startswith(NOTE_PREFIX)]
    fragments.append(f"{NOTE_PREFIX}{source_time}")
    return NOTE_SEPARATOR.join(fragments)


def state_path_for(workspace):
    return Path(workspace) / WORKSPACE_STATE


def load_state(path):
    """Read an existing provider-state.json; refuse symlinks, missing files, and non-objects."""
    if path.is_symlink() or path.parent.is_symlink():
        raise QuotaError(f"Refusing to read or write provider state through symlink: {path}")
    if not path.exists():
        raise QuotaError(
            f"{path} does not exist; not creating it. Create the workspace state first "
            f"(first-run bootstrap), then run with --write again."
        )
    if path.is_dir():
        raise QuotaError(f"Provider state path is a directory: {path}")
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, RecursionError) as err:
        raise QuotaError(f"Invalid JSON in {path}: {err}") from err
    if not isinstance(state, dict):
        raise QuotaError("provider-state.json must contain a JSON object keyed by pool name.")
    return state


def apply_reading(state, reading):
    """Update only the codex entry's quota fields and note; every other key is preserved."""
    key = next(
        (k for k, v in state.items() if k != "_calibration" and isinstance(k, str) and isinstance(v, dict)
         and normalize_state_key(k) == "codex"),
        None,
    )
    if key is None:
        key = "codex"
        state[key] = {"status": "up"}
    entry = state[key]
    entry["five_hour_pct"] = reading["five_hour_pct"]
    entry["weekly_pct"] = reading["weekly_pct"]
    entry["resets_at"] = reading["resets_at"]
    entry["observed_at"] = reading["observed_at"]
    entry["note"] = merge_note(entry.get("note"), reading["source_time"])
    return state


def build_parser():
    parser = argparse.ArgumentParser(
        description=DESCRIPTION,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--source", choices=SOURCES, default="codex", help="Quota source (default: codex).")
    parser.add_argument(
        "--codex-home",
        default=None,
        help="Codex home directory holding sessions/ (default: $CODEX_HOME or ~/.codex).",
    )
    parser.add_argument("--format", choices=("text", "json"), default="text", help="Output format (default: text).")
    parser.add_argument(
        "--write",
        action="store_true",
        help="Update the codex entry (five_hour_pct, weekly_pct, resets_at, observed_at, note) in "
        "<workspace>/.orchestration/provider-state.json. The file must already exist.",
    )
    parser.add_argument("--workspace", default=".", help="Workspace root for --write (default: .).")
    parser.add_argument("--now", default=None, help="Override the reading time (ISO 8601 UTC); for tests.")
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        now = parse_iso_utc(args.now, "--now") if args.now else datetime.now(timezone.utc)
    except ValueError as err:
        parser.error(str(err))
    codex_home = args.codex_home or os.environ.get("CODEX_HOME") or str(Path.home() / ".codex")

    try:
        state = None
        path = None
        if args.write:
            path = state_path_for(args.workspace)
            state = load_state(path)
        reading = read_codex(codex_home, now)
        if args.write:
            _write_json_atomic(path, apply_reading(state, reading))
    except (QuotaError, ValueError, OSError) as err:
        print(f"read_quota: {err}", file=sys.stderr)
        return 1

    if args.format == "json":
        print(json.dumps(reading, indent=2, ensure_ascii=True))
    else:
        print(render_text(reading))
    for warning in reading["warnings"]:
        print(f"read_quota: warning: {warning}", file=sys.stderr)
    if args.write:
        print(f"read_quota: updated {path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
