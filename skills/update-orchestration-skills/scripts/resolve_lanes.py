"""Deterministically rank eligible orchestration lanes from measurements and live provider state."""

import argparse
from collections import defaultdict
from datetime import datetime, timedelta, timezone
import json
import math
from pathlib import Path
import re
import statistics
import sys


SKILL_DIR = Path(__file__).resolve().parents[1]
BUNDLED_MEASUREMENTS = SKILL_DIR / "references" / "model-measurements.md"
WORKSPACE_MEASUREMENTS = Path(".orchestration/model-measurements.md")
WORKSPACE_STATE = Path(".orchestration/provider-state.json")

ROLES = ("coding", "reasoning", "accuracy", "knowledge", "review")
AUTHOR_FAMILIES = ("claude", "openai", "google", "deepseek")
EQUIVALENCE_POINTS = 3.0
WEEKLY_MOVE_PCT = 85.0
WEEKLY_STOP_PCT = 90.0
FIVE_HOUR_MOVE_PCT = 90.0
FIVE_HOUR_STOP_PCT = 95.0
DEFAULT_STALE_MINUTES = 5

POOL_ALIASES = {
    "anthropic": "claude",
    "claude": "claude",
    "openai": "codex",
    "chatgpt": "codex",
    "codex": "codex",
    "google": "gemini",
    "gemini": "gemini",
    "agy": "gemini",
    "antigravity": "gemini",
    "deepseek": "deepseek",
}

FAMILY_ALIASES = {
    "anthropic": "claude",
    "claude": "claude",
    "openai": "openai",
    "chatgpt": "openai",
    "codex": "openai",
    "google": "google",
    "gemini": "google",
    "agy": "google",
    "antigravity": "google",
    "deepseek": "deepseek",
}

PROFILE_METRIC_ALIASES = {
    "coding": "coding",
    "reasoning": "reasoning",
    "accuracy": "accuracy",
    "knowledge": "knowledge",
    "knowledge-work": "knowledge",
    "knowledge_work": "knowledge",
    "knowledge work": "knowledge",
    "review": "review",
}

LATENCY_METRICS = {
    "seconds-per-task",
    "s-per-task",
    "latency-seconds",
}

ESTIMATED_LATENCY_METRICS = {
    "estimated-seconds-per-task",
}

INDEX_METRICS = {
    "index",
    "intelligence-index",
    "aa-intelligence-index",
}

MISSING_TOKENS = {"", "-", "\u2013", "\u2014", "null", "none", "n/a", "unknown"}

OBSERVATIONS_RE = re.compile(
    r"<!--\s*observations:start\s*-->\s*```(?:json)?\s*\n(.*?)\n```\s*<!--\s*observations:end\s*-->",
    re.DOTALL,
)
BACKTICK_EFFORT_RE = re.compile(r"^(.*?)\s*`([^`]+)`\s*$")
PAREN_EFFORT_RE = re.compile(r"^(.*?)\s*\(([^)]+)\)\s*$")
LEADING_NUMBER_RE = re.compile(r"^[~*\s]*([+-]?\d+(?:\.\d+)?)")
TABLE_SEP_RE = re.compile(r"^\|?(?:\s*:?-{3,}:?\s*\|)+\s*:?-{3,}:?\s*\|?$")


def normalize_pool(raw):
    """Map provider/client names and aliases to canonical provider-state pool keys."""
    if not raw or not isinstance(raw, str):
        return "unknown"
    token = raw.split("/", 1)[0].strip().lower()
    if not token:
        return "unknown"
    return POOL_ALIASES.get(token, token)


def normalize_family(raw):
    """Map provider/client names and aliases to canonical model-family names."""
    if not raw or not isinstance(raw, str):
        return "unknown"
    token = raw.split("/", 1)[0].strip().lower()
    if not token:
        return "unknown"
    return FAMILY_ALIASES.get(token, token)


def infer_provider_from_model(model_name):
    """Best-effort provider inference when a historical table omits the Provider column."""
    low = model_name.strip().lower()
    if any(tok in low for tok in ("fable", "opus", "sonnet", "haiku", "claude", "mythos")):
        return "anthropic"
    if any(tok in low for tok in ("gpt", "codex", "o1", "o3", "o4", "astra", "sol", "terra", "luna")):
        return "openai"
    if any(tok in low for tok in ("gemini", "neon", "hydrogen", "argon")):
        return "google"
    if "deepseek" in low:
        return "deepseek"
    if "glm" in low:
        return "zhipu"
    if "qwen" in low:
        return "alibaba"
    return "unknown"


def slugify(text):
    """Normalize a model identifier for cross-table matching."""
    return re.sub(r"[^a-z0-9.]+", "-", text.strip().lower()).strip("-")


def parse_iso_utc(raw, field_name="timestamp"):
    """Parse an ISO-8601 timestamp into timezone-aware UTC (Python 3.9+ compatible)."""
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError(f"{field_name} must be a non-empty ISO-8601 string.")
    text = raw.strip()
    if text.endswith(("Z", "z")):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as err:
        raise ValueError(f"Invalid ISO-8601 {field_name}: {raw!r}") from err
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def format_iso_utc(dt):
    """Format a UTC datetime as YYYY-MM-DDTHH:MM:SSZ."""
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_number(cell):
    """Parse a leading numeric value from a Markdown table cell, returning None when missing."""
    cleaned = cell.strip().replace("**", "").strip()
    if cleaned.lower() in MISSING_TOKENS:
        return None
    if cleaned.startswith(("-", "\u2013", "\u2014")) and not re.match(r"^-\d", cleaned):
        return None
    match = LEADING_NUMBER_RE.match(cleaned)
    if not match:
        return None
    value = float(match.group(1))
    return value if math.isfinite(value) else None


