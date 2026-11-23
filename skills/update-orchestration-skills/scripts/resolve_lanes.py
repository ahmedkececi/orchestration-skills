"""Deterministically rank eligible orchestration lanes from measurements and live provider state."""

import argparse
from collections import defaultdict
from datetime import datetime, timedelta, timezone
import json
import math
import os
from pathlib import Path
import re
import stat
import statistics
import sys
from tempfile import NamedTemporaryFile

# Isolated mode (python3 -I) leaves the script directory off sys.path; add it for sibling imports.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from refresh import normalize


SKILL_DIR = Path(__file__).resolve().parents[1]
BUNDLED_MEASUREMENTS = SKILL_DIR / "references" / "model-measurements.md"
WORKSPACE_MEASUREMENTS = Path(".orchestration/model-measurements.md")
WORKSPACE_STATE = Path(".orchestration/provider-state.json")
WORKSPACE_PROFILE = Path(".orchestration/project-profile.md")

ROLES = ("coding", "reasoning", "accuracy", "knowledge", "review")
AUTHOR_FAMILIES = ("claude", "openai", "google", "deepseek")
EQUIVALENCE_POINTS = 3.0
WEEKLY_MOVE_PCT = 90.0
WEEKLY_STOP_PCT = 95.0
FIVE_HOUR_MOVE_PCT = 90.0
FIVE_HOUR_STOP_PCT = 95.0
DEFAULT_STALE_MINUTES = 5

UNIT_SIZES = ("xs", "s", "m", "l", "xl")
UNIT_SIZE_MULTIPLIERS = {
    "xs": 0.25,
    "s": 0.55,
    "m": 1.0,
    "l": 1.9,
    "xl": 3.2,
}
DEFAULT_BURN_PER_M = {
    "codex": {"five_hour_pct": 5.0, "weekly_pct": 2.0},
    "claude": {"five_hour_pct": 6.0, "weekly_pct": 2.5},
    "gemini": {"five_hour_pct": 4.5, "weekly_pct": 1.8},
    "deepseek": {"five_hour_pct": 2.0, "weekly_pct": 1.0},
}
FALLBACK_BURN_PER_M = {"five_hour_pct": 5.0, "weekly_pct": 2.0}

CALIBRATION_KEY = "_calibration"
CALIBRATION_VERSION = 1
CALIBRATION_ALPHA = 0.35
SAFETY_MARGIN_COLD = 1.40
SAFETY_MARGIN_LOW_SAMPLES = 1.25
SAFETY_MARGIN_MIN_AUTO = 1.15
SAFETY_MARGIN_MAX_AUTO = 1.50
SAFETY_MARGIN_MIN_OVERRIDE = 1.0
SAFETY_MARGIN_MAX_OVERRIDE = 3.0
MAX_RATIO_MIN = 1.0
MAX_RATIO_MAX = 2.0

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

HISTORICAL_MODEL_IDS = {
    "fable 5.2": "claude-fable-5-2",
    "fable-5.2": "claude-fable-5-2",
    "opus 5.5": "claude-opus-5-5",
    "opus-5.5": "claude-opus-5-5",
    "sonnet 5.5": "claude-sonnet-5-5",
    "sonnet-5.5": "claude-sonnet-5-5",
    "haiku 5.5": "claude-haiku-5-5",
    "haiku-5.5": "claude-haiku-5-5",
    "neon": "gemini-4-neon",
    "hydrogen": "gemini-4-hydrogen",
    "argon": "gemini-4-argon",
    "deepseek-flash": "deepseek-v4.1-flash-1017",
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
KNOWN_EFFORTS = {"low", "medium", "high", "xhigh", "max", "minimal", "default", "unspecified"}

WORKSPACE_DELIMITER = "<!-- workspace-measurements:v1 -->"
OBSERVATIONS_START_RE = re.compile(r"<!--\s*observations:start\s*-->")
OBSERVATIONS_RE = re.compile(
    r"<!--\s*observations:start\s*-->\s*```(?:json)?\s*\n(.*?)\n```\s*<!--\s*observations:end\s*-->",
    re.DOTALL,
)
BACKTICK_EFFORT_RE = re.compile(r"^(.*?)\s*`([^`]+)`\s*$")
PAREN_EFFORT_RE = re.compile(r"^(.*?)\s*\(([^)]+)\)\s*$")
LEADING_NUMBER_RE = re.compile(
    r"^[~*\s]*([+-]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?(?:[eE][+-]?\d+)?)(.*)$"
)
RANGE_SUFFIX_RE = re.compile(r"^\s*[-\u2013\u2014]\s*[+-]?\d")
BAD_NUMBER_TAIL_RE = re.compile(r"^[.,eE\d]")
TABLE_SEP_RE = re.compile(r"^\|?(?:\s*:?-{3,}:?\s*\|)+\s*:?-{3,}:?\s*\|?$")
PROFILE_MARKER = "<!-- orchestration-lanes:v1 -->"
PROFILE_LANES_RE = re.compile(r"^[ \t]*```json[ \t]*\r?\n(.*?)\r?\n[ \t]*```[ \t]*(?:\r?\n|$)", re.DOTALL)
LANE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/+-]{0,127}")
POOL_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,127}")
REQUIRED_LANE_FIELDS = {"model", "effort", "pool", "runner", "roles"}
MAX_LIMIT_LEN = 160

_ANTHROPIC_RE = re.compile(r"(?:^|[^a-z0-9])(?:claude(?=$|[^a-z])|(?:fable|opus|sonnet|haiku|mythos)(?=$|[^a-z0-9]))")
_OPENAI_RE = re.compile(r"(?:^|[^a-z0-9])(?:gpt(?=$|[^a-z])|(?:codex|o1|o3|o4|astra|sol|terra|luna)(?=$|[^a-z0-9]))")
_GOOGLE_RE = re.compile(r"(?:^|[^a-z0-9])(?:gemini(?=$|[^a-z])|(?:neon|hydrogen|argon)(?=$|[^a-z0-9]))")
_DEEPSEEK_RE = re.compile(r"(?:^|[^a-z0-9])deepseek(?=$|[^a-z])")
_ZHIPU_RE = re.compile(r"(?:^|[^a-z0-9])glm(?=$|[^a-z])")
_ALIBABA_RE = re.compile(r"(?:^|[^a-z0-9])qwen(?=$|[^a-z])")


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


def canonical_model_id(model):
    """Resolve shipped benchmark aliases without guessing at other model IDs."""
    model = model.strip()
    return HISTORICAL_MODEL_IDS.get(model.lower(), model)


def normalize_state_key(raw):
    """Normalize known pool aliases without cutting namespaced model IDs at '/'."""
    key = canonical_model_id(raw).lower()
    if " / " in key:
        return normalize_pool(key)
    if "/" in key:
        left, right = (part.strip() for part in key.split("/", 1))
        left_pool = POOL_ALIASES.get(left)
        right_pool = POOL_ALIASES.get(right)
        if left_pool is not None and right_pool == left_pool:
            return left_pool
    return POOL_ALIASES.get(key, key)


def lane_key(model, effort, pool):
    return canonical_model_id(model).lower(), effort.lower(), pool


def parse_authorized_lanes(profile):
    """Read the explicit lane declarations from a project profile, if present."""
    if PROFILE_MARKER not in profile:
        return None
    if profile.count(PROFILE_MARKER) != 1:
        raise ValueError("Project profile requires exactly one orchestration-lanes:v1 marker.")
    match = PROFILE_LANES_RE.match(profile.split(PROFILE_MARKER, 1)[1].lstrip())
    if not match:
        raise ValueError("Place a fenced JSON lane array immediately after the orchestration-lanes:v1 marker.")
    try:
        rows = json.loads(match.group(1))
    except (json.JSONDecodeError, RecursionError) as err:
        raise ValueError(f"Invalid authorized lane JSON in project profile: {err}") from err
    if not isinstance(rows, list):
        raise ValueError("Authorized lanes must be a JSON array in the project profile.")

    lanes = {}
    for index, row in enumerate(rows, 1):
        if (
            not isinstance(row, dict)
            or not REQUIRED_LANE_FIELDS.issubset(row)
            or row.keys() - REQUIRED_LANE_FIELDS - {"restricted_data"}
        ):
            raise ValueError(f"Authorized lane {index} requires model, effort, pool, runner and roles.")
        for field in ("model", "effort", "pool"):
            pattern = POOL_ID if field == "pool" else LANE_ID
            if not isinstance(row[field], str) or not pattern.fullmatch(row[field]):
                raise ValueError(f"Authorized lane {index} has an invalid {field} ID.")
        runner = row["runner"]
        if not isinstance(runner, str) or not runner.strip() or any(ord(char) < 32 or ord(char) == 127 for char in runner):
            raise ValueError(f"Authorized lane {index} requires a runner name on one line.")
        roles = row["roles"]
        if (
            not isinstance(roles, list)
            or not roles
            or not all(isinstance(role, str) and role in ROLES for role in roles)
            or len(set(roles)) != len(roles)
        ):
            raise ValueError(f"Authorized lane {index} requires a non-empty list of unique supported roles.")
        restricted = row.get("restricted_data", False)
        if type(restricted) is not bool:
            raise ValueError(f"Authorized lane {index} requires a boolean restricted_data permission.")
        key = lane_key(row["model"], row["effort"], normalize_pool(row["pool"]))
        if key in lanes:
            raise ValueError(f"Duplicate authorized lane for {row['model']} at {row['effort']} in {row['pool']}.")
        lanes[key] = {**row, "runner": runner.strip(), "restricted_data": restricted}
    return lanes


def infer_provider_from_model(model_name):
    """Best-effort provider inference when a historical table omits the Provider column."""
    low = model_name.strip().lower()
    if _ANTHROPIC_RE.search(low):
        return "anthropic"
    if _OPENAI_RE.search(low):
        return "openai"
    if _GOOGLE_RE.search(low):
        return "google"
    if _DEEPSEEK_RE.search(low):
        return "deepseek"
    if _ZHIPU_RE.search(low):
        return "zhipu"
    if _ALIBABA_RE.search(low):
        return "alibaba"
    return "unknown"


def parse_iso_utc(raw, field_name="timestamp"):
    """Parse an ISO-8601 timestamp into timezone-aware UTC (Python 3.9+ compatible)."""
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError(f"{field_name} must be a non-empty ISO-8601 string.")
    text = raw.strip()
    if text.endswith(("Z", "z")):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except (ValueError, OverflowError) as err:
        raise ValueError(f"Invalid ISO-8601 {field_name}: {raw!r}") from err


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
    raw_num, rest = match.group(1), match.group(2)
    if BAD_NUMBER_TAIL_RE.match(rest) or RANGE_SUFFIX_RE.match(rest):
        return None
    value = float(raw_num.replace(",", ""))
    if not math.isfinite(value):
        return None
    return 0.0 if value == 0.0 else value


def _strip_enclosing_backticks(text):
    text = text.strip()
    if len(text) >= 2 and text.startswith("`") and text.endswith("`") and "`" not in text[1:-1]:
        return text[1:-1].strip()
    return text


