"""Read Codex subscription quota from local logs or record a manual pool reading."""

import argparse
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import sys

# Isolated mode (python3 -I) leaves the script directory off sys.path; add it for sibling imports.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from resolve_lanes import (  # noqa: E402
    LANE_ID,
    RESERVED_STATE_KEYS,
    WORKSPACE_STATE,
    _write_json_atomic,
    format_iso_utc,
    normalize_state_key,
    parse_iso_utc,
)


SOURCES = ("codex", "manual")
FIVE_HOUR_MINUTES = 300
WEEKLY_MINUTES = 10080
NOTE_PREFIX = "codex log "
NOTE_SEPARATOR = " · "
MAX_FILES_TRIED = 50
MAX_RECORDS_COMPARED = 5
MAX_NOTE_LEN = 240

DESCRIPTION = """Read Codex quota from the newest session log under <codex_home>/sessions/, or record a
manual quota reading for any pool (e.g. Claude from /usage, Gemini, DeepSeek).

Codex writes a `rate_limits` event after each turn. The newest event whose limit_id is "codex"
gives the five-hour window (window_minutes 300) and the weekly window (10080). Percentages only
change when Codex is used, so the reading is current even when the log event is old; it is
reported with `source_time` (the log event) and `observed_at` (now, the reading time).

Caveat: ChatGPT web usage draws on the same weekly pool but is not written to the Codex log,
so the weekly figure can lag behind the real one. Treat the weekly number as a lower bound.

Manual mode (`--source manual --provider <pool> --five-hour PCT --weekly PCT --write`) writes
the validated reading for that pool with `observed_at` = now into provider-state.json.
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
    """Return the parsed Codex reading with the newest rate_limits timestamp across recent active logs."""
    best = None
    compared = 0
    for mtime, path in _session_logs(codex_home)[:MAX_FILES_TRIED]:
        try:
            record = _last_codex_record(path)
        except OSError:
            continue
        if record is None:
            continue
        event_time, limits = record
        try:
            source_dt = parse_iso_utc(event_time, "timestamp")
        except ValueError:
            source_dt = datetime.fromtimestamp(mtime, tz=timezone.utc)
        source_time = format_iso_utc(source_dt)
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
        candidate = (
            (source_dt, mtime),
            {
                "source": "codex",
                "provider": "codex",
                "five_hour_pct": windows["five_hour"]["pct"],
                "weekly_pct": windows["weekly"]["pct"],
                "five_hour_resets_at": windows["five_hour"]["resets_at"],
                "weekly_resets_at": windows["weekly"]["resets_at"],
                "resets_at": min(future) if future else None,
                "source_time": source_time,
                "observed_at": format_iso_utc(now),
                "log_file": path,
                "warnings": warnings,
            },
        )
        if best is None or candidate[0] > best[0]:
            best = candidate
        compared += 1
        if compared >= MAX_RECORDS_COMPARED:
            break
    if best is not None:
        return best[1]
    raise QuotaError(f"No Codex rate_limits record (limit_id 'codex') found under {Path(codex_home) / 'sessions'}.")


def _validate_manual_pct(value, field_name):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise QuotaError(f"{field_name} must be a finite number between 0 and 100 (got {value!r}).")
    val = float(value)
    if not math.isfinite(val) or val < 0.0 or val > 100.0:
        raise QuotaError(f"{field_name} must be between 0 and 100 (got {value!r}).")
    out = round(val, 2)
    return 0.0 if out == 0.0 else out


def _validate_manual_provider(raw):
    if not isinstance(raw, str) or not raw.strip():
        raise QuotaError("--provider must be a non-empty pool or model identifier.")
    text = raw.strip()
    if text.startswith("_") or any(ord(ch) < 32 or ord(ch) == 127 or ch == "|" for ch in text):
        raise QuotaError(f"Invalid --provider identifier: {raw!r}.")
    key = normalize_state_key(text)
    if not key or key == "unknown" or key.startswith("_") or not LANE_ID.fullmatch(key):
        raise QuotaError(f"Invalid --provider identifier: {raw!r}.")
    return key


def _validate_manual_note(note):
    if note is None:
        return None
    if not isinstance(note, str):
        raise QuotaError("--note must be a string.")
    cleaned = note.strip()
    if len(cleaned) > MAX_NOTE_LEN or any(ord(ch) < 32 or ord(ch) == 127 for ch in cleaned):
        raise QuotaError(f"--note must be a single-line string (<= {MAX_NOTE_LEN} chars).")
    return cleaned or None


def read_manual(
    provider,
    *,
    five_hour=None,
    weekly=None,
    five_hour_resets=None,
    weekly_resets=None,
    note=None,
    now,
):
    """Validate and construct a manual quota reading for any pool."""
    pool_key = _validate_manual_provider(provider)
    if five_hour is None and weekly is None:
        raise QuotaError("Manual reading requires at least one of --five-hour or --weekly.")

    five_pct = _validate_manual_pct(five_hour, "--five-hour") if five_hour is not None else None
    week_pct = _validate_manual_pct(weekly, "--weekly") if weekly is not None else None
    clean_note = _validate_manual_note(note)

    warnings = []
    five_r = None
    week_r = None
    future = []
    if five_hour_resets is not None:
        dt = parse_iso_utc(five_hour_resets, "--five-hour-resets")
        five_r = format_iso_utc(dt)
        if dt > now:
            future.append(five_r)
        else:
            warnings.append(f"--five-hour-resets ({five_r}) is not in the future relative to observed_at.")
    if weekly_resets is not None:
        dt = parse_iso_utc(weekly_resets, "--weekly-resets")
        week_r = format_iso_utc(dt)
        if dt > now:
            future.append(week_r)
        else:
            warnings.append(f"--weekly-resets ({week_r}) is not in the future relative to observed_at.")

    now_iso = format_iso_utc(now)
    return {
        "source": "manual",
        "provider": pool_key,
        "five_hour_pct": five_pct,
        "weekly_pct": week_pct,
        "five_hour_resets_at": five_r,
        "weekly_resets_at": week_r,
        "resets_at": min(future) if future else None,
        "source_time": now_iso,
        "observed_at": now_iso,
        "note": clean_note,
        "warnings": warnings,
    }


def render_text(reading):
    def part(label, pct, resets):
        pct_text = f"{pct:g}%" if pct is not None else "unknown"
        return f"{label} {pct_text}" + (f" (resets {resets})" if resets else "")

    if reading["source"] == "manual":
        note_part = f" · note {reading['note']}" if reading.get("note") else ""
        return (
            f"{reading['provider']} (manual): "
            f"{part('5h', reading['five_hour_pct'], reading['five_hour_resets_at'])} · "
            f"{part('weekly', reading['weekly_pct'], reading['weekly_resets_at'])} · "
            f"observed {reading['observed_at']}{note_part}"
        )

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
    """Update only the target pool's quota fields and note; every other key is preserved."""
    target_pool = reading.get("provider") or "codex"
    key = next(
        (
            k
            for k, v in state.items()
            if k not in RESERVED_STATE_KEYS
            and isinstance(k, str)
            and isinstance(v, dict)
            and normalize_state_key(k) == target_pool
        ),
        None,
    )
    if key is None:
        key = target_pool
        state[key] = {"status": "up"}
    entry = state[key]
    entry["five_hour_pct"] = reading["five_hour_pct"]
    entry["weekly_pct"] = reading["weekly_pct"]
    entry["resets_at"] = reading["resets_at"]
    entry["observed_at"] = reading["observed_at"]
    if reading.get("source") == "codex":
        entry["note"] = merge_note(entry.get("note"), reading["source_time"])
    elif reading.get("note") is not None:
        entry["note"] = reading["note"]
    return state