def parse_model_and_effort(cell):
    """Extract (model_name, effort) from routing-reference or profile-average table cells."""
    text = cell.strip()
    bt_match = BACKTICK_EFFORT_RE.match(text)
    if bt_match:
        return bt_match.group(1).strip(), bt_match.group(2).strip().lower()

    if "/" in text and "(" not in text and " " not in text:
        model_part, effort_part = text.rsplit("/", 1)
        return model_part.strip(), effort_part.strip().lower()

    paren_match = PAREN_EFFORT_RE.match(text)
    if paren_match:
        model_part = paren_match.group(1).strip()
        inner = paren_match.group(2).strip()
        low_inner = inner.lower()
        if low_inner in ("low", "medium", "high", "xhigh", "max", "unspecified"):
            return model_part, low_inner
        if "highest effort" in low_inner:
            return model_part, "max"
        return model_part, "unspecified"

    return text, "unspecified"


def split_md_row(line):
    """Split a Markdown table row into stripped cell strings."""
    stripped = line.strip()
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|"):
        stripped = stripped[:-1]
    return [cell.strip() for cell in stripped.split("|")]


def extract_markdown_tables(text):
    """Return list of (heading, headers, rows) for all Markdown tables in text."""
    tables = []
    heading = ""
    lines = text.splitlines()
    idx = 0
    while idx < len(lines):
        line = lines[idx]
        stripped = line.strip()
        if stripped.startswith("#"):
            heading = stripped.lstrip("#").strip()
            idx += 1
            continue
        if (
            "|" in line
            and idx + 1 < len(lines)
            and TABLE_SEP_RE.match(lines[idx + 1].strip())
        ):
            headers = split_md_row(line)
            idx += 2
            rows = []
            while idx < len(lines):
                row_line = lines[idx].strip()
                if not row_line or "|" not in row_line or row_line.startswith("#"):
                    break
                cells = split_md_row(row_line)
                if len(cells) >= len(headers):
                    rows.append(cells[: len(headers)])
                idx += 1
            tables.append((heading, headers, rows))
            continue
        idx += 1
    return tables


def _table_candidates(headers, rows):
    """Convert a parsed Markdown profile table into candidate dicts."""
    norm_headers = [h.strip().lower() for h in headers]
    col = {name: i for i, name in enumerate(norm_headers)}

    model_idx = None
    for key in ("model (effort)", "model / effort", "model"):
        if key in col:
            model_idx = col[key]
            break
    if model_idx is None:
        return []

    required_profiles = ("coding", "reasoning", "accuracy")
    if not all(name in col for name in required_profiles):
        return []

    provider_idx = None
    for key in ("provider / client", "provider", "pool"):
        if key in col:
            provider_idx = col[key]
            break

    knowledge_idx = col.get("knowledge work", col.get("knowledge"))
    latency_idx = col.get("s/task", col.get("seconds/task"))
    index_idx = col.get("index", col.get("ii"))

    candidates = []
    for cells in rows:
        raw_model = cells[model_idx]
        model, effort = parse_model_and_effort(raw_model)
        if not model:
            continue
        raw_provider = cells[provider_idx] if provider_idx is not None else infer_provider_from_model(model)
        pool = normalize_pool(raw_provider)
        family = normalize_family(raw_provider)

        profiles = {
            "coding": parse_number(cells[col["coding"]]),
            "reasoning": parse_number(cells[col["reasoning"]]),
            "accuracy": parse_number(cells[col["accuracy"]]),
            "knowledge": parse_number(cells[knowledge_idx]) if knowledge_idx is not None else None,
        }
        latency_s = parse_number(cells[latency_idx]) if latency_idx is not None else None
        index_val = parse_number(cells[index_idx]) if index_idx is not None else None

        candidates.append(
            {
                "model": model,
                "effort": effort,
                "pool": pool,
                "family": family,
                "provider_label": raw_provider,
                "profiles": profiles,
                "review_override": None,
                "index": index_val,
                "latency_s": latency_s,
                "source": "historical",
            }
        )
    return candidates


def parse_historical_candidates(markdown_text):
    """Parse historical routing/profile tables from model-measurements.md."""
    baseline_part = markdown_text.split("<!-- workspace-measurements:v1 -->", 1)[0]
    tables = extract_markdown_tables(baseline_part)

    # Prefer the compact 'Historical routing reference' table when present because it
    # combines multi-source averages with provider/client and s/task columns.
    prioritized = []
    for heading, headers, rows in tables:
        low_heading = heading.lower()
        if "routing reference" in low_heading:
            prioritized.append((0, heading, headers, rows))
        elif "profile averages" in low_heading:
            prioritized.append((1, heading, headers, rows))
        elif "task profiles" in low_heading:
            prioritized.append((2, heading, headers, rows))
        elif "historical scores" in low_heading:
            prioritized.append((3, heading, headers, rows))
        else:
            prioritized.append((4, heading, headers, rows))

    prioritized.sort(key=lambda item: item[0])
    for _, _, headers, rows in prioritized:
        parsed = _table_candidates(headers, rows)
        if parsed:
            return parsed
    return []


