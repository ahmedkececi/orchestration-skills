"""Single-manager claim/lock helper for .orchestration/manager-lock.json (zero dependencies)."""

import argparse
from datetime import datetime, timedelta, timezone
import hmac
import json
import os
from pathlib import Path
import secrets
import sys

# Isolated mode (python3 -I) leaves the script directory off sys.path; add it for sibling imports.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from resolve_lanes import (  # noqa: E402
    _write_json_atomic,
    format_iso_utc,
    parse_iso_utc,
)


WORKSPACE_LOCK = Path(".orchestration/manager-lock.json")
LOCK_VERSION = 1
DEFAULT_TTL_MINUTES = 30
MAX_WHO_LEN = 128
TOKEN_BYTES = 8

DESCRIPTION = """Guard a workspace against concurrent orchestration managers.

Stores a local, git-ignored manager claim in <workspace>/.orchestration/manager-lock.json.
At session start run:
  python3 -I .../manager_lock.py status
  python3 -I .../manager_lock.py claim --who <label>

`claim` creates a random per-session token, stores it in the lock file, and prints it
(`token: <hex>` in text output; `token` field in JSON). Record the token in the
checkpoint's manager line and pass `--token <hex>` to `heartbeat` (when updating the
checkpoint) and `release` (at handoff or session end).

`--who` is a human-readable label (main loop + short session hint) shown in `status`
and refusal messages; `--who` alone never counts as the same holder. A `claim` while
a fresh claim exists is refused with exit code 2 unless the caller passes the matching
`--token` (renewal) or `--force` (only with explicit operator approval). `heartbeat`
and `release` require the matching `--token` (exit code 2 otherwise; `release --force`
is allowed with operator approval). An expired claim can be taken by anyone without a
token. A new session (even of the same model) must never reuse another session's token;
if `claim` is refused, stop and ask the operator.
"""


class LockError(Exception):
    """Operational or validation error while accessing the manager lock."""


def lock_path_for(workspace="."):
    return Path(workspace) / WORKSPACE_LOCK


def _validate_who(who):
    if not isinstance(who, str):
        raise LockError("--who must be a non-empty single-line string.")
    cleaned = who.strip()
    if (
        not cleaned
        or len(cleaned) > MAX_WHO_LEN
        or any(ord(ch) < 32 or ord(ch) == 127 for ch in cleaned)
    ):
        raise LockError(f"--who must be a non-empty single-line string (<= {MAX_WHO_LEN} chars).")
    return cleaned


def _validate_ttl(ttl_minutes):
    if type(ttl_minutes) is not int or ttl_minutes < 1:
        raise LockError(f"--ttl-minutes must be a positive integer (got {ttl_minutes!r}).")
    return ttl_minutes


def _generate_token(exclude=None):
    token = secrets.token_hex(TOKEN_BYTES)
    while exclude is not None and hmac.compare_digest(token, exclude):
        token = secrets.token_hex(TOKEN_BYTES)
    return token


def _tokens_match(provided, stored):
    if not isinstance(provided, str) or not isinstance(stored, str):
        return False
    p = provided.strip()
    s = stored.strip()
    if not p or not s:
        return False
    return hmac.compare_digest(p, s)


def _resolve_now(now=None):
    if now is None:
        return datetime.now(timezone.utc)
    if isinstance(now, str):
        return parse_iso_utc(now, "--now")
    if isinstance(now, datetime):
        return now.astimezone(timezone.utc) if now.tzinfo is not None else now.replace(tzinfo=timezone.utc)
    raise LockError(f"Invalid now timestamp: {now!r}")


def _check_workspace(workspace):
    ws = Path(workspace)
    if not ws.exists() or not ws.is_dir():
        raise LockError(f"Workspace directory does not exist: {ws}")
    return ws


def _check_no_symlink(lock_path):
    if lock_path.is_symlink() or lock_path.parent.is_symlink():
        raise LockError(f"Refusing to access manager lock through symlink: {lock_path}")


