"""Validate benchmark checklists and render the archived suite as a live matrix."""

from collections import defaultdict
from pathlib import Path
import statistics

from catalogs import fields, https_urls, identifier, read_json, rows, valid_date


SUITE = read_json(Path(__file__).resolve().parents[1] / "references" / "benchmark-suite.json")
UNITS = {test["metric"]: test["unit"] for test in SUITE}
SUITE_BY_LOWER = {metric.lower(): metric for metric in UNITS}
PROFILE_METRIC_UNITS = {
    "coding": "points",
    "reasoning": "points",
    "accuracy": "points",
    "knowledge": "points",
    "knowledge-work": "points",
    "knowledge_work": "points",
    "review": "points",
    "seconds-per-task": "seconds",
    "s-per-task": "seconds",
    "latency-seconds": "seconds",
    "estimated-seconds-per-task": "seconds",
}
UNIT_SUFFIXES = {
    "percent": "%",
    "elo": " Elo",
    "points": " pts",
    "seconds": " s",
    "usd": " USD",
    "tokens": " tok",
}


def validate_metric_unit(metric, unit, *, strict_profiles=True):
    low = metric.lower()
    expected = UNITS.get(metric) or UNITS.get(low)
    if expected and unit != expected:
        raise ValueError(f"{metric} must use the {expected} unit.")
    if strict_profiles:
        expected_profile = PROFILE_METRIC_UNITS.get(low)
        if expected_profile and unit != expected_profile:
            raise ValueError(f"{metric} must use the {expected_profile} unit.")


def normalize_check(row):
    fields(row, "model effort date checked sources", "Benchmark check")
    identifier(row["model"], "benchmark model ID")
    identifier(row["effort"], "benchmark effort")
    if not valid_date(row["date"]):
        raise ValueError("Each benchmark check needs an ISO date.")
    checked = rows(row["checked"], "Checked metric IDs")
    if (
        not all(isinstance(item, str) for item in checked)
        or len(checked) != len(UNITS)
        or set(checked) != UNITS.keys()
    ):
        raise ValueError("Each benchmark check must account for every metric in benchmark-suite.json.")
    if rows(row["sources"], "Benchmark sources"):
        https_urls(row["sources"], "Benchmark sources")
    return {**row, "checked": list(UNITS)}


def require_coverage(data, eligible):
    eligible_ci = {model.lower(): model for model in eligible}
    covered = {(row["model"].lower(), row["effort"].lower()) for row in data["benchmark_checks"]}
    covered_models = {model for model, _ in covered}
    if covered_models - eligible_ci.keys():
        raise ValueError("Benchmark checks include a model outside the verified refresh scope.")
    missing = [eligible_ci[m] for m in sorted(eligible_ci.keys() - covered_models)]
    if missing:
        raise ValueError("Missing benchmark checklist for: " + ", ".join(missing))
    for row in data["measurements"]:
        variant = (row["model"].lower(), row["effort"].lower())
        if variant not in covered:
            raise ValueError(f"Missing benchmark checklist for {row['model']} at {row['effort']} effort.")
        validate_metric_unit(row["metric"], row["unit"])


def _pick_label(values, preferred_lower):
    if not values:
        return preferred_lower
    return preferred_lower if preferred_lower in values else min(values)


def matrix(data, grouped):
    model_labels = {row["model"].lower(): row["model"] for row in data["models"]}
    checks = {}
    variant_labels = {}
    for row in data["benchmark_checks"]:
        key = (row["model"].lower(), row["effort"].lower())
        checks[key] = row
        variant_labels[key] = (model_labels.get(key[0], row["model"]), row["effort"])

    merged_groups = defaultdict(list)
    for (model, effort, metric, cohort, unit), observations in grouped.items():
        ci_key = (model.lower(), effort.lower(), metric.lower(), cohort.lower(), unit)
        merged_groups[ci_key].extend(observations)

    cells = defaultdict(lambda: defaultdict(list))
    variants = set(checks)
    for (model_k, effort_k, metric_k, cohort_k, unit), observations in sorted(merged_groups.items()):
        key = (model_k, effort_k)
        variants.add(key)
        if key not in variant_labels:
            disp_model = model_labels.get(model_k) or _pick_label({obs["model"] for obs in observations}, model_k)
            disp_effort = _pick_label({obs["effort"] for obs in observations}, effort_k)
            variant_labels[key] = (disp_model, disp_effort)
        canonical_metric = SUITE_BY_LOWER.get(metric_k)
        if canonical_metric is None or UNITS[canonical_metric] != unit:
            continue
        average = statistics.fmean(row["value"] for row in observations)
        suffix = UNIT_SUFFIXES.get(unit, f" {unit}")
        disp_cohort = _pick_label({obs["cohort"] for obs in observations}, cohort_k)
        cells[key][canonical_metric].append(f"{average:.10g}{suffix} (`{disp_cohort}`)")

    represented = {model_k for model_k, _ in variants}
    for row in data["models"]:
        model_k = row["model"].lower()
        if model_k not in represented:
            key = (model_k, "unspecified")
            variants.add(key)
            variant_labels[key] = (row["model"], "unspecified")
    if not variants:
        return []

    header = ["Model", "Effort", "Checked on", *(test["column"] for test in SUITE)]
    lines = [
        "",
        "### Benchmark coverage by model and effort",
        "",
        "A dash (-) means no verified result for this exact test version and effort "
        "in this workspace. Scores from different cohorts are shown separately. "
        "The source observations below provide the measurements and their dates.",
        "",
        "| " + " | ".join(header) + " |",
        "| " + " | ".join("---" for _ in header) + " |",
    ]
    for key in sorted(variants):
        disp_model, disp_effort = variant_labels[key]
        check = checks.get(key)
        date = check["date"] if check else "-"
        values = ["<br>".join(cells[key][metric]) or "-" for metric in UNITS]
        lines.append("| " + " | ".join([f"`{disp_model}`", disp_effort, date, *values]) + " |")
    if checks:
        lines.extend(["", "Benchmark sources checked in the latest lookup for each variant:"])
        for key, check in sorted(checks.items()):
            disp_model, disp_effort = variant_labels[key]
            sources = ", ".join(f"<{url}>" for url in check["sources"]) or "-"
            lines.append(f"- `{disp_model}` (`{disp_effort}`): {sources}")
    return lines