def parse_workspace_observations(markdown_text):
    """Parse refreshed workspace models and measurements from <!-- observations:start --> JSON."""
    match = OBSERVATIONS_RE.search(markdown_text)
    if not match:
        return []
    raw_json = match.group(1).strip()
    try:
        payload = json.loads(raw_json)
    except json.JSONDecodeError as err:
        raise ValueError(f"Malformed observations JSON block in measurements file: {err}") from err
    if not isinstance(payload, dict):
        raise ValueError("Observations JSON block must be a JSON object.")

    model_providers = {}
    for row in payload.get("models", []):
        if isinstance(row, dict) and isinstance(row.get("model"), str):
            model_providers[row["model"]] = str(row.get("provider") or "")

    variants = set()
    for row in payload.get("benchmark_checks", []):
        if isinstance(row, dict) and isinstance(row.get("model"), str):
            effort = str(row.get("effort") or "unspecified").strip().lower()
            variants.add((row["model"], effort))

    grouped_values = defaultdict(lambda: defaultdict(list))
    for row in payload.get("measurements", []):
        if not isinstance(row, dict):
            continue
        model = row.get("model")
        metric = row.get("metric")
        value = row.get("value")
        if not isinstance(model, str) or not isinstance(metric, str):
            continue
        effort = str(row.get("effort") or "unspecified").strip().lower()
        variants.add((model, effort))
        if type(value) in (int, float) and math.isfinite(value):
            grouped_values[(model, effort)][metric.strip().lower()].append(float(value))

    represented_models = {model for model, _ in variants}
    for model in model_providers:
        if model not in represented_models:
            variants.add((model, "unspecified"))

    candidates = []
    for model, effort in sorted(variants):
        raw_provider = model_providers.get(model) or infer_provider_from_model(model)
        pool = normalize_pool(raw_provider)
        family = normalize_family(raw_provider)
        metrics = grouped_values[(model, effort)]

        profiles = {"coding": None, "reasoning": None, "accuracy": None, "knowledge": None}
        review_override = None
        latency_s = None
        est_latency_s = None
        index_val = None

        for metric_name, vals in metrics.items():
            if not vals:
                continue
            mean_val = statistics.fmean(vals)
            if metric_name in PROFILE_METRIC_ALIASES:
                canonical = PROFILE_METRIC_ALIASES[metric_name]
                if canonical == "review":
                    review_override = mean_val
                else:
                    profiles[canonical] = mean_val
            elif metric_name in LATENCY_METRICS:
                latency_s = mean_val
            elif metric_name in ESTIMATED_LATENCY_METRICS:
                est_latency_s = mean_val
            elif metric_name in INDEX_METRICS:
                index_val = mean_val

        candidates.append(
            {
                "model": model,
                "effort": effort,
                "pool": pool,
                "family": family,
                "provider_label": raw_provider or "unknown",
                "profiles": profiles,
                "review_override": review_override,
                "index": index_val,
                "latency_s": latency_s if latency_s is not None else est_latency_s,
                "source": "workspace",
            }
        )
    return candidates


def merge_candidates(historical, workspace):
    """Merge historical and workspace candidates; workspace metrics override matching variants."""
    merged = []
    by_key = {}

    for item in historical:
        key = (slugify(item["model"]), item["effort"].lower())
        entry = {
            **item,
            "profiles": dict(item["profiles"]),
        }
        by_key[key] = entry
        merged.append(entry)

    for item in workspace:
        key = (slugify(item["model"]), item["effort"].lower())
        existing = by_key.get(key)
        if existing is None:
            entry = {
                **item,
                "profiles": dict(item["profiles"]),
            }
            by_key[key] = entry
            merged.append(entry)
        else:
            for prof_name, prof_val in item["profiles"].items():
                if prof_val is not None:
                    existing["profiles"][prof_name] = prof_val
            if item["review_override"] is not None:
                existing["review_override"] = item["review_override"]
            if item["latency_s"] is not None:
                existing["latency_s"] = item["latency_s"]
            if item["index"] is not None:
                existing["index"] = item["index"]
            if item["pool"] != "unknown":
                existing["pool"] = item["pool"]
                existing["family"] = item["family"]
                existing["provider_label"] = item["provider_label"]
            existing["source"] = "workspace"
    return merged


def _optional_pct(entry, field):
    value = entry.get(field)
    if value is None:
        return None
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError(f"Provider state field '{field}' must be a finite number or null.")
    if value < 0 or value > 100:
        raise ValueError(f"Provider state field '{field}' must be between 0 and 100 (got {value}).")
    return float(value)


def _validate_stale_minutes(stale_minutes):
    if type(stale_minutes) is not int or stale_minutes < 0:
        raise ValueError(f"stale_minutes must be a non-negative integer (got {stale_minutes!r}).")
    return stale_minutes