def _load_lock(lock_path):
    _check_no_symlink(lock_path)
    if not lock_path.exists():
        return None
    if lock_path.is_dir():
        raise LockError(f"Manager lock path is a directory: {lock_path}")
    try:
        data = json.loads(lock_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, RecursionError) as err:
        raise LockError(f"Invalid JSON in {lock_path}: {err}") from err
    if not isinstance(data, dict):
        raise LockError(f"Manager lock file must contain a JSON object: {lock_path}")

    holder = data.get("holder")
    if not isinstance(holder, str) or not holder.strip():
        raise LockError(f"Manager lock is missing a valid 'holder': {lock_path}")
    ttl = data.get("ttl_minutes", DEFAULT_TTL_MINUTES)
    if type(ttl) is not int or ttl < 1:
        raise LockError(f"Manager lock has invalid 'ttl_minutes': {ttl!r}")

    raw_token = data.get("token")
    if raw_token is not None:
        if not isinstance(raw_token, str) or not raw_token.strip():
            raise LockError(f"Manager lock has invalid 'token': {lock_path}")
        stored_token = raw_token.strip()
    else:
        stored_token = None

    claimed_raw = data.get("claimed_at")
    heartbeat_raw = data.get("heartbeat_at") or claimed_raw
    if not heartbeat_raw:
        raise LockError(f"Manager lock is missing 'heartbeat_at'/'claimed_at': {lock_path}")
    heartbeat_dt = parse_iso_utc(heartbeat_raw, "heartbeat_at")
    claimed_dt = parse_iso_utc(claimed_raw, "claimed_at") if claimed_raw else heartbeat_dt
    expires_dt = heartbeat_dt + timedelta(minutes=ttl)

    return {
        "version": data.get("version", LOCK_VERSION),
        "holder": holder.strip(),
        "claimed_at": format_iso_utc(claimed_dt),
        "heartbeat_at": format_iso_utc(heartbeat_dt),
        "ttl_minutes": ttl,
        "expires_at": format_iso_utc(expires_dt),
        "_token": stored_token,
        "_heartbeat_dt": heartbeat_dt,
        "_expires_dt": expires_dt,
    }


def _evaluate_lock(loaded, now_dt):
    if loaded is None:
        return {
            "state": "unlocked",
            "active": False,
            "expired": False,
            "age_minutes": None,
            "remaining_minutes": None,
            "lock": None,
        }
    hb_dt = loaded["_heartbeat_dt"]
    exp_dt = loaded["_expires_dt"]
    age_seconds = max(0.0, (now_dt - hb_dt).total_seconds())
    rem_seconds = (exp_dt - now_dt).total_seconds()
    expired = now_dt >= exp_dt
    age_minutes = round(age_seconds / 60.0, 1)
    remaining_minutes = round(max(0.0, rem_seconds) / 60.0, 1)
    public_lock = {k: v for k, v in loaded.items() if not k.startswith("_")}
    return {
        "state": "expired" if expired else "active",
        "active": not expired,
        "expired": expired,
        "age_minutes": age_minutes,
        "remaining_minutes": remaining_minutes,
        "lock": public_lock,
    }


def _build_payload(holder, claimed_dt, heartbeat_dt, ttl_minutes, token):
    expires_dt = heartbeat_dt + timedelta(minutes=ttl_minutes)
    return {
        "version": LOCK_VERSION,
        "holder": holder,
        "token": token,
        "claimed_at": format_iso_utc(claimed_dt),
        "heartbeat_at": format_iso_utc(heartbeat_dt),
        "ttl_minutes": ttl_minutes,
        "expires_at": format_iso_utc(expires_dt),
    }


def get_status(workspace=".", *, now=None):
    """Inspect the workspace manager lock without modifying it."""
    _check_workspace(workspace)
    now_dt = _resolve_now(now)
    path = lock_path_for(workspace)
    loaded = _load_lock(path)
    info = _evaluate_lock(loaded, now_dt)
    return {
        "action": "status",
        "ok": True,
        "lock_path": str(path),
        "evaluated_at": format_iso_utc(now_dt),
        **info,
    }