def parse_model_and_effort(cell):
    """Extract (model_name, effort) from routing-reference or profile-average table cells."""
    text = cell.strip()
    if len(text) >= 2 and text.startswith("`") and text.endswith("`") and "`" not in text[1:-1]:
        inner = text[1:-1].strip()
        if "/" in inner and "(" not in inner and " " not in inner:
            model_part, effort_part = inner.rsplit("/", 1)
            if effort_part.strip().lower() in KNOWN_EFFORTS:
                return model_part.strip(), effort_part.strip().lower()
        return inner, "default"

    bt_match = BACKTICK_EFFORT_RE.match(text)
    if bt_match and bt_match.group(1).strip():
        return _strip_enclosing_backticks(bt_match.group(1)), bt_match.group(2).strip().lower()

    if "/" in text and "(" not in text and " " not in text:
        model_part, effort_part = text.rsplit("/", 1)
        if effort_part.strip().lower() in KNOWN_EFFORTS:
            return _strip_enclosing_backticks(model_part), effort_part.strip().lower()

    paren_match = PAREN_EFFORT_RE.match(text)
    if paren_match:
        model_part = _strip_enclosing_backticks(paren_match.group(1))
        inner = paren_match.group(2).strip()
        low_inner = inner.lower()
        if low_inner in KNOWN_EFFORTS:
            return model_part, low_inner
        if "highest effort" in low_inner:
            return model_part, "max"
        return model_part, "unspecified"

    return _strip_enclosing_backticks(text), "unspecified"


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
        latency_cell = cells[latency_idx] if latency_idx is not None else ""
        latency_s = parse_number(latency_cell)
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
                "latency_kind": "estimate" if "*" in latency_cell else "measured",
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
    if WORKSPACE_DELIMITER in markdown_text:
        if markdown_text.count(WORKSPACE_DELIMITER) > 1:
            raise ValueError("Measurements file contains multiple workspace-measurements:v1 delimiters.")
        section = markdown_text.split(WORKSPACE_DELIMITER, 1)[1]
    else:
        section = markdown_text
    starts = OBSERVATIONS_START_RE.findall(section)
    if len(starts) > 1:
        raise ValueError("Measurements file contains multiple observations:start blocks.")
    match = OBSERVATIONS_RE.search(section)
    if not match:
        if starts:
            raise ValueError("Malformed observations block in measurements file.")
        return []
    raw_json = match.group(1).strip()
    try:
        payload = json.loads(raw_json)
    except (json.JSONDecodeError, RecursionError) as err:
        raise ValueError(f"Malformed observations JSON block in measurements file: {err}") from err
    if not isinstance(payload, dict):
        raise ValueError("Observations JSON block must be a JSON object.")

    payload.pop("catalog_audit", None)
    try:
        data = normalize(payload)
    except (TypeError, OverflowError) as err:
        raise ValueError(f"Invalid workspace observations: {err}") from err
    display_models = {}
    model_providers = {}
    for row in data["models"]:
        mkey = row["model"].lower()
        display_models.setdefault(mkey, row["model"])
        model_providers[mkey] = row["provider"]
    variants = set()
    for row in data["benchmark_checks"]:
        mkey = row["model"].lower()
        display_models.setdefault(mkey, row["model"])
        variants.add((mkey, row["effort"].lower()))

    # Retain the exact cohort, unit, and dated source observations. An agent may
    # append distinct valid benchmarks for one model without changing its scale.
    observations = defaultdict(lambda: defaultdict(dict))
    for row in data["measurements"]:
        mkey = row["model"].lower()
        display_models.setdefault(mkey, row["model"])
        variant = mkey, row["effort"].lower()
        variants.add(variant)
        metric = row["metric"].lower()
        if metric in LATENCY_METRICS:
            metric = "seconds-per-task"
        elif metric in ESTIMATED_LATENCY_METRICS:
            metric = "estimated-seconds-per-task"
        elif metric in INDEX_METRICS:
            metric = "index"
        else:
            metric = PROFILE_METRIC_ALIASES.get(metric, metric)
        if metric not in (*PROFILE_METRIC_ALIASES.values(), "seconds-per-task", "estimated-seconds-per-task", "index"):
            continue
        sources = observations[variant][metric].setdefault((row["cohort"].lower(), row["unit"]), {})
        source_key = row["source"].lower()
        prior = sources.get(source_key)
        if prior is None or row["date"] >= prior["date"]:
            sources[source_key] = row

    represented_models = {mkey for mkey, _ in variants}
    variants.update((mkey, "unspecified") for mkey in model_providers.keys() - represented_models)
    candidates = []
    for mkey, effort in sorted(variants, key=lambda pair: (display_models[pair[0]], pair[1])):
        model = display_models[mkey]
        raw_provider = model_providers.get(mkey) or infer_provider_from_model(model)
        candidates.append(
            {
                "model": model,
                "effort": effort,
                "pool": normalize_pool(raw_provider),
                "family": normalize_family(raw_provider),
                "provider_label": raw_provider or "unknown",
                "profiles": dict.fromkeys(ROLES[:-1]),
                "review_override": None,
                "latency_s": None,
                "index": None,
                "source": "workspace",
                "observations": observations[(mkey, effort)],
            }
        )
    return candidates


def _copy_candidate(item):
    copied = dict(item)
    if "profiles" in item and isinstance(item["profiles"], dict):
        copied["profiles"] = dict(item["profiles"])
    if "observations" in item and isinstance(item["observations"], dict):
        copied_obs = {}
        for metric, groups in item["observations"].items():
            copied_groups = {}
            for (cohort, unit), sources in groups.items():
                norm_group = (cohort.lower(), unit)
                target = copied_groups.setdefault(norm_group, {})
                for source, row in sources.items():
                    source_key = source.lower()
                    prev = target.get(source_key)
                    if prev is None or row["date"] >= prev["date"]:
                        target[source_key] = dict(row)
            copied_obs[metric] = copied_groups
        copied["observations"] = copied_obs
    return copied


def merge_candidates(historical, workspace):
    """Join matching variants while keeping historical and live evidence separate."""
    merged = {lane_key(item["model"], item["effort"], item["pool"]): _copy_candidate(item) for item in historical}
    for item in workspace:
        key = lane_key(item["model"], item["effort"], item["pool"])
        existing = merged.get(key)
        if existing is None:
            merged[key] = _copy_candidate(item)
            continue
        observations = existing.setdefault("observations", {})
        for metric, groups in item.get("observations", {}).items():
            for (cohort, unit), sources in groups.items():
                existing_sources = observations.setdefault(metric, {}).setdefault((cohort.lower(), unit), {})
                for source, row in sources.items():
                    source_key = source.lower()
                    previous = existing_sources.get(source_key)
                    if previous is None or row["date"] >= previous["date"]:
                        existing_sources[source_key] = dict(row)
    return list(merged.values())


def _groups(candidate, metric, unit):
    grouped = {}
    for (cohort, observed_unit), values in candidate.get("observations", {}).get(metric, {}).items():
        if observed_unit != unit:
            continue
        bucket = grouped.setdefault(cohort.lower(), {})
        for source, row in values.items():
            source_key = source.lower()
            prior = bucket.get(source_key)
            if prior is None or row["date"] >= prior["date"]:
                bucket[source_key] = row
    return grouped


def _role_cohorts(candidate, role):
    if role != "review":
        return _groups(candidate, role, "points").keys()
    direct = _groups(candidate, "review", "points").keys()
    accuracy = _groups(candidate, "accuracy", "points").keys()
    reasoning = _groups(candidate, "reasoning", "points").keys()
    return direct | (accuracy & reasoning)


def _mean(sources):
    return statistics.fmean(row["value"] for _, row in sorted(sources.items())) if sources else None


def _matched_sources(evidence):
    return set.intersection(*(set(rows) for rows in evidence)) if evidence else set()


def _select_comparable_group(evidence, metrics, same_family_flags=None):
    """Find the largest subset of represented candidates sharing non-empty source intersections."""
    represented = [idx for idx, row in enumerate(evidence) if all(row[metric] for metric in metrics)]
    if not represented:
        return [], {metric: set() for metric in (*metrics, "knowledge")}, []

    if len(represented) == 1:
        idx = represented[0]
        matched = {metric: set(evidence[idx][metric]) for metric in (*metrics, "knowledge")}
        return [idx], matched, []

    seen_groups = set()
    best_rank = None
    best_group = None
    best_matched = None

    if len(metrics) == 1:
        metric = metrics[0]
        all_sources = sorted(set().union(*(evidence[idx][metric].keys() for idx in represented)))
        candidate_groups = (
            tuple(idx for idx in represented if source in evidence[idx][metric])
            for source in all_sources
        )
    else:
        m0, m1 = metrics
        pairs = sorted({
            (s0, s1)
            for idx in represented
            for s0 in evidence[idx][m0]
            for s1 in evidence[idx][m1]
        })
        candidate_groups = (
            tuple(idx for idx in represented if s0 in evidence[idx][m0] and s1 in evidence[idx][m1])
            for s0, s1 in pairs
        )

    for group in candidate_groups:
        if len(group) < 2 or group in seen_groups:
            continue
        seen_groups.add(group)
        matched = {
            metric: _matched_sources([evidence[idx][metric] for idx in group])
            for metric in (*metrics, "knowledge")
        }
        if not all(matched[metric] for metric in metrics):
            continue
        if same_family_flags is not None:
            cross_count = sum(1 for idx in group if not same_family_flags[idx])
            has_cross = cross_count > 0
            cross_priority = (0 if has_cross else 1, -len(group), -cross_count)
        else:
            cross_priority = (0, -len(group), 0)
        rank = (
            *cross_priority,
            -sum(len(matched[metric]) for metric in metrics),
            -len(matched["knowledge"]),
            tuple(tuple(sorted(matched[metric])) for metric in metrics),
            tuple(sorted(matched["knowledge"])),
            group,
        )
        if best_rank is None or rank < best_rank:
            best_rank = rank
            best_group = list(group)
            best_matched = matched

    if best_group is None:
        return [], {metric: set() for metric in (*metrics, "knowledge")}, []

    comparable_set = set(best_group)
    outliers = [idx for idx in represented if idx not in comparable_set]
    return best_group, best_matched, outliers


def _shared_role_evidence(candidates, cohort, role, same_family_flags=None):
    """Choose one common scoring rubric and largest comparable source-matched group."""
    cohort_key = cohort.lower()

    def evaluate(metrics):
        evidence = [
            {metric: _groups(c, metric, "points").get(cohort_key, {}) for metric in (*metrics, "knowledge")}
            for c in candidates
        ]
        comparable, matched, outliers = _select_comparable_group(
            evidence, metrics, same_family_flags=same_family_flags
        )
        return metrics, evidence, comparable, matched, outliers

    if role == "review":
        ar_res = evaluate(("accuracy", "reasoning"))
        rev_res = evaluate(("review",))
        ar_comp = ar_res[2]
        rev_comp = rev_res[2]
        if same_family_flags is not None:
            ar_has_cross = any(not same_family_flags[idx] for idx in ar_comp)
            rev_has_cross = any(not same_family_flags[idx] for idx in rev_comp)
            if ar_comp and (not rev_comp or (ar_has_cross, len(ar_comp)) >= (rev_has_cross, len(rev_comp))):
                return ar_res
            if rev_comp:
                return rev_res
        else:
            if ar_comp and len(ar_comp) >= len(rev_comp):
                return ar_res
            if rev_comp:
                return rev_res
        return ar_res if any(row["accuracy"] and row["reasoning"] for row in ar_res[1]) else rev_res

    return evaluate((role,))


def _workspace_projection(candidate, cohort):
    """Render profiles from one cohort, and keep timing provenance for tie breaks."""
    cohort_key = cohort.lower() if cohort is not None else None
    profiles = {
        metric: _mean(_groups(candidate, metric, "points").get(cohort_key))
        for metric in ROLES[:-1]
    }
    latency_kind = None
    latency_cohort = None
    latency = None
    latency_sources = ()
    for metric, kind in (("seconds-per-task", "measured"), ("estimated-seconds-per-task", "estimate")):
        groups = _groups(candidate, metric, "seconds")
        if cohort_key is not None and cohort_key in groups:
            latency_cohort = cohort_key
            evidence = groups[cohort_key]
            latency = _mean(evidence)
            latency_sources = tuple(sorted(evidence))
            latency_kind = kind
            break
        if len(groups) == 1:
            latency_cohort, evidence = next(iter(groups.items()))
            latency = _mean(evidence)
            latency_sources = tuple(sorted(evidence))
            latency_kind = kind
            break
        if groups:
            break
    return {
        "profiles": profiles,
        "review_override": None,
        "latency_s": latency,
        "latency_kind": latency_kind,
        "latency_cohort": latency_cohort,
        "latency_sources": latency_sources,
        "index": _mean(_groups(candidate, "index", "points").get(cohort_key)),
        "source": "workspace" if candidate.get("observations") else candidate["source"],
    }


def _score_candidates(eligible, role, requested_cohort, warnings, norm_author=None):
    """Project eligible lanes into one comparable benchmark domain."""
    candidates = [item.pop("_candidate") for item in eligible]
    cohorts = sorted(set().union(*(_role_cohorts(candidate, role) for candidate in candidates)))
    requested_key = requested_cohort.lower() if requested_cohort is not None else None
    cohort = requested_key or (cohorts[0] if len(cohorts) == 1 else None)
    if requested_cohort is None and len(cohorts) > 1:
        warnings.append(
            f"Multiple live {role} cohorts ({', '.join(cohorts)}); using historical scores where available. "
            "Pass --cohort to select one comparable live cohort."
        )
    if cohort is None:
        return _score_candidates_from_history(eligible, candidates, role)

    same_family_flags = (
        [item["same_family"] for item in eligible]
        if role == "review" and norm_author and any(not item["same_family"] for item in eligible)
        else None
    )
    metrics, evidence, comparable, matched, outliers = _shared_role_evidence(
        candidates, cohort, role, same_family_flags=same_family_flags
    )
    display_cohort = requested_cohort if requested_cohort is not None else cohort
    if not comparable or not all(matched[metric] for metric in metrics):
        warnings.append(f"No matched {role} observations in live cohort '{display_cohort}'.")
        if requested_cohort is None:
            return _score_candidates_from_history(eligible, candidates, role)

    comparable_set = set(comparable)

    if role == "review" and norm_author and comparable_set:
        has_cross_family = any(not item["same_family"] for item in eligible)
        has_measured_cross = any(not eligible[idx]["same_family"] for idx in comparable_set)
        if has_cross_family and not has_measured_cross:
            if requested_cohort is None and any(
                not item["same_family"] and role_score(cand, role) is not None
                for item, cand in zip(eligible, candidates)
            ):
                warnings.append(
                    f"Live cohort '{cohort}' has only same-family review scores for author family '{norm_author}'; "
                    "falling back to historical scores so cross-family reviewers can be compared."
                )
                return _score_candidates_from_history(eligible, candidates, role)
            warnings.append(
                f"Live cohort '{display_cohort}' has no measured cross-family reviewers for author family '{norm_author}'; "
                "same-family lane cannot be recommended ahead of unmeasured cross-family reviewers."
            )

    if outliers:
        outlier_labels = ", ".join(
            f"{eligible[idx]['model']} ({eligible[idx]['effort']})" for idx in outliers
        )
        shared_sources = ", ".join(sorted(set().union(*(matched[metric] for metric in metrics))))
        warnings.append(
            f"Live cohort '{cohort}' excluded unshared-source {role} observations for {outlier_labels} "
            f"(scoring on shared source(s): {shared_sources})."
        )

    for idx, (item, candidate, row) in enumerate(zip(eligible, candidates, evidence)):
        projection = _workspace_projection(candidate, cohort)
        if idx in comparable_set:
            for metric in metrics:
                common = {source: row[metric][source] for source in matched[metric]}
                if metric == "review":
                    projection["review_override"] = _mean(common)
                else:
                    projection["profiles"][metric] = _mean(common)
            if metrics == ("accuracy", "reasoning"):
                common = {source: row["knowledge"][source] for source in matched["knowledge"]}
                projection["profiles"]["knowledge"] = _mean(common)
            score = role_score(projection, role)
        else:
            score = None
        item.update(projection, score=score)
    basis = "workspace" if any(item["score"] is not None for item in eligible) else "unavailable"
    reported_cohort = cohort if basis == "workspace" else display_cohort
    return basis, reported_cohort, {"metrics": metrics, "matched": matched, "drop_knowledge": False}


