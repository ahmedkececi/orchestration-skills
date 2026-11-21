"""Validate benchmark checklists and render the archived suite as a live matrix."""

from collections import defaultdict
from pathlib import Path
import statistics

from catalogs import fields, https_urls, identifier, read_json, rows, valid_date


SUITE = read_json(Path(__file__).resolve().parents[1] / "references" / "benchmark-suite.json")
UNITS = {test["metric"]: test["unit"] for test in SUITE}


def normalize_check(row):
    fields(row, "model effort date checked sources", "Benchmark check")
    identifier(row["model"], "benchmark model ID")
    identifier(row["effort"], "benchmark effort")
    if not valid_date(row["date"]):
        raise ValueError("Each benchmark check needs an ISO date.")
    checked = rows(row["checked"], "Checked metric IDs")
    if len(checked) != len(UNITS) or set(checked) != UNITS.keys():
        raise ValueError("Each benchmark check must account for every metric in benchmark-suite.json.")
    if rows(row["sources"], "Benchmark sources"):
        https_urls(row["sources"], "Benchmark sources")
    return {**row, "checked": list(UNITS)}


def require_coverage(data, eligible):
    covered = {(row["model"], row["effort"]) for row in data["benchmark_checks"]}
    covered_models = {model for model, _ in covered}
    if covered_models - eligible:
        raise ValueError("Benchmark checks include a model outside the verified refresh scope.")
    if eligible - covered_models:
        raise ValueError("Missing benchmark checklist for: " + ", ".join(sorted(eligible - covered_models)))
    for row in data["measurements"]:
        variant = (row["model"], row["effort"])
        if variant not in covered:
            raise ValueError(f"Missing benchmark checklist for {variant[0]} at {variant[1]} effort.")
        expected = UNITS.get(row["metric"])
        if expected and row["unit"] != expected:
            raise ValueError(f"{row['metric']} must use the {expected} unit.")


def matrix(data, grouped):
    checks = {(row["model"], row["effort"]): row for row in data["benchmark_checks"]}
    cells = defaultdict(lambda: defaultdict(list))
    variants = set(checks)
    for (model, effort, metric, cohort, unit), observations in sorted(grouped.items()):
        key = (model, effort)
        variants.add(key)
        if UNITS.get(metric) != unit:
            continue
        average = statistics.fmean(row["value"] for row in observations)
        suffix = "%" if unit == "percent" else " Elo"
        cells[key][metric].append(f"{average:.10g}{suffix} (`{cohort}`)")
    represented = {model for model, _ in variants}
    variants.update((row["model"], "unspecified") for row in data["models"] if row["model"] not in represented)
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
        model, effort = key
        check = checks.get(key)
        date = check["date"] if check else "-"
        values = ["<br>".join(cells[key][metric]) or "-" for metric in UNITS]
        lines.append("| " + " | ".join([f"`{model}`", effort, date, *values]) + " |")
    if checks:
        lines.extend(["", "Benchmark sources checked in the latest lookup for each variant:"])
        for (model, effort), check in sorted(checks.items()):
            sources = ", ".join(f"<{url}>" for url in check["sources"]) or "-"
            lines.append(f"- `{model}` (`{effort}`): {sources}")
    return lines