def claim_lock(
    workspace=".",
    *,
    who,
    ttl_minutes=DEFAULT_TTL_MINUTES,
    token=None,
    force=False,
    now=None,
):
    """Acquire or renew the workspace manager lock. Returns (exit_code, result_dict)."""
    _check_workspace(workspace)
    clean_who = _validate_who(who)
    ttl = _validate_ttl(ttl_minutes)
    now_dt = _resolve_now(now)
    path = lock_path_for(workspace)
    loaded = _load_lock(path)
    info = _evaluate_lock(loaded, now_dt)

    stored_token = loaded.get("_token") if loaded is not None else None
    token_matches = loaded is not None and _tokens_match(token, stored_token)

    if info["active"] and not token_matches and not force:
        holder = info["lock"]["holder"]
        age = info["age_minutes"]
        holder_ttl = info["lock"]["ttl_minutes"]
        expires = info["lock"]["expires_at"]
        has_token = isinstance(token, str) and bool(token.strip())
        reason = (
            "provided --token does not match active claim"
            if has_token
            else "matching --token required to renew (--who alone does not match)"
        )
        message = (
            f"manager_lock: claim refused — held by '{holder}' "
            f"(age {age:.1f} min, TTL {holder_ttl} min, expires {expires}); {reason}. "
            "Stop and ask the operator; pass --force only with explicit operator approval."
        )
        return 2, {
            "action": "claim",
            "ok": False,
            "refused": True,
            "lock_path": str(path),
            "evaluated_at": format_iso_utc(now_dt),
            "message": message,
            **info,
        }

    renewed = False
    forced = False
    taken_over_from = None

    if info["active"] and token_matches and not force:
        renewed = True
        claimed_dt = parse_iso_utc(loaded["claimed_at"], "claimed_at")
        claim_token = stored_token
    else:
        claimed_dt = now_dt
        claim_token = _generate_token(exclude=stored_token)
        if loaded is not None:
            taken_over_from = loaded["holder"]
            forced = bool(force and info["active"])

    payload = _build_payload(clean_who, claimed_dt, now_dt, ttl, claim_token)
    try:
        _write_json_atomic(path, payload)
    except ValueError as err:
        raise LockError(str(err)) from err

    return 0, {
        "action": "claim",
        "ok": True,
        "refused": False,
        "renewed": renewed,
        "forced": forced,
        "taken_over_from": taken_over_from,
        "token": claim_token,
        "lock_path": str(path),
        "evaluated_at": format_iso_utc(now_dt),
        "state": "active",
        "active": True,
        "expired": False,
        "age_minutes": 0.0,
        "remaining_minutes": float(ttl),
        "lock": payload,
    }


def heartbeat_lock(workspace=".", *, who=None, token=None, ttl_minutes=None, now=None):
    """Refresh heartbeat_at on a lock whose stored token matches `--token`. Returns (exit_code, result_dict)."""
    _check_workspace(workspace)
    clean_who = _validate_who(who) if who is not None else None
    ttl_override = _validate_ttl(ttl_minutes) if ttl_minutes is not None else None
    now_dt = _resolve_now(now)
    path = lock_path_for(workspace)
    loaded = _load_lock(path)
    if loaded is None:
        label = clean_who or "<label>"
        raise LockError(f"No manager claim exists at {path}; run `claim --who {label}` first.")

    info = _evaluate_lock(loaded, now_dt)
    stored_token = loaded.get("_token")
    if not _tokens_match(token, stored_token):
        holder = info["lock"]["holder"]
        age = info["age_minutes"]
        holder_ttl = info["lock"]["ttl_minutes"]
        has_token = isinstance(token, str) and bool(token.strip())
        reason = "provided --token does not match" if has_token else "missing --token"
        message = (
            f"manager_lock: heartbeat refused — {reason}; lock is held by '{holder}' "
            f"(age {age:.1f} min, TTL {holder_ttl} min)."
        )
        return 2, {
            "action": "heartbeat",
            "ok": False,
            "refused": True,
            "lock_path": str(path),
            "evaluated_at": format_iso_utc(now_dt),
            "message": message,
            **info,
        }

    eff_holder = clean_who if clean_who is not None else loaded["holder"]
    eff_ttl = ttl_override if ttl_override is not None else loaded["ttl_minutes"]
    claimed_dt = parse_iso_utc(loaded["claimed_at"], "claimed_at")
    payload = _build_payload(eff_holder, claimed_dt, now_dt, eff_ttl, stored_token)
    try:
        _write_json_atomic(path, payload)
    except ValueError as err:
        raise LockError(str(err)) from err

    return 0, {
        "action": "heartbeat",
        "ok": True,
        "refused": False,
        "token": stored_token,
        "lock_path": str(path),
        "evaluated_at": format_iso_utc(now_dt),
        "state": "active",
        "active": True,
        "expired": False,
        "age_minutes": 0.0,
        "remaining_minutes": float(eff_ttl),
        "lock": payload,
    }