def _score_candidates_from_history(eligible, candidates, role):
    drop_knowledge = False
    if role == "review":
        review_measured = [
            cand for cand in candidates
            if cand.get("review_override") is None
            and cand["profiles"].get("accuracy") is not None
            and cand["profiles"].get("reasoning") is not None
        ]
        has_know = any(cand["profiles"].get("knowledge") is not None for cand in review_measured)
        missing_know = any(cand["profiles"].get("knowledge") is None for cand in review_measured)
        drop_knowledge = has_know and missing_know

    for item, candidate in zip(eligible, candidates):
        item.update(
            score=role_score(candidate, role, ignore_knowledge=drop_knowledge),
            latency_kind=candidate.get("latency_kind", "measured"),
            latency_cohort=None,
        )
    basis = "historical" if any(item["score"] is not None for item in eligible) else "unavailable"
    return basis, None, {"metrics": None, "matched": None, "drop_knowledge": drop_knowledge}


def _score_excluded(excluded, role, score_basis, score_cohort, score_meta):
    """Align excluded lane scores with the active scoring domain."""
    for item in excluded:
        cand = item.pop("_candidate")
        if score_basis == "workspace" and score_cohort is not None:
            cohort_key = score_cohort.lower()
            metrics = score_meta["metrics"]
            matched = score_meta["matched"]
            row = {
                metric: _groups(cand, metric, "points").get(cohort_key, {})
                for metric in (*metrics, "knowledge")
            }
            if all(matched[metric] and matched[metric].issubset(row[metric]) for metric in metrics):
                projection = _workspace_projection(cand, cohort_key)
                for metric in metrics:
                    common = {source: row[metric][source] for source in matched[metric]}
                    if metric == "review":
                        projection["review_override"] = _mean(common)
                    else:
                        projection["profiles"][metric] = _mean(common)
                if metrics == ("accuracy", "reasoning"):
                    if matched["knowledge"]:
                        if not matched["knowledge"].issubset(row["knowledge"]):
                            item["score"] = None
                            continue
                        common = {source: row["knowledge"][source] for source in matched["knowledge"]}
                        projection["profiles"]["knowledge"] = _mean(common)
                    else:
                        projection["profiles"]["knowledge"] = None
                item["score"] = role_score(projection, role)
                item["source"] = "workspace"
            else:
                item["score"] = None
        elif score_cohort is not None:
            item["score"] = None
        else:
            item["score"] = role_score(cand, role, ignore_knowledge=score_meta["drop_knowledge"])


def _effective_headroom(item):
    if item.get("unit_size") is not None:
        return item.get("projected_headroom_pct")
    return item.get("headroom")


def _shared_latencies(eligible):
    """Use timings only when the lanes tied on pre-latency sort keys all have matched measurements."""
    tied = defaultdict(list)
    for item in eligible:
        key = (
            item.get("same_family", False),
            item.get("deprioritized", False),
            item.get("stale", False),
            _effective_headroom(item),
            item["score"],
        )
        tied[key].append(item)

    for (*_, score), items in tied.items():
        cohorts = {
            (item["latency_cohort"], item.get("latency_sources", ()))
            for item in items
        }
        comparable = score is not None and len(cohorts) == 1 and all(
            item["latency_s"] is not None and item["latency_kind"] == "measured" for item in items
        )
        for item in items:
            item["_comparable_latency"] = item["latency_s"] if comparable else float("inf")


def _optional_pct(entry, field):
    value = entry.get(field)
    if value is None:
        return None
    if type(value) not in (int, float):
        raise ValueError(f"Provider state field '{field}' must be a finite number or null.")
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError(f"Provider state field '{field}' must be a finite number or null.")
    if value < 0 or value > 100:
        raise ValueError(f"Provider state field '{field}' must be between 0 and 100 (got {value}).")
    result = float(value)
    return 0.0 if result == 0.0 else result


def _optional_limit(entry, pool):
    value = entry.get("limit")
    if value is None:
        return None
    if (
        not isinstance(value, str)
        or len(value) > MAX_LIMIT_LEN
        or "|" in value
        or any(ord(ch) < 32 or ord(ch) == 127 for ch in value)
    ):
        raise ValueError(
            f"Provider '{pool}' field 'limit' must be null or a single-line string (<= {MAX_LIMIT_LEN} chars, no '|')."
        )
    cleaned = value.strip()
    return cleaned or None


def _fmt_pct(pct):
    val = float(pct)
    return str(int(val)) if val.is_integer() else str(val)


def _fmt_proj_num(val):
    num = float(val)
    if num == 0.0:
        num = 0.0
    if round(num, 1) == num:
        return f"{num:.1f}"
    return f"{num:.2f}".rstrip("0").rstrip(".")


def _validate_stale_minutes(stale_minutes):
    if type(stale_minutes) is not int or stale_minutes < 0:
        raise ValueError(f"stale_minutes must be a non-negative integer (got {stale_minutes!r}).")
    return stale_minutes


def _validate_unit_size(unit_size):
    if not isinstance(unit_size, str):
        raise ValueError(f"unit_size must be one of {', '.join(UNIT_SIZES)} (got {unit_size!r}).")
    norm = unit_size.strip().lower()
    if norm not in UNIT_SIZE_MULTIPLIERS:
        raise ValueError(f"unit_size must be one of {', '.join(UNIT_SIZES)} (got {unit_size!r}).")
    return norm


def _validate_safety_margin(safety_margin):
    if type(safety_margin) not in (int, float):
        raise ValueError(
            f"safety_margin must be a finite number between {SAFETY_MARGIN_MIN_OVERRIDE:g} "
            f"and {SAFETY_MARGIN_MAX_OVERRIDE:g} (got {safety_margin!r})."
        )
    try:
        val = float(safety_margin)
    except OverflowError as err:
        raise ValueError(f"safety_margin is out of range: {safety_margin!r}") from err
    if not math.isfinite(val) or val < SAFETY_MARGIN_MIN_OVERRIDE or val > SAFETY_MARGIN_MAX_OVERRIDE:
        raise ValueError(
            f"safety_margin must be between {SAFETY_MARGIN_MIN_OVERRIDE:g} "
            f"and {SAFETY_MARGIN_MAX_OVERRIDE:g} (got {safety_margin!r})."
        )
    return round(val, 4)


def _validate_pct_value(value, field_name):
    if type(value) not in (int, float):
        raise ValueError(f"{field_name} must be a finite number between 0 and 100 (got {value!r}).")
    try:
        num = float(value)
    except OverflowError as err:
        raise ValueError(f"{field_name} is out of range: {value!r}") from err
    if not math.isfinite(num) or num < 0.0 or num > 100.0:
        raise ValueError(f"{field_name} must be between 0 and 100 (got {value!r}).")
    return 0.0 if num == 0.0 else num


def _validate_nonneg_float(value, field_name, *, max_value=None):
    if type(value) not in (int, float):
        raise ValueError(f"{field_name} must be a finite non-negative number (got {value!r}).")
    try:
        num = float(value)
    except OverflowError as err:
        raise ValueError(f"{field_name} is out of range: {value!r}") from err
    if not math.isfinite(num) or num < 0.0:
        raise ValueError(f"{field_name} must be a finite non-negative number (got {value!r}).")
    if max_value is not None and num > max_value:
        raise ValueError(f"{field_name} must be <= {max_value} (got {value!r}).")
    return 0.0 if num == 0.0 else num


def _validate_nonneg_int(value, field_name):
    if type(value) is not int or value < 0:
        raise ValueError(f"{field_name} must be a non-negative integer (got {value!r}).")
    return value


def model_burn_weight(model, effort="medium"):
    """Deterministic burn multiplier for cold-start and pool-level estimation."""
    low_model = (model or "").strip().lower()
    low_effort = (effort or "medium").strip().lower()
    tokens = set(re.findall(r"[a-z0-9]+", low_model))
    if "mythos" in tokens or "fable" in tokens:
        return 1.7
    if "astra" in tokens:
        return 1.6
    if "opus" in tokens and low_effort in ("high", "xhigh", "max"):
        return 1.2
    if "sol" in tokens and low_effort in ("xhigh", "max"):
        return 1.2
    if "sonnet" in tokens:
        return 0.65
    if "hydrogen" in tokens:
        return 0.55
    if "terra" in tokens or "luna" in tokens:
        return 0.5
    if "haiku" in tokens or "flash" in tokens:
        return 0.25
    return 1.0


def calibration_lane_key(provider, model, effort="medium"):
    """Canonical lowercased calibration lane key '<provider>/<model>/<effort>'."""
    pool = normalize_pool(provider)
    canon_model = canonical_model_id(str(model)).lower()
    norm_effort = str(effort or "medium").strip().lower() or "medium"
    return f"{pool}/{canon_model}/{norm_effort}"


def _parse_calibration_lane_key(raw_key):
    if not isinstance(raw_key, str) or not raw_key.strip():
        raise ValueError(f"Invalid calibration lane key: {raw_key!r}.")
    text = raw_key.strip()
    first = text.find("/")
    last = text.rfind("/")
    if first <= 0 or last <= first + 1 or last >= len(text) - 1:
        raise ValueError(
            f"Calibration lane key {raw_key!r} must use '<provider>/<model>/<effort>' format."
        )
    provider_part = text[:first].strip()
    model_part = text[first + 1 : last].strip()
    effort_part = text[last + 1 :].strip()
    if not provider_part or not model_part or not effort_part:
        raise ValueError(
            f"Calibration lane key {raw_key!r} must use '<provider>/<model>/<effort>' format."
        )
    return calibration_lane_key(provider_part, model_part, effort_part)


def empty_calibration():
    """Return a fresh empty calibration structure."""
    return {
        "version": CALIBRATION_VERSION,
        "alpha": CALIBRATION_ALPHA,
        "lanes": {},
        "pools": {},
    }