def _parse_pct_arg(raw):
    try:
        val = float(raw)
    except ValueError as err:
        raise argparse.ArgumentTypeError(f"invalid percentage: {raw!r}") from err
    if not math.isfinite(val) or val < 0.0 or val > 100.0:
        raise argparse.ArgumentTypeError(f"percentage must be between 0 and 100 (got {raw!r})")
    return val


def build_parser():
    parser = argparse.ArgumentParser(
        description=DESCRIPTION,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--source", choices=SOURCES, default="codex", help="Quota source (default: codex).")
    parser.add_argument(
        "--codex-home",
        default=None,
        help="Codex home directory holding sessions/ (default: $CODEX_HOME or ~/.codex; --source codex only).",
    )
    parser.add_argument(
        "--provider",
        default=None,
        help="Target pool or model key for --source manual (e.g. claude, gemini, deepseek, codex).",
    )
    parser.add_argument(
        "--five-hour",
        type=_parse_pct_arg,
        default=None,
        metavar="PCT",
        help="Five-hour window usage percentage 0-100 (--source manual).",
    )
    parser.add_argument(
        "--weekly",
        type=_parse_pct_arg,
        default=None,
        metavar="PCT",
        help="Weekly window usage percentage 0-100 (--source manual).",
    )
    parser.add_argument(
        "--five-hour-resets",
        default=None,
        metavar="ISO",
        help="Optional five-hour reset timestamp in ISO-8601 UTC (--source manual).",
    )
    parser.add_argument(
        "--weekly-resets",
        default=None,
        metavar="ISO",
        help="Optional weekly reset timestamp in ISO-8601 UTC (--source manual).",
    )
    parser.add_argument(
        "--note",
        default=None,
        metavar="TEXT",
        help="Optional single-line note to store with the reading (--source manual).",
    )
    parser.add_argument("--format", choices=("text", "json"), default="text", help="Output format (default: text).")
    parser.add_argument(
        "--write",
        action="store_true",
        help="Update the pool entry (five_hour_pct, weekly_pct, resets_at, observed_at, note) in "
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

    manual_flags_used = any(
        val is not None
        for val in (
            args.provider,
            args.five_hour,
            args.weekly,
            args.five_hour_resets,
            args.weekly_resets,
            args.note,
        )
    )
    if args.source == "codex":
        if manual_flags_used:
            parser.error(
                "--provider, --five-hour, --weekly, --five-hour-resets, --weekly-resets, "
                "and --note require --source manual."
            )
    else:
        if args.codex_home is not None:
            parser.error("--codex-home cannot be used with --source manual.")
        if not args.provider:
            parser.error("--provider is required with --source manual.")
        if args.five_hour is None and args.weekly is None:
            parser.error("--source manual requires at least one of --five-hour or --weekly.")

    try:
        state = None
        path = None
        if args.write:
            path = state_path_for(args.workspace)
            state = load_state(path)
        if args.source == "manual":
            reading = read_manual(
                args.provider,
                five_hour=args.five_hour,
                weekly=args.weekly,
                five_hour_resets=args.five_hour_resets,
                weekly_resets=args.weekly_resets,
                note=args.note,
                now=now,
            )
        else:
            codex_home = args.codex_home or os.environ.get("CODEX_HOME") or str(Path.home() / ".codex")
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