def release_lock(workspace=".", *, who=None, token=None, force=False, now=None):
    """Release the manager lock if `--token` matches or `--force` is passed. Returns (exit_code, result_dict)."""
    _check_workspace(workspace)
    if who is not None:
        _validate_who(who)
    now_dt = _resolve_now(now)
    path = lock_path_for(workspace)
    loaded = _load_lock(path)
    if loaded is None:
        return 0, {
            "action": "release",
            "ok": True,
            "refused": False,
            "released": False,
            "lock_path": str(path),
            "evaluated_at": format_iso_utc(now_dt),
            "state": "unlocked",
            "active": False,
            "expired": False,
            "lock": None,
        }

    info = _evaluate_lock(loaded, now_dt)
    token_matches = _tokens_match(token, loaded.get("_token"))
    if not token_matches and not force:
        holder = info["lock"]["holder"]
        age = info["age_minutes"]
        holder_ttl = info["lock"]["ttl_minutes"]
        has_token = isinstance(token, str) and bool(token.strip())
        reason = "provided --token does not match" if has_token else "missing --token"
        message = (
            f"manager_lock: release refused — {reason}; held by '{holder}' "
            f"(age {age:.1f} min, TTL {holder_ttl} min). "
            "Pass --force only with explicit operator approval."
        )
        return 2, {
            "action": "release",
            "ok": False,
            "refused": True,
            "released": False,
            "lock_path": str(path),
            "evaluated_at": format_iso_utc(now_dt),
            "message": message,
            **info,
        }

    _check_no_symlink(path)
    path.unlink(missing_ok=True)
    return 0, {
        "action": "release",
        "ok": True,
        "refused": False,
        "released": True,
        "forced": bool(force and not token_matches),
        "released_holder": info["lock"]["holder"],
        "lock_path": str(path),
        "evaluated_at": format_iso_utc(now_dt),
        "state": "unlocked",
        "active": False,
        "expired": False,
        "lock": None,
    }


def render_text(result):
    action = result["action"]
    if action == "status":
        if result["state"] == "unlocked":
            return f"manager_lock: unlocked ({result['lock_path']})"
        lock = result["lock"]
        state_word = "active" if result["active"] else "expired"
        tail = (
            f"expires {lock['expires_at']}"
            if result["active"]
            else f"expired at {lock['expires_at']}"
        )
        return (
            f"manager_lock: {state_word} · holder '{lock['holder']}' · "
            f"age {result['age_minutes']:.1f} min / TTL {lock['ttl_minutes']} min ({tail})"
        )
    if not result["ok"]:
        return result["message"]
    if action == "claim":
        lock = result["lock"]
        extra = ""
        if result.get("renewed"):
            extra = " · renewed"
        elif result.get("taken_over_from"):
            how = "forced takeover" if result.get("forced") else "expired claim replaced"
            extra = f" · {how} from '{result['taken_over_from']}'"
        return (
            f"manager_lock: claimed by '{lock['holder']}' · "
            f"TTL {lock['ttl_minutes']} min (expires {lock['expires_at']}){extra}\n"
            f"token: {result['token']}"
        )
    if action == "heartbeat":
        lock = result["lock"]
        return (
            f"manager_lock: heartbeat updated for '{lock['holder']}' · "
            f"TTL {lock['ttl_minutes']} min (expires {lock['expires_at']})"
        )
    if action == "release":
        if not result.get("released"):
            return f"manager_lock: already unlocked ({result['lock_path']})"
        return f"manager_lock: released claim for '{result['released_holder']}'"
    return f"manager_lock: {action} ok"