def parse_provider_state(raw_state, now, stale_minutes):
    """Normalize and evaluate provider-state.json entries against now and stale TTL."""
    _validate_stale_minutes(stale_minutes)
    if not isinstance(raw_state, dict):
        raise ValueError("provider-state.json must contain a JSON object keyed by pool name.")

    normalized_entries = {}
    for raw_key, entry in raw_state.items():
        if not isinstance(raw_key, str) or not isinstance(entry, dict):
            raise ValueError(f"Invalid provider-state entry for key {raw_key!r}.")
        pool_key = normalize_pool(raw_key)
        # Prefer explicit canonical pool key if both alias and canonical key appear.
        if pool_key not in normalized_entries or raw_key.strip().lower() == pool_key:
            normalized_entries[pool_key] = entry

    evaluated = {}
    warnings = []
    stale_delta = timedelta(minutes=stale_minutes)

    for pool, entry in sorted(normalized_entries.items()):
        status = str(entry.get("status", "up")).strip().lower()
        if status not in ("up", "down"):
            raise ValueError(f"Provider '{pool}' has unsupported status {status!r}; expected 'up' or 'down'.")

        five_hour_pct = _optional_pct(entry, "five_hour_pct")
        weekly_pct = _optional_pct(entry, "weekly_pct")
        limit_note = entry.get("limit")
        resets_at_raw = entry.get("resets_at")
        down_until_raw = entry.get("down_until")
        observed_at_raw = entry.get("observed_at")

        # Evaluate staleness without crashing on missing or unparseable observed_at.
        stale = False
        observed_at_iso = None
        age_minutes = None
        if observed_at_raw is None or (isinstance(observed_at_raw, str) and not observed_at_raw.strip()):
            stale = True
            warnings.append(f"Pool '{pool}' state is stale (missing observed_at).")
        else:
            try:
                observed_dt = parse_iso_utc(observed_at_raw, f"{pool}.observed_at")
                observed_at_iso = format_iso_utc(observed_dt)
                delta = now - observed_dt
                age_minutes = round(delta.total_seconds() / 60.0, 1)
                if delta > stale_delta:
                    stale = True
                    warnings.append(
                        f"Pool '{pool}' state is stale (observed {age_minutes:.1f} min ago; TTL {stale_minutes} min)."
                    )
            except ValueError as err:
                stale = True
                warnings.append(f"Pool '{pool}' state is stale ({err}).")

        # Compute headroom when percentages are available.
        remainders = []
        if weekly_pct is not None:
            remainders.append(max(0.0, 100.0 - weekly_pct))
        if five_hour_pct is not None:
            remainders.append(max(0.0, 100.0 - five_hour_pct))
        headroom = round(min(remainders), 2) if remainders else None

        # Evaluate exclusion (down / stopped) and deprioritization (move threshold).
        excluded = False
        deprioritized = False
        probe_due = False
        reasons = []
        effective_state = "up"

        if status == "down":
            if down_until_raw is None or (isinstance(down_until_raw, str) and not down_until_raw.strip()):
                excluded = True
                effective_state = "down"
                reasons.append("down (no down_until)" + (f": {limit_note}" if limit_note else ""))
            else:
                try:
                    down_until_dt = parse_iso_utc(down_until_raw, f"{pool}.down_until")
                    if down_until_dt > now:
                        excluded = True
                        effective_state = "down"
                        reasons.append(
                            f"down until {format_iso_utc(down_until_dt)}"
                            + (f" ({limit_note})" if limit_note else "")
                        )
                    else:
                        probe_due = True
                except ValueError:
                    excluded = True
                    effective_state = "down"
                    reasons.append(f"down (unparseable down_until: {down_until_raw!r})")

        stop_reasons = []
        if weekly_pct is not None and weekly_pct >= WEEKLY_STOP_PCT:
            stop_reasons.append(f"weekly_pct={weekly_pct:g}% >= {WEEKLY_STOP_PCT:g}%")
        if five_hour_pct is not None and five_hour_pct >= FIVE_HOUR_STOP_PCT:
            stop_reasons.append(f"five_hour_pct={five_hour_pct:g}% >= {FIVE_HOUR_STOP_PCT:g}%")

        if stop_reasons:
            excluded = True
            if effective_state != "down":
                effective_state = "stopped"
            reasons.append("stopped (" + ", ".join(stop_reasons) + ")")
        elif not excluded:
            move_reasons = []
            if weekly_pct is not None and weekly_pct >= WEEKLY_MOVE_PCT:
                move_reasons.append(f"weekly_pct={weekly_pct:g}% >= {WEEKLY_MOVE_PCT:g}%")
            if five_hour_pct is not None and five_hour_pct >= FIVE_HOUR_MOVE_PCT:
                move_reasons.append(f"five_hour_pct={five_hour_pct:g}% >= {FIVE_HOUR_MOVE_PCT:g}%")
            if move_reasons:
                deprioritized = True
                effective_state = "deprioritized"
                reasons.append("past move threshold (" + ", ".join(move_reasons) + ")")

        evaluated[pool] = {
            "status": status,
            "effective_state": effective_state,
            "excluded": excluded,
            "deprioritized": deprioritized,
            "probe_due": probe_due,
            "stale": stale,
            "age_minutes": age_minutes,
            "headroom": headroom,
            "five_hour_pct": five_hour_pct,
            "weekly_pct": weekly_pct,
            "down_until": down_until_raw,
            "resets_at": resets_at_raw,
            "limit": limit_note,
            "observed_at": observed_at_iso or observed_at_raw,
            "reasons": reasons,
        }

    return evaluated, warnings