def parse_calibration(raw_state):
    """Extract and validate optional '_calibration' section from raw provider-state dict."""
    if raw_state is None:
        return empty_calibration()
    if not isinstance(raw_state, dict):
        raise ValueError("provider-state.json must contain a JSON object.")
    raw_cal = raw_state.get(CALIBRATION_KEY)
    if raw_cal is None:
        return empty_calibration()
    if not isinstance(raw_cal, dict):
        raise ValueError(f"'{CALIBRATION_KEY}' must be a JSON object.")

    version = raw_cal.get("version", CALIBRATION_VERSION)
    if type(version) is not int or version != CALIBRATION_VERSION:
        raise ValueError(
            f"'{CALIBRATION_KEY}.version' must be integer {CALIBRATION_VERSION} (got {version!r})."
        )

    alpha_raw = raw_cal.get("alpha", CALIBRATION_ALPHA)
    if type(alpha_raw) not in (int, float) or not math.isfinite(float(alpha_raw)):
        raise ValueError(f"'{CALIBRATION_KEY}.alpha' must be a finite number in (0, 1].")
    alpha = float(alpha_raw)
    if alpha <= 0.0 or alpha > 1.0:
        raise ValueError(f"'{CALIBRATION_KEY}.alpha' must be in (0, 1] (got {alpha_raw!r}).")

    raw_lanes = raw_cal.get("lanes", {})
    if not isinstance(raw_lanes, dict):
        raise ValueError(f"'{CALIBRATION_KEY}.lanes' must be a JSON object.")

    lanes = {}
    for raw_key, entry in raw_lanes.items():
        if not isinstance(entry, dict):
            raise ValueError(f"Calibration lane entry for {raw_key!r} must be a JSON object.")
        norm_key = _parse_calibration_lane_key(raw_key)
        if norm_key in lanes:
            raise ValueError(f"Conflicting calibration lane entries normalize to '{norm_key}'.")

        samples = _validate_nonneg_int(entry.get("samples", 0), f"{CALIBRATION_KEY}.lanes[{raw_key}].samples")
        five_hour_per_m = (
            _validate_nonneg_float(
                entry["five_hour_per_m"], f"{CALIBRATION_KEY}.lanes[{raw_key}].five_hour_per_m"
            )
            if entry.get("five_hour_per_m") is not None
            else None
        )
        weekly_per_m = (
            _validate_nonneg_float(
                entry["weekly_per_m"], f"{CALIBRATION_KEY}.lanes[{raw_key}].weekly_per_m"
            )
            if entry.get("weekly_per_m") is not None
            else None
        )
        max_ratio_raw = entry.get("max_ratio", 1.0)
        max_ratio = (
            _validate_nonneg_float(max_ratio_raw, f"{CALIBRATION_KEY}.lanes[{raw_key}].max_ratio")
            if max_ratio_raw is not None
            else 1.0
        )

        raw_by_size = entry.get("by_size", {})
        if not isinstance(raw_by_size, dict):
            raise ValueError(f"'{CALIBRATION_KEY}.lanes[{raw_key}].by_size' must be a JSON object.")
        by_size = {}
        for raw_size, size_entry in raw_by_size.items():
            norm_size = _validate_unit_size(raw_size)
            if norm_size in by_size:
                raise ValueError(f"Duplicate by_size key '{norm_size}' in calibration lane '{norm_key}'.")
            if not isinstance(size_entry, dict):
                raise ValueError(
                    f"'{CALIBRATION_KEY}.lanes[{raw_key}].by_size[{raw_size}]' must be a JSON object."
                )
            bs_samples = _validate_nonneg_int(
                size_entry.get("samples", 0),
                f"{CALIBRATION_KEY}.lanes[{raw_key}].by_size[{raw_size}].samples",
            )
            bs_5h = (
                _validate_pct_value(
                    size_entry["five_hour_pct"],
                    f"{CALIBRATION_KEY}.lanes[{raw_key}].by_size[{raw_size}].five_hour_pct",
                )
                if size_entry.get("five_hour_pct") is not None
                else None
            )
            bs_wk = (
                _validate_pct_value(
                    size_entry["weekly_pct"],
                    f"{CALIBRATION_KEY}.lanes[{raw_key}].by_size[{raw_size}].weekly_pct",
                )
                if size_entry.get("weekly_pct") is not None
                else None
            )
            by_size[norm_size] = {
                "samples": bs_samples,
                "five_hour_pct": bs_5h,
                "weekly_pct": bs_wk,
            }

        updated_at = entry.get("updated_at")
        if updated_at is not None:
            updated_at = format_iso_utc(
                parse_iso_utc(updated_at, f"{CALIBRATION_KEY}.lanes[{raw_key}].updated_at")
            )

        lanes[norm_key] = {
            "samples": samples,
            "five_hour_per_m": five_hour_per_m,
            "weekly_per_m": weekly_per_m,
            "max_ratio": max_ratio,
            "by_size": by_size,
            "updated_at": updated_at,
        }

    raw_pools = raw_cal.get("pools", {})
    if not isinstance(raw_pools, dict):
        raise ValueError(f"'{CALIBRATION_KEY}.pools' must be a JSON object.")

    pools = {}
    for raw_pool, entry in raw_pools.items():
        if not isinstance(raw_pool, str) or not raw_pool.strip() or not isinstance(entry, dict):
            raise ValueError(f"Calibration pool entry for {raw_pool!r} must be a JSON object.")
        norm_pool = normalize_pool(raw_pool)
        if norm_pool == "unknown":
            raise ValueError(f"Invalid calibration pool key: {raw_pool!r}.")
        if norm_pool in pools:
            raise ValueError(f"Conflicting calibration pool entries normalize to '{norm_pool}'.")

        samples = _validate_nonneg_int(entry.get("samples", 0), f"{CALIBRATION_KEY}.pools[{raw_pool}].samples")
        five_hour_per_m = (
            _validate_nonneg_float(
                entry["five_hour_per_m"], f"{CALIBRATION_KEY}.pools[{raw_pool}].five_hour_per_m"
            )
            if entry.get("five_hour_per_m") is not None
            else None
        )
        weekly_per_m = (
            _validate_nonneg_float(
                entry["weekly_per_m"], f"{CALIBRATION_KEY}.pools[{raw_pool}].weekly_per_m"
            )
            if entry.get("weekly_per_m") is not None
            else None
        )
        max_ratio_raw = entry.get("max_ratio", 1.0)
        max_ratio = (
            _validate_nonneg_float(max_ratio_raw, f"{CALIBRATION_KEY}.pools[{raw_pool}].max_ratio")
            if max_ratio_raw is not None
            else 1.0
        )
        updated_at = entry.get("updated_at")
        if updated_at is not None:
            updated_at = format_iso_utc(
                parse_iso_utc(updated_at, f"{CALIBRATION_KEY}.pools[{raw_pool}].updated_at")
            )

        pools[norm_pool] = {
            "samples": samples,
            "five_hour_per_m": five_hour_per_m,
            "weekly_per_m": weekly_per_m,
            "max_ratio": max_ratio,
            "updated_at": updated_at,
        }

    return {
        "version": version,
        "alpha": alpha,
        "lanes": lanes,
        "pools": pools,
    }


def _auto_safety_margin(samples, max_ratio):
    if samples <= 0:
        return SAFETY_MARGIN_COLD
    if samples < 3:
        return SAFETY_MARGIN_LOW_SAMPLES
    bounded = min(SAFETY_MARGIN_MAX_AUTO, max(SAFETY_MARGIN_MIN_AUTO, float(max_ratio or 1.0)))
    return round(bounded, 2)


def estimate_burn(
    provider,
    model,
    effort,
    unit_size,
    *,
    calibration=None,
    safety_margin=None,
):
    """Estimate five-hour and weekly quota burn for one unit using calibration or cold-start priors."""
    norm_size = _validate_unit_size(unit_size)
    margin_override = _validate_safety_margin(safety_margin) if safety_margin is not None else None
    pool = normalize_pool(provider)
    mult = UNIT_SIZE_MULTIPLIERS[norm_size]
    weight = model_burn_weight(model, effort)
    defaults = DEFAULT_BURN_PER_M.get(pool, FALLBACK_BURN_PER_M)
    cold = {
        "five_hour_pct": defaults["five_hour_pct"] * weight * mult,
        "weekly_pct": defaults["weekly_pct"] * weight * mult,
    }

    cal = calibration if isinstance(calibration, dict) else empty_calibration()
    cal_lanes = cal.get("lanes") or {}
    cal_pools = cal.get("pools") or {}

    lkey = calibration_lane_key(pool, model, effort)
    lane_entry = cal_lanes.get(lkey)
    pool_entry = cal_pools.get(pool)

    has_pool = bool(
        isinstance(pool_entry, dict)
        and pool_entry.get("samples", 0) > 0
        and (
            pool_entry.get("five_hour_per_m") is not None
            or pool_entry.get("weekly_per_m") is not None
        )
    )

    def pool_or_cold(pct_field, per_m_field):
        if has_pool and pool_entry.get(per_m_field) is not None:
            return pool_entry[per_m_field] * weight * mult
        return cold[pct_field]

    by_size_entry = (
        (lane_entry.get("by_size") or {}).get(norm_size)
        if isinstance(lane_entry, dict)
        else None
    )
    has_by_size = bool(
        isinstance(by_size_entry, dict)
        and by_size_entry.get("samples", 0) > 0
        and (
            by_size_entry.get("five_hour_pct") is not None
            or by_size_entry.get("weekly_pct") is not None
        )
    )
    has_lane = bool(
        isinstance(lane_entry, dict)
        and lane_entry.get("samples", 0) > 0
        and (
            has_by_size
            or lane_entry.get("five_hour_per_m") is not None
            or lane_entry.get("weekly_per_m") is not None
        )
    )

    if has_lane:
        samples = int(lane_entry["samples"])
        max_ratio = lane_entry.get("max_ratio", 1.0)
        if has_by_size:
            source = "lane_exact"
            bs_samples = int(by_size_entry["samples"])
            estimates = {}
            for pct_field, per_m_field in (
                ("five_hour_pct", "five_hour_per_m"),
                ("weekly_pct", "weekly_per_m"),
            ):
                bs_val = by_size_entry.get(pct_field)
                per_m_val = lane_entry.get(per_m_field)
                scaled_val = per_m_val * mult if per_m_val is not None else None
                if bs_samples >= 2:
                    if bs_val is not None:
                        estimates[pct_field] = bs_val
                    elif scaled_val is not None:
                        estimates[pct_field] = scaled_val
                    else:
                        estimates[pct_field] = pool_or_cold(pct_field, per_m_field)
                else:
                    if bs_val is not None and scaled_val is not None:
                        estimates[pct_field] = 0.65 * bs_val + 0.35 * scaled_val
                    elif bs_val is not None:
                        estimates[pct_field] = bs_val
                    elif scaled_val is not None:
                        estimates[pct_field] = scaled_val
                    else:
                        estimates[pct_field] = pool_or_cold(pct_field, per_m_field)
            est_5h = estimates["five_hour_pct"]
            est_weekly = estimates["weekly_pct"]
        else:
            source = "lane_scaled"
            est_5h = (
                lane_entry["five_hour_per_m"] * mult
                if lane_entry.get("five_hour_per_m") is not None
                else pool_or_cold("five_hour_pct", "five_hour_per_m")
            )
            est_weekly = (
                lane_entry["weekly_per_m"] * mult
                if lane_entry.get("weekly_per_m") is not None
                else pool_or_cold("weekly_pct", "weekly_per_m")
            )
    elif has_pool:
        source = "pool_scaled"
        samples = int(pool_entry["samples"])
        max_ratio = pool_entry.get("max_ratio", 1.0)
        est_5h = (
            pool_entry["five_hour_per_m"] * weight * mult
            if pool_entry.get("five_hour_per_m") is not None
            else cold["five_hour_pct"]
        )
        est_weekly = (
            pool_entry["weekly_per_m"] * weight * mult
            if pool_entry.get("weekly_per_m") is not None
            else cold["weekly_pct"]
        )
    else:
        source = "cold_start"
        samples = 0
        max_ratio = 1.0
        est_5h = cold["five_hour_pct"]
        est_weekly = cold["weekly_pct"]

    margin = margin_override if margin_override is not None else _auto_safety_margin(samples, max_ratio)
    out_5h = round(float(est_5h), 2)
    out_weekly = round(float(est_weekly), 2)
    return {
        "unit_size": norm_size,
        "five_hour_pct": 0.0 if out_5h == 0.0 else out_5h,
        "weekly_pct": 0.0 if out_weekly == 0.0 else out_weekly,
        "safety_margin": margin,
        "source": source,
        "samples": samples,
    }


def _default_file_mode():
    mask = os.umask(0o022)
    os.umask(mask)
    return 0o666 & ~mask