def _parse_positive_int(raw):
    try:
        val = int(raw)
    except ValueError as err:
        raise argparse.ArgumentTypeError(f"invalid integer: {raw!r}") from err
    if val < 1:
        raise argparse.ArgumentTypeError("value must be >= 1")
    return val


def build_parser():
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--workspace", default=".", help="Workspace root directory (default: .).")
    common.add_argument("--now", default=None, help="Override current UTC time (ISO-8601); for tests.")
    common.add_argument("--format", choices=("text", "json"), default="text", help="Output format (default: text).")

    parser = argparse.ArgumentParser(
        description=DESCRIPTION,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    p_claim = subparsers.add_parser("claim", parents=[common], help="Claim or renew manager ownership of the workspace.")
    p_claim.add_argument(
        "--who",
        required=True,
        help="Human-readable manager label (main loop + short session hint, e.g. opus, opus-s1, sol).",
    )
    p_claim.add_argument(
        "--token",
        default=None,
        help="Matching session token to renew an existing active claim (omit for a new session).",
    )
    p_claim.add_argument(
        "--ttl-minutes",
        type=_parse_positive_int,
        default=DEFAULT_TTL_MINUTES,
        help=f"Lock TTL in minutes (default: {DEFAULT_TTL_MINUTES}).",
    )
    p_claim.add_argument(
        "--force",
        action="store_true",
        help="Take over an active claim with a new session token (use only when operator approves).",
    )

    p_hb = subparsers.add_parser("heartbeat", parents=[common], help="Refresh heartbeat on an existing claim.")
    p_hb.add_argument(
        "--who",
        default=None,
        help="Optional human-readable manager label.",
    )
    p_hb.add_argument(
        "--token",
        default=None,
        help="Session token printed by `claim` (must match the stored token; exit 2 otherwise).",
    )
    p_hb.add_argument(
        "--ttl-minutes",
        type=_parse_positive_int,
        default=None,
        help="Optional new TTL in minutes (default: preserve existing TTL).",
    )

    p_rel = subparsers.add_parser("release", parents=[common], help="Release the manager claim at handoff/end.")
    p_rel.add_argument(
        "--who",
        default=None,
        help="Optional human-readable manager label.",
    )
    p_rel.add_argument(
        "--token",
        default=None,
        help="Session token printed by `claim` (required unless `--force` with operator approval).",
    )
    p_rel.add_argument(
        "--force",
        action="store_true",
        help="Release an active claim without a matching token (use only when operator approves).",
    )

    subparsers.add_parser("status", parents=[common], help="Inspect the current manager claim status.")
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        now_dt = parse_iso_utc(args.now, "--now") if args.now else datetime.now(timezone.utc)
    except ValueError as err:
        parser.error(str(err))

    try:
        if args.command == "status":
            code, result = 0, get_status(args.workspace, now=now_dt)
        elif args.command == "claim":
            code, result = claim_lock(
                args.workspace,
                who=args.who,
                ttl_minutes=args.ttl_minutes,
                token=args.token,
                force=args.force,
                now=now_dt,
            )
        elif args.command == "heartbeat":
            code, result = heartbeat_lock(
                args.workspace,
                who=args.who,
                token=args.token,
                ttl_minutes=args.ttl_minutes,
                now=now_dt,
            )
        elif args.command == "release":
            code, result = release_lock(
                args.workspace,
                who=args.who,
                token=args.token,
                force=args.force,
                now=now_dt,
            )
        else:
            parser.error(f"Unknown command: {args.command}")
    except (LockError, ValueError, OSError) as err:
        print(f"manager_lock: {err}", file=sys.stderr)
        return 1

    if args.format == "json":
        print(json.dumps(result, indent=2, ensure_ascii=True))
        if code != 0 and result.get("message"):
            print(result["message"], file=sys.stderr)
    else:
        stream = sys.stdout if code == 0 else sys.stderr
        print(render_text(result), file=stream)
    return code


if __name__ == "__main__":
    sys.exit(main())