def role_score(candidate, role):
    """Compute the role score for a candidate, or None when required metrics are missing."""
    if role == "review":
        if candidate.get("review_override") is not None:
            return round(float(candidate["review_override"]), 2)
        acc = candidate["profiles"].get("accuracy")
        reas = candidate["profiles"].get("reasoning")
        know = candidate["profiles"].get("knowledge")
        if acc is None or reas is None:
            return None
        if know is not None:
            return round(0.5 * acc + 0.3 * reas + 0.2 * know, 2)
        return round(0.6 * acc + 0.4 * reas, 2)
    val = candidate["profiles"].get(role)
    return round(float(val), 2) if val is not None else None


def scoring_description(role):
    """Human-readable description of the scoring formula for the selected role."""
    if role == "review":
        return (
            "0.5*accuracy + 0.3*reasoning + 0.2*knowledge "
            "(or 0.6*accuracy + 0.4*reasoning when knowledge is absent; requires accuracy and reasoning)"
        )
    return f"{role} profile score"


def resolve_lanes(
    candidates,
    provider_states,
    *,
    role="coding",
    author_family=None,
    allowed_providers=None,
    restricted_data=False,
    state_loaded=False,
    state_warnings=None,
):
    """Filter, score, classify (±3-pt equivalence), and deterministically rank lanes."""
    warnings = list(state_warnings or [])
    eligible = []
    excluded = []

    allowed_set = set(allowed_providers) if allowed_providers is not None else None
    norm_author = normalize_family(author_family) if author_family else None
    if norm_author and role != "review":
        warnings.append(
            f"--author-family '{norm_author}' is ignored for role '{role}' (applies only to --role review)."
        )

    slug_to_state = {}
    for state_key, state_val in provider_states.items():
        s_key = slugify(state_key)
        if s_key and s_key not in slug_to_state:
            slug_to_state[s_key] = state_val

    for cand in candidates:
        pool = cand["pool"]
        family = cand["family"]
        score = role_score(cand, role)

        exclusion_reasons = []
        if restricted_data and pool != "claude":
            exclusion_reasons.append("restricted-data (claude only)")
        if allowed_set is not None and pool not in allowed_set:
            exclusion_reasons.append("not in --providers allowlist")

        pstate = provider_states.get(pool)
        model_low = cand["model"].strip().lower()
        model_slug = slugify(cand["model"])
        mstate = None
        if model_low != pool:
            mstate = provider_states.get(model_low)
        if mstate is None and model_slug != pool:
            mstate = provider_states.get(model_slug) or slug_to_state.get(model_slug)

        if pstate is not None and pstate["excluded"]:
            exclusion_reasons.extend(pstate["reasons"])
        if mstate is not None and mstate["excluded"]:
            exclusion_reasons.extend(f"model {r}" for r in mstate["reasons"])

        if exclusion_reasons:
            excluded.append(
                {
                    "model": cand["model"],
                    "effort": cand["effort"],
                    "pool": pool,
                    "family": family,
                    "score": score,
                    "source": cand["source"],
                    "reasons": exclusion_reasons,
                }
            )
            continue

        if pstate is None:
            effective_state = "untracked" if state_loaded else "up"
            deprioritized = False
            headroom = None
            stale = state_loaded
            probe_due = False
            state_reasons = ["not listed in provider-state.json"] if state_loaded else []
        else:
            effective_state = pstate["effective_state"]
            deprioritized = pstate["deprioritized"]
            headroom = pstate["headroom"]
            stale = pstate["stale"]
            probe_due = pstate["probe_due"]
            state_reasons = list(pstate["reasons"])

        if mstate is not None:
            if mstate["deprioritized"]:
                deprioritized = True
                effective_state = "deprioritized"
                state_reasons.extend(f"model {r}" for r in mstate["reasons"])
            if mstate["headroom"] is not None:
                headroom = mstate["headroom"] if headroom is None else min(headroom, mstate["headroom"])
            stale = stale or mstate["stale"]
            probe_due = probe_due or mstate["probe_due"]

        same_family = bool(role == "review" and norm_author and family == norm_author)

        eligible.append(
            {
                "model": cand["model"],
                "effort": cand["effort"],
                "pool": pool,
                "family": family,
                "score": score,
                "profiles": dict(cand["profiles"]),
                "latency_s": cand["latency_s"],
                "index": cand["index"],
                "source": cand["source"],
                "pool_state": effective_state,
                "deprioritized": deprioritized,
                "headroom": headroom,
                "stale": stale,
                "probe_due": probe_due,
                "same_family": same_family,
                "state_reasons": state_reasons,
            }
        )

    if state_loaded:
        untracked_pools = sorted({item["pool"] for item in eligible if item["pool_state"] == "untracked"})
        for pool in untracked_pools:
            warnings.append(f"Pool '{pool}' is absent from provider-state.json (treated as stale/unknown headroom).")

    # Compute top score for the ±3-point equivalence rubric.
    # For cross-family review, anchor equivalence to the best eligible cross-family candidate
    # when at least one measured cross-family candidate exists.
    measured = [item for item in eligible if item["score"] is not None]
    cross_family_anchored = False
    if role == "review" and norm_author:
        cross_measured = [item for item in measured if not item["same_family"]]
        if cross_measured:
            anchor_pool = cross_measured
            cross_family_anchored = True
        else:
            anchor_pool = measured
    else:
        anchor_pool = measured

    top_score = max((item["score"] for item in anchor_pool), default=None)

    for item in eligible:
        flags = []
        if item["score"] is None:
            item["delta"] = None
            item["tier"] = "unmeasured"
            flags.append("unmeasured")
        else:
            delta = round(item["score"] - top_score, 2) if top_score is not None else 0.0
            item["delta"] = delta
            if top_score is not None and (top_score - item["score"]) <= EQUIVALENCE_POINTS + 1e-9:
                item["tier"] = "equivalent"
            else:
                item["tier"] = "below (+1 verification)"
                flags.append("below (+1 verification)")

        if item["same_family"]:
            flags.append("same-family")
        if item["deprioritized"]:
            flags.append("deprioritized")
        if item["probe_due"]:
            flags.append("cooldown-expired (probe)")
        if item["stale"]:
            flags.append("stale")
        item["flags"] = flags

    def sort_key(item):
        is_unmeasured = item["score"] is None
        is_same_family = item["same_family"]
        is_below = item["tier"] != "equivalent"
        # Known positive headroom is preferred over unknown (conservative neutral tie-break: 0.0).
        headroom_rank = item["headroom"] if item["headroom"] is not None else 0.0
        score_rank = item["score"] if item["score"] is not None else -1.0
        latency_rank = item["latency_s"] if item["latency_s"] is not None else float("inf")

        if is_unmeasured:
            # Unmeasured candidates always trail measured ones, preserving cross-family and health ordering.
            return (
                2,
                1 if is_same_family else 0,
                1 if item["deprioritized"] else 0,
                -headroom_rank,
                0.0,
                latency_rank,
                item["model"].lower(),
                item["effort"].lower(),
            )

        if not is_below:
            # Equivalent tier: healthy before deprioritized, cross-family first (already bucketed),
            # higher headroom first, then higher score, then lower latency.
            return (
                0 if not is_same_family else 1,
                0,
                1 if item["deprioritized"] else 0,
                -headroom_rank,
                -score_rank,
                latency_rank,
                item["model"].lower(),
                item["effort"].lower(),
            )

        # Below tier: stronger score first, then healthy before deprioritized, higher headroom, lower latency.
        return (
            0 if not is_same_family else 1,
            1,
            -score_rank,
            1 if item["deprioritized"] else 0,
            -headroom_rank,
            latency_rank,
            item["model"].lower(),
            item["effort"].lower(),
        )

    eligible.sort(key=sort_key)
    for rank, item in enumerate(eligible, start=1):
        item["rank"] = rank

    excluded.sort(
        key=lambda item: (
            -(item["score"] if item["score"] is not None else -1.0),
            item["model"].lower(),
            item["effort"].lower(),
        )
    )

    if not eligible:
        warnings.append(f"No eligible lanes available for role '{role}'.")
    elif eligible[0]["same_family"]:
        warnings.append(
            f"No cross-family reviewer available for author family '{norm_author}'; top lane is same-family."
        )
    elif eligible[0]["score"] is None:
        warnings.append(f"All eligible lanes are unmeasured for role '{role}'.")

    return {
        "top_score": top_score,
        "cross_family_anchored": cross_family_anchored,
        "recommended": eligible[0] if eligible else None,
        "ranked": eligible,
        "excluded": excluded,
        "warnings": warnings,
    }


