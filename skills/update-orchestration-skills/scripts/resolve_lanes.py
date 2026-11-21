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

from refresh import normalize


SKILL_DIR = Path(__file__).resolve().parents[1]
BUNDLED_MEASUREMENTS = SKILL_DIR / "references" / "model-measurements.md"
WORKSPACE_MEASUREMENTS = Path(".orchestration/model-measurements.md")
WORKSPACE_STATE = Path(".orchestration/provider-state.json")
WORKSPACE_PROFILE = Path(".orchestration/project-profile.md")

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


def _shared_latencies(eligible):
    """Use timings only when the lanes tied on pre-latency sort keys all have matched measurements."""
    tied = defaultdict(list)
    for item in eligible:
        key = (
            item.get("same_family", False),
            item.get("deprioritized", False),
            item.get("stale", False),
            item.get("headroom"),
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
    seen_raw_keys = {}
    for raw_key, entry in raw_state.items():
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
):
    """Filter, score, classify (±3-pt equivalence), and deterministically rank lanes."""
    warnings = list(state_warnings or [])
    eligible = []
    excluded = []

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
                    "model": lane["model"] if lane else cand["model"],
                    "effort": cand["effort"],
                    "pool": pool,
                    "family": family,
                    "score": score,
                    "source": cand["source"],
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

        if mstate is not None and not (
            pstate is not None
            and not pstate["stale"]
            and pstate["status"] == "up"
            and _is_unconfigured_placeholder(mstate)
        ):
            if mstate["deprioritized"]:
                deprioritized = True
                effective_state = "deprioritized"
                state_reasons.extend(f"model {r}" for r in mstate["reasons"])
            if mstate["headroom"] is not None:
                headroom = mstate["headroom"] if headroom is None else min(headroom, mstate["headroom"])
            stale = stale or mstate["stale"]

        if stale:
            headroom = None
            if effective_state == "up":
                effective_state = "stale"

        same_family = bool(role == "review" and norm_author and family == norm_author)

        eligible.append(
            {
                "model": lane["model"] if lane else cand["model"],
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


def render_markdown(report):
    """Render lane resolution report as concise GitHub-flavored Markdown."""
    anchor_label = "top eligible cross-family score" if report.get("cross_family_anchored") else "top eligible score"
    lines = [
        f"# Lane resolution · {report['role']}",
        "",
        f"- **Role:** `{report['role']}` ({report['scoring_method']})",
        f"- **Equivalence band:** within ±{report['equivalence_threshold_points']:g} pts of {anchor_label} `{_fmt_num(report['top_score'])}`",
    ]
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
        lines.append(
            f"- **Recommended lane:** `{rec['model']}` (`{rec['effort']}`) · "
            f"pool `{rec['pool']}` · score `{_fmt_num(rec['score'])}` · "
            f"headroom `{headroom_str}`{flags_str}"
        )
        lines.append(f"- **Authorized runner:** {_md_cell(rec['runner'])}")
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
    profile_path=None,
    role="coding",
    author_family=None,
    allowed_providers=None,
    restricted_data=False,
    now=None,
    stale_minutes=DEFAULT_STALE_MINUTES,
    cohort=None,
):
    """Load files from disk and return the structured lane resolution report dict."""
    _validate_stale_minutes(stale_minutes)
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
    )

    return {
        "role": role,
        "scoring_method": scoring_description(role),
        "equivalence_threshold_points": EQUIVALENCE_POINTS,
        "top_score": result["top_score"],
        "score_basis": result["score_basis"],
        "score_cohort": result["score_cohort"],
        "cross_family_anchored": result["cross_family_anchored"],
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
            profile_path=args.profile,
            role=args.role,
            author_family=args.author_family,
            allowed_providers=args.providers,
            restricted_data=args.restricted_data,
            now=eval_now,
            stale_minutes=args.stale_minutes,
            cohort=args.cohort,
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