def _write_json_atomic(path, payload):
    """Atomically write JSON to path, preserving mode/umask and rejecting symlinks."""
    target = Path(path)
    if target.is_symlink() or target.parent.is_symlink():
        raise ValueError(f"Refusing to write provider state through symlink: {target}")
    if target.exists() and target.is_dir():
        raise ValueError(f"Provider state path is a directory: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.parent.is_symlink():
        raise ValueError(f"Refusing to write provider state through symlink parent: {target.parent}")
    mode = stat.S_IMODE(target.stat().st_mode) if target.exists() else _default_file_mode()
    contents = json.dumps(payload, indent=2, ensure_ascii=True, allow_nan=False) + "\n"
    with NamedTemporaryFile(mode="w", encoding="utf-8", dir=target.parent, delete=False) as handle:
        temp = Path(handle.name)
        try:
            handle.write(contents)
            handle.flush()
            os.fsync(handle.fileno())
            handle.close()
            os.chmod(temp, mode)
            if target.is_symlink():
                raise ValueError(f"Refusing to overwrite symlink: {target}")
            os.replace(temp, target)
        finally:
            temp.unlink(missing_ok=True)


def record_burn(
    state_path,
    *,
    provider,
    model,
    effort="medium",
    unit_size,
    before_5h=None,
    after_5h=None,
    before_weekly=None,
    after_weekly=None,
    reset_occurred=False,
    now=None,
    alpha=None,
):
    """Record an observed post-unit burn sample into provider-state.json atomically."""
    if not isinstance(provider, str) or not provider.strip():
        raise ValueError("provider must be a non-empty string.")
    pool = normalize_pool(provider)
    if pool == "unknown" or not POOL_ID.fullmatch(pool):
        raise ValueError(f"Invalid provider ID: {provider!r}.")

    if not isinstance(model, str) or not model.strip() or any(
        ord(ch) < 32 or ord(ch) == 127 or ch == "|" for ch in model
    ):
        raise ValueError(f"Invalid model ID: {model!r}.")
    clean_model = model.strip()

    if not isinstance(effort, str) or not effort.strip() or any(
        ord(ch) < 32 or ord(ch) == 127 or ch == "|" for ch in effort
    ):
        raise ValueError(f"Invalid effort value: {effort!r}.")
    norm_effort = effort.strip().lower()

    norm_size = _validate_unit_size(unit_size)

    if type(reset_occurred) is not bool:
        raise ValueError("reset_occurred must be a boolean.")

    if (before_5h is None) != (after_5h is None):
        raise ValueError("Both before_5h and after_5h must be provided together.")
    if (before_weekly is None) != (after_weekly is None):
        raise ValueError("Both before_weekly and after_weekly must be provided together.")
    if before_5h is None and before_weekly is None:
        raise ValueError("At least one metric pair (before_5h/after_5h or before_weekly/after_weekly) is required.")

    b5 = _validate_pct_value(before_5h, "before_5h") if before_5h is not None else None
    a5 = _validate_pct_value(after_5h, "after_5h") if after_5h is not None else None
    bw = _validate_pct_value(before_weekly, "before_weekly") if before_weekly is not None else None
    aw = _validate_pct_value(after_weekly, "after_weekly") if after_weekly is not None else None

    if now is None:
        eval_now = datetime.now(timezone.utc)
    elif isinstance(now, str):
        eval_now = parse_iso_utc(now, "now")
    elif isinstance(now, datetime):
        eval_now = now.astimezone(timezone.utc) if now.tzinfo is not None else now.replace(tzinfo=timezone.utc)
    else:
        raise ValueError(f"Invalid now timestamp: {now!r}.")
    now_iso = format_iso_utc(eval_now)

    s_path = Path(state_path)
    if s_path.is_symlink() or s_path.parent.is_symlink():
        raise ValueError(f"Refusing to read or write provider state through symlink: {s_path}")
    if s_path.exists():
        if s_path.is_dir():
            raise ValueError(f"Provider state path is a directory: {s_path}")
        try:
            raw_state = json.loads(s_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, RecursionError) as err:
            raise ValueError(f"Invalid JSON in {s_path}: {err}") from err
        if not isinstance(raw_state, dict):
            raise ValueError("provider-state.json must contain a JSON object keyed by pool name.")
    else:
        raw_state = {}

    # Validate existing provider keys for alias collisions and find matching live entry key.
    seen_keys = {}
    target_provider_key = None
    for raw_key, entry in raw_state.items():
        if raw_key == CALIBRATION_KEY:
            continue
        if not isinstance(raw_key, str) or not raw_key.strip() or not isinstance(entry, dict):
            raise ValueError(f"Invalid provider-state entry for key {raw_key!r}.")
        norm_key = normalize_state_key(raw_key)
        if norm_key in seen_keys:
            raise ValueError(
                f"Conflicting provider-state entries for '{norm_key}': "
                f"{seen_keys[norm_key]!r} and {raw_key!r} normalize to the same key."
            )
        seen_keys[norm_key] = raw_key
        if norm_key == pool:
            target_provider_key = raw_key

    had_calibration = CALIBRATION_KEY in raw_state and raw_state[CALIBRATION_KEY] is not None
    cal = parse_calibration(raw_state)
    if alpha is not None:
        if type(alpha) not in (int, float) or not math.isfinite(float(alpha)):
            raise ValueError("alpha must be a finite number in (0, 1].")
        eff_alpha = float(alpha)
        if eff_alpha <= 0.0 or eff_alpha > 1.0:
            raise ValueError(f"alpha must be in (0, 1] (got {alpha!r}).")
        cal["alpha"] = eff_alpha
    else:
        eff_alpha = cal["alpha"]

    mult = UNIT_SIZE_MULTIPLIERS[norm_size]
    weight = model_burn_weight(clean_model, norm_effort)
    lkey = calibration_lane_key(pool, clean_model, norm_effort)

    # Capture prior estimates before updating calibration so max_ratio compares actual vs prior.
    prev_lane_est = estimate_burn(pool, clean_model, norm_effort, norm_size, calibration=cal)
    prev_pool_entry = cal["pools"].get(pool)
    defaults = DEFAULT_BURN_PER_M.get(pool, FALLBACK_BURN_PER_M)
    prev_pool_est = {}
    for pct_field, per_m_field in (
        ("five_hour_pct", "five_hour_per_m"),
        ("weekly_pct", "weekly_per_m"),
    ):
        if isinstance(prev_pool_entry, dict) and prev_pool_entry.get(per_m_field) is not None:
            prev_pool_est[pct_field] = prev_pool_entry[per_m_field] * weight * mult
        else:
            prev_pool_est[pct_field] = defaults[pct_field] * weight * mult

    warnings = []
    skipped_windows = []
    valid_deltas = {}
    deltas_report = {"five_hour_pct": None, "weekly_pct": None}

    for pct_field, before_val, after_val in (
        ("five_hour_pct", b5, a5),
        ("weekly_pct", bw, aw),
    ):
        if before_val is None:
            continue
        if reset_occurred:
            skipped_windows.append(pct_field)
            warnings.append(
                f"reset_occurred set; skipped calibration update for {pct_field} "
                f"(live state updated to {_fmt_num(after_val)}%)."
            )
            continue
        if after_val < before_val:
            skipped_windows.append(pct_field)
            warnings.append(
                f"window reset detected; skipped calibration update for {pct_field} "
                f"(before={_fmt_num(before_val)}%, after={_fmt_num(after_val)}%; live state updated)."
            )
            continue
        delta = round(after_val - before_val, 4)
        if delta == 0.0:
            delta = 0.0
        valid_deltas[pct_field] = delta
        deltas_report[pct_field] = delta

    if valid_deltas:
        lane = cal["lanes"].get(lkey)
        if lane is None:
            lane = {
                "samples": 0,
                "five_hour_per_m": None,
                "weekly_per_m": None,
                "max_ratio": 1.0,
                "by_size": {},
                "updated_at": now_iso,
            }
        lane["samples"] += 1
        lane["updated_at"] = now_iso
        size_bucket = lane["by_size"].get(norm_size)
        if size_bucket is None:
            size_bucket = {"samples": 0, "five_hour_pct": None, "weekly_pct": None}
            lane["by_size"][norm_size] = size_bucket
        size_bucket["samples"] += 1

        pool_cal = cal["pools"].get(pool)
        if pool_cal is None:
            pool_cal = {
                "samples": 0,
                "five_hour_per_m": None,
                "weekly_per_m": None,
                "max_ratio": 1.0,
                "updated_at": now_iso,
            }
        pool_cal["samples"] += 1
        pool_cal["updated_at"] = now_iso

        for pct_field, per_m_field in (
            ("five_hour_pct", "five_hour_per_m"),
            ("weekly_pct", "weekly_per_m"),
        ):
            if pct_field not in valid_deltas:
                continue
            delta = valid_deltas[pct_field]

            obs_lane_per_m = delta / mult
            prev_lane_per_m = lane.get(per_m_field)
            new_lane_per_m = (
                obs_lane_per_m
                if prev_lane_per_m is None
                else eff_alpha * obs_lane_per_m + (1.0 - eff_alpha) * prev_lane_per_m
            )
            new_lane_per_m = round(new_lane_per_m, 4)
            lane[per_m_field] = 0.0 if new_lane_per_m == 0.0 else new_lane_per_m

            prev_bs = size_bucket.get(pct_field)
            new_bs = delta if prev_bs is None else eff_alpha * delta + (1.0 - eff_alpha) * prev_bs
            new_bs = round(new_bs, 4)
            size_bucket[pct_field] = 0.0 if new_bs == 0.0 else new_bs

            prev_est_val = prev_lane_est.get(pct_field)
            if prev_est_val is not None and prev_est_val > 0.0:
                ratio = min(MAX_RATIO_MAX, max(MAX_RATIO_MIN, delta / prev_est_val))
                lane["max_ratio"] = round(max(float(lane.get("max_ratio", 1.0)), ratio), 4)

            obs_pool_per_m = delta / (mult * weight)
            prev_pool_per_m = pool_cal.get(per_m_field)
            new_pool_per_m = (
                obs_pool_per_m
                if prev_pool_per_m is None
                else eff_alpha * obs_pool_per_m + (1.0 - eff_alpha) * prev_pool_per_m
            )
            new_pool_per_m = round(new_pool_per_m, 4)
            pool_cal[per_m_field] = 0.0 if new_pool_per_m == 0.0 else new_pool_per_m

            prev_pool_est_val = prev_pool_est.get(pct_field)
            if prev_pool_est_val is not None and prev_pool_est_val > 0.0:
                pool_ratio = min(MAX_RATIO_MAX, max(MAX_RATIO_MIN, delta / prev_pool_est_val))
                pool_cal["max_ratio"] = round(max(float(pool_cal.get("max_ratio", 1.0)), pool_ratio), 4)

        cal["lanes"][lkey] = lane
        cal["pools"][pool] = pool_cal

    updated_state = dict(raw_state)
    if target_provider_key is None:
        target_provider_key = pool
        live_entry = {
            "status": "up",
            "down_until": None,
            "limit": None,
            "five_hour_pct": None,
            "weekly_pct": None,
            "resets_at": None,
            "observed_at": now_iso,
        }
    else:
        live_entry = dict(raw_state[target_provider_key])

    if a5 is not None:
        live_entry["five_hour_pct"] = a5
    if aw is not None:
        live_entry["weekly_pct"] = aw
    live_entry["observed_at"] = now_iso
    updated_state[target_provider_key] = live_entry

    if valid_deltas or had_calibration:
        updated_state[CALIBRATION_KEY] = cal

    _write_json_atomic(s_path, updated_state)

    updated_est = estimate_burn(pool, clean_model, norm_effort, norm_size, calibration=cal)
    return {
        "mode": "record_burn",
        "state_path": str(s_path),
        "provider": pool,
        "model": canonical_model_id(clean_model),
        "effort": norm_effort,
        "lane_key": lkey,
        "unit_size": norm_size,
        "recorded_at": now_iso,
        "calibration_updated": bool(valid_deltas),
        "deltas": deltas_report,
        "skipped_windows": skipped_windows,
        "warnings": warnings,
        "estimated_burn": updated_est,
        "lane_calibration": cal["lanes"].get(lkey),
        "pool_calibration": cal["pools"].get(pool),
        "provider_state": live_entry,
    }


def render_record_burn_markdown(summary):
    """Render --record-burn output as concise GitHub-flavored Markdown."""
    deltas = summary["deltas"]
    est = summary["estimated_burn"]
    pstate = summary["provider_state"]
    delta_parts = []
    if deltas["five_hour_pct"] is not None:
        delta_parts.append(f"5h `+{_fmt_num(deltas['five_hour_pct'])}%`")
    if deltas["weekly_pct"] is not None:
        delta_parts.append(f"weekly `+{_fmt_num(deltas['weekly_pct'])}%`")
    delta_str = ", ".join(delta_parts) if delta_parts else "none (calibration skipped due to window reset)"

    lines = [
        f"# Burn calibration recorded · `{_md_cell(summary['lane_key'])}`",
        "",
        f"- **State file:** `{summary['state_path']}`",
        f"- **Lane:** `{_md_cell(summary['lane_key'])}` (unit size `{summary['unit_size']}`)",
        f"- **Recorded at:** `{summary['recorded_at']}`",
        f"- **Observed delta:** {delta_str}",
        f"- **Calibration updated:** `{'yes' if summary['calibration_updated'] else 'no'}`",
        (
            f"- **Updated estimate (`{est['unit_size']}`):** "
            f"5h `+{_fmt_num(est['five_hour_pct'])}%`, weekly `+{_fmt_num(est['weekly_pct'])}%` "
            f"(safety margin `{_fmt_num(est['safety_margin'])}x`, source `{est['source']}`, samples `{est['samples']}`)"
        ),
        (
            f"- **Updated provider state (`{summary['provider']}`):** "
            f"status `{_md_cell(pstate.get('status', 'up'))}`, "
            f"5h `{_fmt_num(pstate.get('five_hour_pct'))}%`, "
            f"weekly `{_fmt_num(pstate.get('weekly_pct'))}%`, "
            f"observed_at `{_md_cell(pstate.get('observed_at'))}`"
        ),
    ]
    if summary["warnings"]:
        lines.extend(["", "## Warnings", ""])
        for warning in summary["warnings"]:
            clean_warning = str(warning).replace("\r\n", " ").replace("\r", " ").replace("\n", " ")
            lines.append(f"- {clean_warning}")
    return "\n".join(lines) + "\n"


def parse_provider_state(raw_state, now, stale_minutes):
    """Normalize and evaluate provider-state.json entries against now and stale TTL."""
    _validate_stale_minutes(stale_minutes)
    if not isinstance(raw_state, dict):
        raise ValueError("provider-state.json must contain a JSON object keyed by pool name.")

    if CALIBRATION_KEY in raw_state:
        parse_calibration(raw_state)

    normalized_entries = {}
    seen_raw_keys = {}
    for raw_key, entry in raw_state.items():
        if raw_key == CALIBRATION_KEY:
            continue
        if not isinstance(raw_key, str) or not raw_key.strip() or not isinstance(entry, dict):
            raise ValueError(f"Invalid provider-state entry for key {raw_key!r}.")
        pool_key = normalize_state_key(raw_key)
        if pool_key in normalized_entries:
            raise ValueError(
                f"Conflicting provider-state entries for '{pool_key}': "
                f"{seen_raw_keys[pool_key]!r} and {raw_key!r} normalize to the same key."
            )
        normalized_entries[pool_key] = entry
        seen_raw_keys[pool_key] = raw_key

    evaluated = {}
    warnings = []
    stale_delta = timedelta(minutes=stale_minutes)

    for pool, entry in sorted(normalized_entries.items()):
        status_raw = entry.get("status", "up")
        if not isinstance(status_raw, str):
            raise ValueError(f"Provider '{pool}' has unsupported status {status_raw!r}; expected 'up' or 'down'.")
        status = status_raw.strip().lower()
        if status not in ("up", "down"):
            raise ValueError(f"Provider '{pool}' has unsupported status {status!r}; expected 'up' or 'down'.")

        five_hour_pct = _optional_pct(entry, "five_hour_pct")
        weekly_pct = _optional_pct(entry, "weekly_pct")
        limit_note = _optional_limit(entry, pool)
        resets_at_raw = entry.get("resets_at")
        if isinstance(resets_at_raw, str) and not resets_at_raw.strip():
            resets_at_raw = None
        down_until_raw = entry.get("down_until")
        if isinstance(down_until_raw, str) and not down_until_raw.strip():
            down_until_raw = None
        observed_at_raw = entry.get("observed_at")

        # Parse down_until early when status is 'down' so an active explicit outage cooldown
        # does not emit a spurious stale warning on observed_at.
        down_until_dt = None
        down_until_error = False
        active_outage = False
        if status == "down" and down_until_raw is not None:
            try:
                down_until_dt = parse_iso_utc(down_until_raw, f"{pool}.down_until")
                active_outage = down_until_dt > now
            except ValueError:
                down_until_error = True

        # Quota percentages are usable only for a current, pre-reset observation.
        stale = False
        observed_dt = None
        observed_at_iso = None
        age_minutes = None
        if observed_at_raw is None or (isinstance(observed_at_raw, str) and not observed_at_raw.strip()):
            if not active_outage:
                stale = True
                warnings.append(f"Pool '{pool}' state is stale (missing observed_at).")
        else:
            try:
                observed_dt = parse_iso_utc(observed_at_raw, f"{pool}.observed_at")
                observed_at_iso = format_iso_utc(observed_dt)
                delta = now - observed_dt
                age_minutes = round(delta.total_seconds() / 60.0, 1)
                if not active_outage:
                    if delta < timedelta(0):
                        stale = True
                        warnings.append(f"Pool '{pool}' state is stale (observed_at is in the future).")
                    elif delta > stale_delta:
                        stale = True
                        warnings.append(
                            f"Pool '{pool}' state is stale (observed {age_minutes:.1f} min ago; TTL {stale_minutes} min)."
                        )
            except ValueError as err:
                if not active_outage:
                    stale = True
                    warnings.append(f"Pool '{pool}' state is stale ({err}).")

        if not stale and not active_outage and resets_at_raw is not None:
            try:
                resets_at = parse_iso_utc(resets_at_raw, f"{pool}.resets_at")
            except ValueError as err:
                stale = True
                warnings.append(f"Pool '{pool}' state is stale (invalid resets_at: {err}).")
            else:
                if observed_dt < resets_at <= now:
                    # A single resets_at cannot identify which of two counters reset.
                    stale = True
                    warnings.append(f"Pool '{pool}' state is stale (quota reset after observed_at).")

        windows = tuple(
            (field, pct, move, stop)
            for field, pct, move, stop in (
                ("weekly_pct", weekly_pct, WEEKLY_MOVE_PCT, WEEKLY_STOP_PCT),
                ("five_hour_pct", five_hour_pct, FIVE_HOUR_MOVE_PCT, FIVE_HOUR_STOP_PCT),
            )
            if not stale and pct is not None
        )
        headroom = round(min(100.0 - pct for _, pct, _, _ in windows), 2) if windows else None

        # Evaluate exclusion (down / stopped) and deprioritization (move threshold).
        excluded = False
        deprioritized = False
        probe_due = False
        reasons = []
        effective_state = "stale" if stale else "up"

        if status == "down":
            excluded = True
            effective_state = "down"
            headroom = None
            if down_until_raw is None:
                reasons.append("down (no down_until)" + (f": {limit_note}" if limit_note else ""))
            elif down_until_error:
                reasons.append(f"down (unparseable down_until: {down_until_raw!r})")
            elif down_until_dt > now:
                reasons.append(
                    f"down until {format_iso_utc(down_until_dt)}"
                    + (f" ({limit_note})" if limit_note else "")
                )
            else:
                probe_due = True
                effective_state = "probe-only"
                reasons.append("Cooldown expired. Confirm recovery with one probe before routing.")
        else:
            stop_reasons = [
                f"{field}={_fmt_pct(pct)}% >= {_fmt_pct(stop)}%"
                for field, pct, _, stop in windows
                if pct >= stop
            ]
            move_reasons = [
                f"{field}={_fmt_pct(pct)}% >= {_fmt_pct(move)}%"
                for field, pct, move, _ in windows
                if pct >= move
            ]
            if stop_reasons:
                excluded = True
                effective_state = "stopped"
                reasons.append("stopped (" + ", ".join(stop_reasons) + ")")
            elif move_reasons:
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


def role_score(candidate, role, *, ignore_knowledge=False):
    """Compute the role score for a candidate, or None when required metrics are missing."""
    if role == "review":
        if candidate.get("review_override") is not None:
            return round(float(candidate["review_override"]), 2)
        acc = candidate["profiles"].get("accuracy")
        reas = candidate["profiles"].get("reasoning")
        know = None if ignore_knowledge else candidate["profiles"].get("knowledge")
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


def _is_unconfigured_placeholder(state):
    return (
        state["status"] == "up"
        and state["five_hour_pct"] is None
        and state["weekly_pct"] is None
        and (state["resets_at"] is None or (isinstance(state["resets_at"], str) and not state["resets_at"].strip()))
        and (state["down_until"] is None or (isinstance(state["down_until"], str) and not state["down_until"].strip()))
        and state["limit"] is None
        and (state["observed_at"] is None or (isinstance(state["observed_at"], str) and not state["observed_at"].strip()))
    )


def resolve_lanes(
    candidates,
    provider_states,
    *,
    role="coding",
    author_family=None,
    allowed_providers=None,
    authorized_lanes=None,
    restricted_data=False,
    state_loaded=False,
    state_warnings=None,
    cohort=None,
    unit_size=None,
    safety_margin=None,
    calibration=None,
):
    """Filter, score, classify (±3-pt equivalence), and deterministically rank lanes."""
    warnings = list(state_warnings or [])
    eligible = []
    excluded = []

    norm_unit_size = _validate_unit_size(unit_size) if unit_size is not None else None
    norm_safety_margin = _validate_safety_margin(safety_margin) if safety_margin is not None else None
    if norm_safety_margin is not None and norm_unit_size is None:
        warnings.append("--safety-margin is ignored when --unit-size is not specified.")
    cal = parse_calibration({CALIBRATION_KEY: calibration}) if calibration is not None else empty_calibration()

    allowed_set = {normalize_pool(p) for p in allowed_providers} if allowed_providers is not None else None
    norm_author = normalize_family(author_family) if author_family else None
    if norm_author and role != "review":
        warnings.append(
            f"--author-family '{norm_author}' is ignored for role '{role}' (applies only to --role review)."
        )

    if authorized_lanes is None:
        warnings.append("No explicit authorized lanes found in the project profile; ranking is advisory.")
    matched_authorized_keys = set()

    for cand in candidates:
        pool = cand["pool"]
        family = cand["family"]
        score = role_score(cand, role)
        key = lane_key(cand["model"], cand["effort"], pool)
        lane = authorized_lanes.get(key) if authorized_lanes is not None else None
        if lane is not None:
            matched_authorized_keys.add(key)

        model_name = lane["model"] if lane else cand["model"]
        est = (
            estimate_burn(
                pool,
                model_name,
                cand["effort"],
                norm_unit_size,
                calibration=cal,
                safety_margin=norm_safety_margin,
            )
            if norm_unit_size is not None
            else None
        )

        exclusion_reasons = []
        if authorized_lanes is not None and (lane is None or role not in lane["roles"]):
            exclusion_reasons.append("model, effort and pool are not authorized for this role")
        if restricted_data and (lane is None or not lane["restricted_data"]):
            exclusion_reasons.append("lane is not authorized for restricted data")
        if allowed_set is not None and pool not in allowed_set:
            exclusion_reasons.append("not in --providers allowlist")

        pstate = provider_states.get(pool)
        model_state_key = normalize_state_key(cand["model"])
        mstate = provider_states.get(model_state_key) if model_state_key != pool else None

        if pstate is not None and pstate["excluded"]:
            exclusion_reasons.extend(pstate["reasons"])
        if mstate is not None and mstate["excluded"]:
            exclusion_reasons.extend(f"model {r}" for r in mstate["reasons"])

        if exclusion_reasons:
            excluded.append(
                {
                    "model": model_name,
                    "effort": cand["effort"],
                    "pool": pool,
                    "family": family,
                    "score": score,
                    "source": cand["source"],
                    "unit_size": norm_unit_size,
                    "estimated_burn": est,
                    "projected_five_hour_pct": None,
                    "projected_weekly_pct": None,
                    "projected_overflow": False,
                    "projected_deprioritized": False,
                    "projected_headroom_pct": None,
                    "reasons": exclusion_reasons,
                    "_candidate": cand,
                }
            )
            continue

        if pstate is None:
            effective_state = "untracked" if state_loaded else "up"
            deprioritized = False
            headroom = None
            stale = state_loaded
            state_reasons = ["not listed in provider-state.json"] if state_loaded else []
        else:
            effective_state = pstate["effective_state"]
            deprioritized = pstate["deprioritized"]
            headroom = pstate["headroom"]
            stale = pstate["stale"]
            state_reasons = list(pstate["reasons"])

        active_mstate = (
            mstate
            if mstate is not None
            and not (
                pstate is not None
                and not pstate["stale"]
                and pstate["status"] == "up"
                and _is_unconfigured_placeholder(mstate)
            )
            else None
        )
        if active_mstate is not None:
            if active_mstate["deprioritized"]:
                deprioritized = True
                effective_state = "deprioritized"
                state_reasons.extend(f"model {r}" for r in active_mstate["reasons"])
            if active_mstate["headroom"] is not None:
                headroom = (
                    active_mstate["headroom"]
                    if headroom is None
                    else min(headroom, active_mstate["headroom"])
                )
            stale = stale or active_mstate["stale"]

        if stale:
            headroom = None
            if effective_state == "up":
                effective_state = "stale"

        projected_five_hour_pct = None
        projected_weekly_pct = None
        projected_overflow = False
        projected_deprioritized = False
        projected_headroom_pct = None

        if norm_unit_size is not None and not stale:
            cur_5h_vals = [
                st["five_hour_pct"]
                for st in (pstate, active_mstate)
                if st is not None and not st["stale"] and st["five_hour_pct"] is not None
            ]
            cur_wk_vals = [
                st["weekly_pct"]
                for st in (pstate, active_mstate)
                if st is not None and not st["stale"] and st["weekly_pct"] is not None
            ]
            current_5h = max(cur_5h_vals) if cur_5h_vals else None
            current_weekly = max(cur_wk_vals) if cur_wk_vals else None
            margin = est["safety_margin"]

            if current_5h is not None:
                proj_5h = round(current_5h + est["five_hour_pct"] * margin, 2)
                projected_five_hour_pct = 0.0 if proj_5h == 0.0 else proj_5h
            if current_weekly is not None:
                proj_wk = round(current_weekly + est["weekly_pct"] * margin, 2)
                projected_weekly_pct = 0.0 if proj_wk == 0.0 else proj_wk

            projected_vals = [v for v in (projected_five_hour_pct, projected_weekly_pct) if v is not None]
            if projected_vals:
                proj_hr = max(0.0, round(100.0 - max(projected_vals), 2))
                projected_headroom_pct = 0.0 if proj_hr == 0.0 else proj_hr

            overflow_reasons = []
            if projected_five_hour_pct is not None and projected_five_hour_pct >= FIVE_HOUR_STOP_PCT:
                overflow_reasons.append(
                    f"projected five_hour_pct {_fmt_proj_num(projected_five_hour_pct)}% >= "
                    f"{_fmt_pct(FIVE_HOUR_STOP_PCT)}% stop "
                    f"({_fmt_proj_num(current_5h)}% + {_fmt_proj_num(est['five_hour_pct'])}% x {_fmt_proj_num(margin)})"
                )
            if projected_weekly_pct is not None and projected_weekly_pct >= WEEKLY_STOP_PCT:
                overflow_reasons.append(
                    f"projected weekly_pct {_fmt_proj_num(projected_weekly_pct)}% >= "
                    f"{_fmt_pct(WEEKLY_STOP_PCT)}% stop "
                    f"({_fmt_proj_num(current_weekly)}% + {_fmt_proj_num(est['weekly_pct'])}% x {_fmt_proj_num(margin)})"
                )

            if overflow_reasons:
                excluded.append(
                    {
                        "model": model_name,
                        "effort": cand["effort"],
                        "pool": pool,
                        "family": family,
                        "score": score,
                        "source": cand["source"],
                        "status": "blocked",
                        "pool_state": "blocked",
                        "unit_size": norm_unit_size,
                        "estimated_burn": est,
                        "projected_five_hour_pct": projected_five_hour_pct,
                        "projected_weekly_pct": projected_weekly_pct,
                        "projected_overflow": True,
                        "projected_deprioritized": False,
                        "projected_headroom_pct": projected_headroom_pct,
                        "reasons": overflow_reasons,
                        "_candidate": cand,
                    }
                )
                continue

            proj_move_reasons = []
            if projected_five_hour_pct is not None and projected_five_hour_pct >= FIVE_HOUR_MOVE_PCT:
                proj_move_reasons.append(
                    f"projected five_hour_pct {_fmt_proj_num(projected_five_hour_pct)}% >= "
                    f"{_fmt_pct(FIVE_HOUR_MOVE_PCT)}% move "
                    f"({_fmt_proj_num(current_5h)}% + {_fmt_proj_num(est['five_hour_pct'])}% x {_fmt_proj_num(margin)})"
                )
            if projected_weekly_pct is not None and projected_weekly_pct >= WEEKLY_MOVE_PCT:
                proj_move_reasons.append(
                    f"projected weekly_pct {_fmt_proj_num(projected_weekly_pct)}% >= "
                    f"{_fmt_pct(WEEKLY_MOVE_PCT)}% move "
                    f"({_fmt_proj_num(current_weekly)}% + {_fmt_proj_num(est['weekly_pct'])}% x {_fmt_proj_num(margin)})"
                )
            if proj_move_reasons:
                projected_deprioritized = True
                deprioritized = True
                if effective_state == "up":
                    effective_state = "deprioritized"
                state_reasons.extend(proj_move_reasons)

        same_family = bool(role == "review" and norm_author and family == norm_author)

        eligible.append(
            {
                "model": model_name,
                "runner": lane["runner"] if lane else None,
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
                "same_family": same_family,
                "state_reasons": state_reasons,
                "unit_size": norm_unit_size,
                "estimated_burn": est,
                "projected_five_hour_pct": projected_five_hour_pct,
                "projected_weekly_pct": projected_weekly_pct,
                "projected_overflow": projected_overflow,
                "projected_deprioritized": projected_deprioritized,
                "projected_headroom_pct": projected_headroom_pct,
                "_candidate": cand,
            }
        )

    if authorized_lanes is not None:
        for key, lane in authorized_lanes.items():
            if key not in matched_authorized_keys:
                warnings.append(
                    f"Authorized lane '{lane['model']}' ({lane['effort']}) in pool '{lane['pool']}' "
                    "has no measurements in model-measurements.md."
                )

    if state_loaded:
        untracked_pools = sorted({item["pool"] for item in eligible if item["pool_state"] == "untracked"})
        for pool in untracked_pools:
            warnings.append(f"Pool '{pool}' is absent from provider-state.json (treated as stale/unknown headroom).")

    score_basis, score_cohort, score_meta = _score_candidates(
        eligible, role, cohort, warnings, norm_author=norm_author
    )
    _score_excluded(excluded, role, score_basis, score_cohort, score_meta)
    _shared_latencies(eligible)

    # Compute top score for the ±3-point equivalence rubric.
    # For cross-family review, anchor equivalence to the best eligible cross-family candidate
    # when at least one measured cross-family candidate exists.
    measured = [item for item in eligible if item["score"] is not None]
    cross_family_anchored = False
    has_cross_family = bool(role == "review" and norm_author and any(not item["same_family"] for item in eligible))
    cross_measured = [item for item in measured if not item["same_family"]] if has_cross_family else []
    if has_cross_family:
        if cross_measured:
            anchor_pool = cross_measured
            cross_family_anchored = True
        else:
            anchor_pool = measured
    else:
        anchor_pool = measured

    unmeasured_cross_blocks_same_family = bool(has_cross_family and not cross_measured)
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
        if item["projected_deprioritized"]:
            flags.append("projected-deprioritized")
        if item["stale"]:
            flags.append("stale")
        item["flags"] = flags

    def sort_key(item):
        is_unmeasured = item["score"] is None
        is_same_family = item["same_family"]
        is_below = item["tier"] != "equivalent"
        # Known positive headroom is preferred over unknown (conservative neutral tie-break: 0.0).
        eff_headroom = _effective_headroom(item)
        headroom_rank = eff_headroom if eff_headroom is not None else 0.0
        score_rank = item["score"] if item["score"] is not None else -1.0
        latency_rank = item["_comparable_latency"]

        if is_unmeasured:
            # When cross-family review has eligible cross-family lanes but none are measured,
            # keep cross-family candidates ahead of same-family candidates so a lone same-family
            # score cannot outrank healthy cross-family reviewers.
            primary = 0 if (unmeasured_cross_blocks_same_family and not is_same_family) else 2
            return (
                primary,
                1 if is_same_family else 0,
                1 if item["deprioritized"] else 0,
                1 if item["stale"] else 0,
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
                1 if item["stale"] else 0,
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
            1 if item["stale"] else 0,
            -headroom_rank,
            latency_rank,
            item["model"].lower(),
            item["effort"].lower(),
        )

    eligible.sort(key=sort_key)
    for rank, item in enumerate(eligible, start=1):
        item["rank"] = rank
        del item["_comparable_latency"]

    excluded.sort(
        key=lambda item: (
            item["score"] is None,
            -(item["score"] if item["score"] is not None else 0.0),
            item["model"].lower(),
            item["effort"].lower(),
        )
    )

    top_lane = (
        eligible[0]
        if eligible and score_basis != "unavailable" and eligible[0]["score"] is not None
        else None
    )
    if not eligible:
        warnings.append(f"No eligible lanes available for role '{role}'.")
    elif unmeasured_cross_blocks_same_family and measured:
        if not any("no measured cross-family reviewers" in w for w in warnings):
            warnings.append(
                f"No measured cross-family reviewers available for author family '{norm_author}'; "
                "same-family lane cannot be recommended ahead of unmeasured cross-family reviewers."
            )
    elif top_lane is None:
        warnings.append(f"No eligible lane has a comparable score for '{role}'.")
    elif top_lane["same_family"]:
        warnings.append(
            f"No cross-family reviewer available for author family '{norm_author}'; top lane is same-family."
        )
    if top_lane is not None and top_lane["stale"]:
        warnings.append("Top lane has stale or untracked quota state. Confirm live usage before routing.")

    return {
        "top_score": top_score,
        "score_basis": score_basis,
        "score_cohort": score_cohort,
        "cross_family_anchored": cross_family_anchored,
        "unit_size": norm_unit_size,
        "safety_margin": norm_safety_margin,
        "recommended": top_lane if authorized_lanes is not None else None,
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


def _md_cell(val):
    text = str(val).replace("\r\n", " ").replace("\r", " ").replace("\n", " ")
    return text.replace("|", "\\|")


def _fmt_projected_cell(row):
    parts = []
    if row.get("projected_five_hour_pct") is not None:
        parts.append(f"5h {_fmt_proj_num(row['projected_five_hour_pct'])}%")
    if row.get("projected_weekly_pct") is not None:
        parts.append(f"wk {_fmt_proj_num(row['projected_weekly_pct'])}%")
    return ", ".join(parts) if parts else "-"


def _fmt_burn_cell(row):
    est = row.get("estimated_burn")
    if not isinstance(est, dict):
        return "-"
    return (
        f"+{_fmt_num(est.get('five_hour_pct'))}% / +{_fmt_num(est.get('weekly_pct'))}% "
        f"(x{_fmt_num(est.get('safety_margin'))}, {est.get('source', '-')})"
    )


def render_markdown(report):
    """Render lane resolution report as concise GitHub-flavored Markdown."""
    anchor_label = "top eligible cross-family score" if report.get("cross_family_anchored") else "top eligible score"
    unit_size = report.get("unit_size")
    lines = [
        f"# Lane resolution · {report['role']}",
        "",
        f"- **Role:** `{report['role']}` ({report['scoring_method']})",
        f"- **Equivalence band:** within ±{report['equivalence_threshold_points']:g} pts of {anchor_label} `{_fmt_num(report['top_score'])}`",
    ]
    if unit_size:
        margin_note = (
            f"safety margin override `{_fmt_num(report['safety_margin'])}x`"
            if report.get("safety_margin") is not None
            else "auto safety margin"
        )
        lines.append(f"- **Unit size:** `{unit_size}` ({margin_note})")
    if report["score_basis"] == "workspace" and report["score_cohort"] is not None:
        lines.append(f"- **Score cohort:** live `{report['score_cohort']}` (matched normalized points)")
    elif report["score_basis"] == "historical":
        lines.append("- **Score cohort:** historical snapshot")
    elif report["score_cohort"] is not None:
        lines.append(f"- **Score cohort:** no comparable score available for `{report['score_cohort']}`")
    else:
        lines.append("- **Score cohort:** no comparable score available")
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
        lines.append("- **Data scope:** `restricted` (requires explicit per-lane authorization)")
    if report["allowed_providers"] is not None:
        allowed_csv = ", ".join(f"`{p}`" for p in report["allowed_providers"])
        lines.append(f"- **Allowed pools:** {allowed_csv}")
    if report["profile_path"]:
        lines.append(f"- **Project profile:** `{report['profile_path']}`")

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
        if unit_size:
            proj_hr = (
                f"{_fmt_num(rec['projected_headroom_pct'])}%"
                if rec.get("projected_headroom_pct") is not None
                else "unknown"
            )
            proj_summary = _fmt_projected_cell(rec)
            proj_extra = f" ({proj_summary})" if proj_summary != "-" else ""
            est = rec.get("estimated_burn")
            burn_extra = (
                f" · est burn `+{_fmt_num(est['five_hour_pct'])}%` 5h / `+{_fmt_num(est['weekly_pct'])}%` wk "
                f"× `{_fmt_num(est['safety_margin'])}` (`{est['source']}`)"
                if isinstance(est, dict)
                else ""
            )
            lines.append(
                f"- **Recommended lane:** `{rec['model']}` (`{rec['effort']}`) · "
                f"pool `{rec['pool']}` · score `{_fmt_num(rec['score'])}` · "
                f"projected headroom `{proj_hr}`{proj_extra} (current `{headroom_str}`){burn_extra}{flags_str}"
            )
        else:
            lines.append(
                f"- **Recommended lane:** `{rec['model']}` (`{rec['effort']}`) · "
                f"pool `{rec['pool']}` · score `{_fmt_num(rec['score'])}` · "
                f"headroom `{headroom_str}`{flags_str}"
            )
        lines.append(f"- **Authorized runner:** {_md_cell(rec['runner'])}")
        if not dispatch_ok(rec):
            lines.append(
                "- **Dispatch:** not OK. Do not send new units to this pool; "
                "take the next ladder step (below-tier, verification one step higher) or wait for the reset."
            )
    elif report["advisory"]:
        lines.append("- **Recommended lane:** none (advisory only)")
    else:
        lines.append("- **Recommended lane:** none")

    if report["warnings"]:
        lines.extend(["", "## Warnings", ""])
        for warning in report["warnings"]:
            clean_warning = str(warning).replace("\r\n", " ").replace("\r", " ").replace("\n", " ")
            lines.append(f"- {clean_warning}")

    lines.extend(["", "## Advisory candidates" if report["advisory"] else "## Ranked eligible lanes", ""])
    if report["ranked"]:
        if unit_size:
            lines.extend(
                [
                    "| Rank | Model | Effort | Pool | Family | Score | Delta | Tier | Pool state | Headroom | Est. burn (5h / wk) | Projected | Proj. headroom | s/task | Flags | Source |",
                    "| ---: | --- | --- | --- | --- | ---: | ---: | --- | --- | ---: | --- | --- | ---: | ---: | --- | --- |",
                ]
            )
        else:
            lines.extend(
                [
                    "| Rank | Model | Effort | Pool | Family | Score | Delta | Tier | Pool state | Headroom | s/task | Flags | Source |",
                    "| ---: | --- | --- | --- | --- | ---: | ---: | --- | --- | ---: | ---: | --- | --- |",
                ]
            )
        for row in report["ranked"]:
            headroom_cell = f"{_fmt_num(row['headroom'])}%" if row["headroom"] is not None else "unknown"
            flags_cell = _md_cell(", ".join(row["flags"]) if row["flags"] else "-")
            latency = _fmt_num(row["latency_s"])
            if row["latency_s"] is not None and row["latency_kind"] == "estimate":
                latency += " (estimate)"
            if unit_size:
                proj_hr_cell = (
                    f"{_fmt_num(row['projected_headroom_pct'])}%"
                    if row.get("projected_headroom_pct") is not None
                    else "unknown"
                )
                lines.append(
                    f"| {row['rank']} | `{_md_cell(row['model'])}` | `{_md_cell(row['effort'])}` | "
                    f"`{_md_cell(row['pool'])}` | `{_md_cell(row['family'])}` | "
                    f"{_fmt_num(row['score'])} | {_fmt_delta(row['delta'])} | {_md_cell(row['tier'])} | "
                    f"{_md_cell(row['pool_state'])} | {headroom_cell} | {_md_cell(_fmt_burn_cell(row))} | "
                    f"{_md_cell(_fmt_projected_cell(row))} | {proj_hr_cell} | {latency} | {flags_cell} | "
                    f"{_md_cell(row['source'])} |"
                )
            else:
                lines.append(
                    f"| {row['rank']} | `{_md_cell(row['model'])}` | `{_md_cell(row['effort'])}` | "
                    f"`{_md_cell(row['pool'])}` | `{_md_cell(row['family'])}` | "
                    f"{_fmt_num(row['score'])} | {_fmt_delta(row['delta'])} | {_md_cell(row['tier'])} | "
                    f"{_md_cell(row['pool_state'])} | {headroom_cell} | {latency} | {flags_cell} | "
                    f"{_md_cell(row['source'])} |"
                )
    else:
        lines.append("_No ranked lanes._")

    if report["excluded"]:
        if unit_size:
            lines.extend(
                [
                    "",
                    "## Excluded lanes",
                    "",
                    "| Model | Effort | Pool | Family | Score | Projected | Reason |",
                    "| --- | --- | --- | --- | ---: | --- | --- |",
                ]
            )
        else:
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
            reason_cell = _md_cell("; ".join(row["reasons"]))
            if unit_size:
                lines.append(
                    f"| `{_md_cell(row['model'])}` | `{_md_cell(row['effort'])}` | "
                    f"`{_md_cell(row['pool'])}` | `{_md_cell(row['family'])}` | "
                    f"{_fmt_num(row['score'])} | {_md_cell(_fmt_projected_cell(row))} | {reason_cell} |"
                )
            else:
                lines.append(
                    f"| `{_md_cell(row['model'])}` | `{_md_cell(row['effort'])}` | "
                    f"`{_md_cell(row['pool'])}` | `{_md_cell(row['family'])}` | "
                    f"{_fmt_num(row['score'])} | {reason_cell} |"
                )

    return "\n".join(lines) + "\n"


def _parse_author_family_arg(raw):
    text = raw.strip() if isinstance(raw, str) else ""
    if not text or not POOL_ID.fullmatch(text):
        raise argparse.ArgumentTypeError(
            f"invalid author family {raw!r} (expected a provider family ID like claude, openai, google, deepseek)"
        )
    norm = normalize_family(text)
    if norm == "unknown" or not POOL_ID.fullmatch(norm):
        raise argparse.ArgumentTypeError(f"invalid author family {raw!r} (cannot be 'unknown')")
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


def _parse_unit_size_arg(raw):
    try:
        return _validate_unit_size(raw)
    except ValueError as err:
        raise argparse.ArgumentTypeError(str(err)) from err


def _parse_safety_margin_arg(raw):
    try:
        value = float(raw)
    except ValueError as err:
        raise argparse.ArgumentTypeError(f"invalid float: {raw!r}") from err
    try:
        return _validate_safety_margin(value)
    except ValueError as err:
        raise argparse.ArgumentTypeError(str(err)) from err


def _parse_pct_arg(raw):
    try:
        value = float(raw)
    except ValueError as err:
        raise argparse.ArgumentTypeError(f"invalid percentage: {raw!r}") from err
    try:
        return _validate_pct_value(value, "percentage")
    except ValueError as err:
        raise argparse.ArgumentTypeError(str(err)) from err


def build_parser():
    parser = argparse.ArgumentParser(
        description=(
            "Deterministically rank eligible orchestration lanes from model measurements and "
            "live provider-state.json using the +/-3-point equivalence rubric, with optional "
            "pre-dispatch projected quota guard and self-calibrating burn recording. "
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
        "--profile",
        type=Path,
        default=None,
        help="Project profile with explicit authorized lanes (default: <workspace>/.orchestration/project-profile.md).",
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
        "--cohort",
        metavar="ID",
        help="Use only this live scoring cohort (default: the sole eligible live cohort, or historical evidence).",
    )
    parser.add_argument(
        "--author-family",
        type=_parse_author_family_arg,
        default=None,
        metavar="FAMILY",
        help="Author model family for --role review (e.g. claude, openai, google, deepseek, or custom provider); prioritizes cross-family lanes first and flags same-family lanes.",
    )
    parser.add_argument(
        "--providers",
        type=_parse_providers_arg,
        default=None,
        metavar="CSV",
        help="Additional comma-separated provider/pool filter (e.g. claude,openai,google).",
    )
    parser.add_argument(
        "--restricted-data",
        action="store_true",
        help="Restrict eligible lanes to those explicitly authorized for restricted data in the project profile.",
    )
    parser.add_argument(
        "--unit-size",
        type=_parse_unit_size_arg,
        default=None,
        metavar="SIZE",
        help=f"Work unit size ({'|'.join(UNIT_SIZES)}) for pre-dispatch projected quota guard or --record-burn.",
    )
    parser.add_argument(
        "--safety-margin",
        type=_parse_safety_margin_arg,
        default=None,
        metavar="FLOAT",
        help=(
            f"Override automatic burn safety margin ({SAFETY_MARGIN_MIN_OVERRIDE:g} to "
            f"{SAFETY_MARGIN_MAX_OVERRIDE:g}) when --unit-size is specified."
        ),
    )
    parser.add_argument(
        "--record-burn",
        action="store_true",
        help="Record observed post-unit quota burn into provider-state.json (_calibration + live percentages).",
    )
    parser.add_argument(
        "--burn-provider",
        default=None,
        metavar="PROVIDER",
        help="Provider/pool for --record-burn (e.g. codex, claude, gemini, deepseek).",
    )
    parser.add_argument(
        "--burn-model",
        default=None,
        metavar="MODEL",
        help="Model ID for --record-burn (e.g. gpt-6.2-sol, claude-opus-5-5).",
    )
    parser.add_argument(
        "--burn-effort",
        default="medium",
        metavar="EFFORT",
        help="Effort level for --record-burn (default: medium).",
    )
    parser.add_argument(
        "--before-5h",
        type=_parse_pct_arg,
        default=None,
        metavar="PCT",
        help="Observed five_hour_pct before running the unit (paired with --after-5h).",
    )
    parser.add_argument(
        "--after-5h",
        type=_parse_pct_arg,
        default=None,
        metavar="PCT",
        help="Observed five_hour_pct after running the unit (paired with --before-5h).",
    )
    parser.add_argument(
        "--before-weekly",
        type=_parse_pct_arg,
        default=None,
        metavar="PCT",
        help="Observed weekly_pct before running the unit (paired with --after-weekly).",
    )
    parser.add_argument(
        "--after-weekly",
        type=_parse_pct_arg,
        default=None,
        metavar="PCT",
        help="Observed weekly_pct after running the unit (paired with --before-weekly).",
    )
    parser.add_argument(
        "--reset-occurred",
        action="store_true",
        help="Indicate a quota window reset occurred during the unit; skip EWMA update while still writing live after percentages.",
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


def dispatch_ok(recommended):
    """True only when a lane is recommended and neither its pool nor its projection is past the move mark.

    Overflowing lanes (projected >= 95%) never become the recommendation; they are excluded and
    reported as blocked. A recommendation that is `deprioritized` or `projected-deprioritized`
    means: do not dispatch new units to that pool (take the next ladder step or wait for the reset).
    """
    if not isinstance(recommended, dict):
        return False
    return not (
        recommended.get("deprioritized")
        or recommended.get("projected_deprioritized")
        or recommended.get("projected_overflow")
        or recommended.get("pool_state") == "blocked"
    )


def resolve_from_paths(
    *,
    workspace=Path("."),
    measurements_path=None,
    state_path=None,
    profile_path=None,
    role="coding",
    author_family=None,
    allowed_providers=None,
    restricted_data=False,
    now=None,
    stale_minutes=DEFAULT_STALE_MINUTES,
    cohort=None,
    unit_size=None,
    safety_margin=None,
):
    """Load files from disk and return the structured lane resolution report dict."""
    _validate_stale_minutes(stale_minutes)
    norm_unit_size = _validate_unit_size(unit_size) if unit_size is not None else None
    norm_safety_margin = _validate_safety_margin(safety_margin) if safety_margin is not None else None
    ws = Path(workspace)
    if not ws.exists() or not ws.is_dir():
        raise ValueError(f"Workspace directory does not exist: {ws}")

    p_path = Path(profile_path) if profile_path is not None else ws / WORKSPACE_PROFILE
    if profile_path is not None and not p_path.is_file():
        raise ValueError(f"Project profile does not exist: {p_path}")
    authorized_lanes = parse_authorized_lanes(p_path.read_text(encoding="utf-8")) if p_path.is_file() else None

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
    calibration = empty_calibration()

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
        except (json.JSONDecodeError, RecursionError) as err:
            raise ValueError(f"Invalid JSON in {resolved_state_path}: {err}") from err
        provider_states, state_warnings = parse_provider_state(raw_state, eval_now, stale_minutes)
        calibration = parse_calibration(raw_state)
        state_loaded = True
    else:
        state_warnings.append(
            "No provider-state.json found. Availability is unverified and quota headroom is unknown."
        )

    meas_text = m_path.read_text(encoding="utf-8")
    historical = parse_historical_candidates(meas_text)
    workspace_obs = parse_workspace_observations(meas_text)
    candidates = merge_candidates(historical, workspace_obs)

    norm_allowed = (
        list(dict.fromkeys(normalize_pool(p) for p in allowed_providers))
        if allowed_providers is not None
        else None
    )

    result = resolve_lanes(
        candidates,
        provider_states,
        role=role,
        author_family=author_family,
        allowed_providers=norm_allowed,
        authorized_lanes=authorized_lanes,
        restricted_data=restricted_data,
        state_loaded=state_loaded,
        state_warnings=state_warnings,
        cohort=cohort,
        unit_size=norm_unit_size,
        safety_margin=norm_safety_margin,
        calibration=calibration,
    )

    return {
        "role": role,
        "scoring_method": scoring_description(role),
        "equivalence_threshold_points": EQUIVALENCE_POINTS,
        "top_score": result["top_score"],
        "score_basis": result["score_basis"],
        "score_cohort": result["score_cohort"],
        "cross_family_anchored": result["cross_family_anchored"],
        "unit_size": result["unit_size"],
        "safety_margin": result["safety_margin"],
        "author_family": normalize_family(author_family) if author_family else None,
        "restricted_data": bool(restricted_data),
        "allowed_providers": norm_allowed,
        "evaluated_at": format_iso_utc(eval_now),
        "stale_minutes": stale_minutes,
        "measurements_path": str(m_path),
        "state_path": str(resolved_state_path) if resolved_state_path is not None else None,
        "profile_path": str(p_path) if p_path.is_file() else None,
        "advisory": authorized_lanes is None,
        "candidate_counts": {
            "historical": len(historical),
            "workspace": len(workspace_obs),
            "total": len(candidates),
        },
        "warnings": result["warnings"],
        "providers": provider_states,
        "recommended": result["recommended"],
        "dispatch_ok": dispatch_ok(result["recommended"]),
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

    if args.record_burn:
        if not args.burn_provider:
            parser.error("--burn-provider is required with --record-burn.")
        if not args.burn_model:
            parser.error("--burn-model is required with --record-burn.")
        if args.unit_size is None:
            parser.error("--unit-size is required with --record-burn.")
        if (args.before_5h is None) != (args.after_5h is None):
            parser.error("--before-5h and --after-5h must be provided together.")
        if (args.before_weekly is None) != (args.after_weekly is None):
            parser.error("--before-weekly and --after-weekly must be provided together.")
        if args.before_5h is None and args.before_weekly is None:
            parser.error(
                "--record-burn requires at least one metric pair "
                "(--before-5h/--after-5h or --before-weekly/--after-weekly)."
            )

        if args.state is not None:
            target_state = args.state
        else:
            ws = Path(args.workspace)
            if not ws.exists() or not ws.is_dir():
                parser.exit(1, f"Burn recording failed: Workspace directory does not exist: {ws}\n")
            target_state = ws / WORKSPACE_STATE

        try:
            summary = record_burn(
                target_state,
                provider=args.burn_provider,
                model=args.burn_model,
                effort=args.burn_effort,
                unit_size=args.unit_size,
                before_5h=args.before_5h,
                after_5h=args.after_5h,
                before_weekly=args.before_weekly,
                after_weekly=args.after_weekly,
                reset_occurred=args.reset_occurred,
                now=eval_now,
            )
        except (ValueError, OSError, OverflowError, RecursionError) as err:
            parser.exit(1, f"Burn recording failed: {err}\n")

        if args.format == "json":
            print(json.dumps(summary, indent=2, ensure_ascii=True))
        else:
            print(render_record_burn_markdown(summary), end="")
        return 0

    if (
        args.burn_provider is not None
        or args.burn_model is not None
        or args.before_5h is not None
        or args.after_5h is not None
        or args.before_weekly is not None
        or args.after_weekly is not None
        or args.reset_occurred
    ):
        parser.error("--burn-provider, --burn-model, --before-*, --after-*, and --reset-occurred require --record-burn.")

    try:
        report = resolve_from_paths(
            workspace=args.workspace,
            measurements_path=args.measurements,
            state_path=args.state,
            profile_path=args.profile,
            role=args.role,
            author_family=args.author_family,
            allowed_providers=args.providers,
            restricted_data=args.restricted_data,
            now=eval_now,
            stale_minutes=args.stale_minutes,
            cohort=args.cohort,
            unit_size=args.unit_size,
            safety_margin=args.safety_margin,
        )
    except (ValueError, OSError, OverflowError, RecursionError) as err:
        parser.exit(1, f"Lane resolution failed: {err}\n")

    if args.format == "json":
        print(json.dumps(report, indent=2, ensure_ascii=True))
    else:
        print(render_markdown(report), end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