def _fmt_num(val):
    if val is None:
        return "-"
    if float(val).is_integer():
        return str(int(val))
    return f"{val:.2f}".rstrip("0").rstrip(".")


def _fmt_delta(val):
    if val is None:
        return "-"
    if abs(val) < 1e-9:
        return "0"
    sign = "+" if val > 0 else ""
    return f"{sign}{_fmt_num(val)}"


def render_markdown(report):
    """Render lane resolution report as concise GitHub-flavored Markdown."""
    anchor_label = "top eligible cross-family score" if report.get("cross_family_anchored") else "top eligible score"
    lines = [
        f"# Lane resolution · {report['role']}",
        "",
        f"- **Role:** `{report['role']}` ({report['scoring_method']})",
        f"- **Equivalence band:** within ±{report['equivalence_threshold_points']:g} pts of {anchor_label} `{_fmt_num(report['top_score'])}`",
    ]
    if report["author_family"]:
        if report["role"] == "review":
            lines.append(
                f"- **Author family:** `{report['author_family']}` "
                "(cross-family lanes prioritized first; same-family marked `same-family`)"
            )
        else:
            lines.append(
                f"- **Author family:** `{report['author_family']}` "
                f"(ignored for role `{report['role']}`; applies only to `--role review`)"
            )
    if report["restricted_data"]:
        lines.append("- **Data scope:** `restricted` (`claude` pool only)")
    if report["allowed_providers"] is not None:
        allowed_csv = ", ".join(f"`{p}`" for p in report["allowed_providers"])
        lines.append(f"- **Allowed pools:** {allowed_csv}")

    counts = report["candidate_counts"]
    lines.append(
        f"- **Measurements:** `{report['measurements_path']}` "
        f"({counts['historical']} historical, {counts['workspace']} workspace)"
    )
    if report["state_path"]:
        lines.append(
            f"- **Provider state:** `{report['state_path']}` "
            f"(evaluated at `{report['evaluated_at']}`, stale TTL: {report['stale_minutes']} min)"
        )
    else:
        lines.append(
            f"- **Provider state:** none found (evaluated at `{report['evaluated_at']}`; "
            "live quotas unchecked)"
        )

    rec = report["recommended"]
    if rec:
        headroom_str = f"{_fmt_num(rec['headroom'])}%" if rec["headroom"] is not None else "unknown"
        flags_str = f" · flags: {', '.join(rec['flags'])}" if rec["flags"] else ""
        lines.append(
            f"- **Recommended lane:** `{rec['model']}` (`{rec['effort']}`) · "
            f"pool `{rec['pool']}` · score `{_fmt_num(rec['score'])}` · "
            f"headroom `{headroom_str}`{flags_str}"
        )
    else:
        lines.append("- **Recommended lane:** none (no eligible lanes)")

    if report["warnings"]:
        lines.extend(["", "## Warnings", ""])
        for warning in report["warnings"]:
            lines.append(f"- {warning}")

    lines.extend(["", "## Ranked eligible lanes", ""])
    if report["ranked"]:
        lines.extend(
            [
                "| Rank | Model | Effort | Pool | Family | Score | Delta | Tier | Pool state | Headroom | s/task | Flags | Source |",
                "| ---: | --- | --- | --- | --- | ---: | ---: | --- | --- | ---: | ---: | --- | --- |",
            ]
        )
        for row in report["ranked"]:
            headroom_cell = f"{_fmt_num(row['headroom'])}%" if row["headroom"] is not None else "unknown"
            flags_cell = ", ".join(row["flags"]) if row["flags"] else "-"
            lines.append(
                f"| {row['rank']} | `{row['model']}` | `{row['effort']}` | `{row['pool']}` | `{row['family']}` | "
                f"{_fmt_num(row['score'])} | {_fmt_delta(row['delta'])} | {row['tier']} | {row['pool_state']} | "
                f"{headroom_cell} | {_fmt_num(row['latency_s'])} | {flags_cell} | {row['source']} |"
            )
    else:
        lines.append("_No eligible lanes._")

    if report["excluded"]:
        lines.extend(
            [
                "",
                "## Excluded lanes",
                "",
                "| Model | Effort | Pool | Family | Score | Reason |",
                "| --- | --- | --- | --- | ---: | --- |",
            ]
        )
        for row in report["excluded"]:
            reason_cell = "; ".join(row["reasons"])
            lines.append(
                f"| `{row['model']}` | `{row['effort']}` | `{row['pool']}` | `{row['family']}` | "
                f"{_fmt_num(row['score'])} | {reason_cell} |"
            )

    return "\n".join(lines) + "\n"


def _parse_author_family_arg(raw):
    norm = normalize_family(raw)
    if norm not in AUTHOR_FAMILIES:
        allowed = ", ".join(AUTHOR_FAMILIES)
        raise argparse.ArgumentTypeError(f"invalid author family {raw!r} (choose from {allowed})")
    return norm


def _parse_providers_arg(raw):
    tokens = [part.strip() for part in raw.split(",") if part.strip()]
    if not tokens:
        raise argparse.ArgumentTypeError("--providers must specify at least one provider.")
    seen = []
    for tok in tokens:
        pool = normalize_pool(tok)
        if pool not in seen:
            seen.append(pool)
    return seen


def _parse_non_negative_int(raw):
    try:
        value = int(raw)
    except ValueError as err:
        raise argparse.ArgumentTypeError(f"invalid integer: {raw!r}") from err
    if value < 0:
        raise argparse.ArgumentTypeError("value must be >= 0")
    return value


def build_parser():
    parser = argparse.ArgumentParser(
        description=(
            "Deterministically rank eligible orchestration lanes from model measurements and "
            "live provider-state.json using the +/-3-point equivalence rubric. "
            "For --role review, candidates are scored by 0.5*accuracy + 0.3*reasoning + 0.2*knowledge "
            "(falling back to 0.6*accuracy + 0.4*reasoning when knowledge is absent; requires accuracy and reasoning), "
            "prioritizing cross-family reviewers first when --author-family is supplied."
        )
    )
    parser.add_argument(
        "--workspace",
        type=Path,
        default=Path("."),
        help="Workspace directory used to locate default .orchestration/ files (default: '.').",
    )
    parser.add_argument(
        "--measurements",
        type=Path,
        default=None,
        help="Measurements Markdown file (default: <workspace>/.orchestration/model-measurements.md if present, else bundled reference).",
    )
    parser.add_argument(
        "--state",
        type=Path,
        default=None,
        help="Provider state JSON file (default: <workspace>/.orchestration/provider-state.json if present).",
    )
    parser.add_argument(
        "--role",
        choices=ROLES,
        default="coding",
        help=(
            "Task profile role to rank (default: coding). "
            "'review' uses 0.5*accuracy + 0.3*reasoning + 0.2*knowledge "
            "(or 0.6*accuracy + 0.4*reasoning without knowledge)."
        ),
    )
    parser.add_argument(
        "--author-family",
        type=_parse_author_family_arg,
        default=None,
        metavar="{claude,openai,google,deepseek}",
        help="Author model family for --role review; prioritizes cross-family lanes first and flags same-family lanes.",
    )
    parser.add_argument(
        "--providers",
        type=_parse_providers_arg,
        default=None,
        metavar="CSV",
        help="Comma-separated allowlist of providers/pools (e.g. claude,openai,google,deepseek).",
    )
    parser.add_argument(
        "--restricted-data",
        action="store_true",
        help="Restrict eligible lanes to the 'claude' pool only.",
    )
    parser.add_argument(
        "--now",
        default=None,
        metavar="ISO_TIMESTAMP",
        help="Override current UTC time (ISO-8601, e.g. 2026-11-21T16:00:00Z) for deterministic TTL/cooldown checks.",
    )
    parser.add_argument(
        "--stale-minutes",
        type=_parse_non_negative_int,
        default=DEFAULT_STALE_MINUTES,
        metavar="INT",
        help=f"Maximum age in minutes before provider-state readings are flagged stale (default: {DEFAULT_STALE_MINUTES}).",
    )
    parser.add_argument(
        "--format",
        choices=("markdown", "json"),
        default="markdown",
        help="Output format (default: markdown).",
    )
    return parser


def resolve_from_paths(
    *,
    workspace=Path("."),
    measurements_path=None,
    state_path=None,
    role="coding",
    author_family=None,
    allowed_providers=None,
    restricted_data=False,
    now=None,
    stale_minutes=DEFAULT_STALE_MINUTES,
):
    """Load files from disk and return the structured lane resolution report dict."""
    _validate_stale_minutes(stale_minutes)
    ws = Path(workspace)
    if not ws.exists() or not ws.is_dir():
        raise ValueError(f"Workspace directory does not exist: {ws}")

    if measurements_path is not None:
        m_path = Path(measurements_path)
        if not m_path.is_file():
            raise ValueError(f"Measurements file does not exist: {m_path}")
    else:
        ws_meas = ws / WORKSPACE_MEASUREMENTS
        m_path = ws_meas if ws_meas.is_file() else BUNDLED_MEASUREMENTS
        if not m_path.is_file():
            raise ValueError(f"Bundled measurements file not found: {m_path}")

    eval_now = now if now is not None else datetime.now(timezone.utc)

    state_loaded = False
    resolved_state_path = None
    provider_states = {}
    state_warnings = []

    if state_path is not None:
        s_path = Path(state_path)
        if not s_path.is_file():
            raise ValueError(f"Provider state file does not exist: {s_path}")
        resolved_state_path = s_path
    else:
        ws_state = ws / WORKSPACE_STATE
        if ws_state.is_file():
            resolved_state_path = ws_state

    if resolved_state_path is not None:
        try:
            raw_state = json.loads(resolved_state_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as err:
            raise ValueError(f"Invalid JSON in {resolved_state_path}: {err}") from err
        provider_states, state_warnings = parse_provider_state(raw_state, eval_now, stale_minutes)
        state_loaded = True
    else:
        state_warnings.append(
            "No provider-state.json found; assuming all pools are up with unknown headroom."
        )

    meas_text = m_path.read_text(encoding="utf-8")
    historical = parse_historical_candidates(meas_text)
    workspace_obs = parse_workspace_observations(meas_text)
    candidates = merge_candidates(historical, workspace_obs)

    result = resolve_lanes(
        candidates,
        provider_states,
        role=role,
        author_family=author_family,
        allowed_providers=allowed_providers,
        restricted_data=restricted_data,
        state_loaded=state_loaded,
        state_warnings=state_warnings,
    )

    return {
        "role": role,
        "scoring_method": scoring_description(role),
        "equivalence_threshold_points": EQUIVALENCE_POINTS,
        "top_score": result["top_score"],
        "cross_family_anchored": result["cross_family_anchored"],
        "author_family": normalize_family(author_family) if author_family else None,
        "restricted_data": bool(restricted_data),
        "allowed_providers": list(allowed_providers) if allowed_providers is not None else None,
        "evaluated_at": format_iso_utc(eval_now),
        "stale_minutes": stale_minutes,
        "measurements_path": str(m_path),
        "state_path": str(resolved_state_path) if resolved_state_path is not None else None,
        "candidate_counts": {
            "historical": len(historical),
            "workspace": len(workspace_obs),
            "total": len(candidates),
        },
        "warnings": result["warnings"],
        "providers": provider_states,
        "recommended": result["recommended"],
        "ranked": result["ranked"],
        "excluded": result["excluded"],
    }


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    eval_now = None
    if args.now is not None:
        try:
            eval_now = parse_iso_utc(args.now, "--now")
        except ValueError as err:
            parser.error(str(err))

    try:
        report = resolve_from_paths(
            workspace=args.workspace,
            measurements_path=args.measurements,
            state_path=args.state,
            role=args.role,
            author_family=args.author_family,
            allowed_providers=args.providers,
            restricted_data=args.restricted_data,
            now=eval_now,
            stale_minutes=args.stale_minutes,
        )
    except (ValueError, OSError) as err:
        parser.exit(1, f"Lane resolution failed: {err}\n")

    if args.format == "json":
        print(json.dumps(report, indent=2, ensure_ascii=True))
    else:
        print(render_markdown(report), end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
