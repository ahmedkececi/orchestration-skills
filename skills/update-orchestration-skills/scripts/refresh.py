"""Merge sourced model observations into one workspace Markdown file."""

import argparse
from collections import defaultdict
import json
import math
from pathlib import Path
import statistics

from benchmarks import matrix, normalize_check, require_coverage, validate_metric_unit
from catalogs import (
    IDENTIFIER, official_url, read_json, registry, safe_output, valid_date, valid_url,
    validate_provider, verify_scan, workspace_path, write_atomic,
)


SKILL = Path(__file__).resolve().parents[1]
BASELINE = SKILL / "references" / "model-measurements.md"
DESTINATION = Path(".orchestration/model-measurements.md")
DELIMITER = "\n<!-- workspace-measurements:v1 -->\n"
STATE_START = "\n<!-- observations:start -->\n```json\n"
STATE_END = "\n```\n<!-- observations:end -->"
UNITS = {"points", "percent", "elo", "seconds", "usd", "tokens"}
KEYS = {
    "models": ("model",),
    "benchmark_checks": ("model", "effort"),
    "measurements": ("model", "effort", "metric", "cohort", "unit", "source"),
}


def normalize(payload):
    if not isinstance(payload, dict) or payload.keys() - KEYS.keys():
        raise ValueError("Expected a JSON object with models, measurements and/or benchmark_checks arrays.")
    data = {}
    for group, key_fields in KEYS.items():
        rows = payload.get(group, [])
        if not isinstance(rows, list):
            raise ValueError(f"{group} must be an array.")
        if group == "benchmark_checks":
            data[group] = [normalize_check(row) for row in rows]
            keys = {(row["model"], row["effort"]) for row in data[group]}
            if len(keys) != len(rows):
                raise ValueError("Duplicate benchmark check for the same model and effort.")
            continue
        entries = []
        seen_keys = set()
        for row in rows:
            if not isinstance(row, dict):
                raise ValueError(f"Each {group} row must be an object.")
            extra = ("provider", "released", "url") if group == "models" else ("date", "value", "url")
            required = set(key_fields + extra)
            if row.keys() != required:
                raise ValueError(f"In {group}, expected fields {', '.join(sorted(required))}.")
            identifiers = ("model", "provider") if group == "models" else key_fields
            if not all(isinstance(row[key], str) and IDENTIFIER.fullmatch(row[key]) for key in identifiers):
                raise ValueError(f"Invalid identifier in {group}: {row.get('model')!r}.")
            if not valid_url(row["url"]):
                raise ValueError("Each row requires an HTTPS source URL without credentials.")
            key = tuple(row[field] for field in key_fields)
            if key in seen_keys:
                raise ValueError(f"Duplicate {group} entry for {row['model']!r}.")
            seen_keys.add(key)
            if group == "models":
                if row["released"] is not None and not valid_date(row["released"]):
                    raise ValueError("released must be an ISO date or null.")
            else:
                if not valid_date(row["date"]) or row["unit"] not in UNITS:
                    raise ValueError("Each measurement needs an ISO date and a supported unit.")
                validate_metric_unit(row["metric"], row["unit"])
                value = row["value"]
                if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
                    raise ValueError("Measurements must be finite, nonnegative numbers.")
                if row["unit"] == "percent" and value > 100:
                    raise ValueError("A percentage must be between 0 and 100.")
                if isinstance(value, float) and value == 0.0:
                    row = {**row, "value": 0.0}
            entries.append(row)
        data[group] = entries
    return data


def merge(previous, incoming):
    merged = {}
    for group, fields in KEYS.items():
        rows = {}
        for row in previous[group] + incoming[group]:
            key = tuple(row[field] for field in fields)
            old = rows.get(key)
            if group in ("measurements", "benchmark_checks") and old and row["date"] < old["date"]:
                continue
            if group == "models" and old and row["provider"].lower() != old["provider"].lower():
                raise ValueError(f"Conflicting providers for {row['model']}. Use qualified model IDs.")
            if group == "models" and old and row["released"] is None:
                row = {**row, "released": old["released"]}
            rows[key] = row
        merged[group] = [row for _, row in sorted(rows.items())]
    return merged


def source_link(row):
    return f'<{row["url"]}>'


def display(value):
    return format(value, ".10g")


def render(baseline, data, audit):
    lines = [
        "## Live workspace measurements",
        "",
        "Averages use each reported source once per exact model, effort, metric, "
        "unit and cohort. Compare rows only on a shared cohort and matched evidence. "
        "Missing values remain unknown.",
        "",
        "### Model releases",
        "",
        "| Exact model ID | Provider | Release date | Source |",
        "| --- | --- | --- | --- |",
    ]
    for row in data["models"]:
        lines.append(
            f'| `{row["model"]}` | {row["provider"]} | '
            f'{row["released"] or "Unknown"} | {source_link(row)} |'
        )

    grouped = defaultdict(list)
    for row in data["measurements"]:
        key = tuple(row[k] for k in ("model", "effort", "metric", "cohort", "unit"))
        grouped[key].append(row)
    lines.extend(matrix(data, grouped))
    if data["measurements"]:
        lines += [
            "",
            "### Scores and profile averages",
            "",
            "| Model | Effort | Metric | Cohort | Unit | Mean | n | Range | Latest |",
            "| --- | --- | --- | --- | --- | ---: | ---: | --- | --- |",
        ]
        for (model, effort, metric, cohort, unit), rows in sorted(grouped.items()):
            values = [row["value"] for row in rows]
            latest = max(row["date"] for row in rows)
            lines.append(
                f"| `{model}` | {effort} | {metric} | {cohort} | {unit} | "
                f"{display(statistics.fmean(values))} | {len(values)} | "
                f"{display(min(values))}–{display(max(values))} | {latest} |"
            )
        lines += [
            "",
            "### Source observations",
            "",
            "| Model | Effort | Metric | Cohort | Value | Unit | Date | Source |",
            "| --- | --- | --- | --- | ---: | --- | --- | --- |",
        ]
        for row in data["measurements"]:
            lines.append(
                f'| `{row["model"]}` | {row["effort"]} | {row["metric"]} | {row["cohort"]} | '
                f'{display(row["value"])} | {row["unit"]} | {row["date"]} | '
                f'{row["source"]} {source_link(row)} |'
            )
    state_data = data.copy()
    if audit is not None:
        lines.extend(render_audit(audit))
        state_data["catalog_audit"] = audit
    state = json.dumps(state_data, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False)
    return baseline.rstrip() + "\n" + DELIMITER + "\n".join(lines) + "\n" + STATE_START + state + STATE_END + "\n"


def read_previous(path):
    if not path.exists():
        return BASELINE.read_text(encoding="utf-8"), normalize({}), None
    baseline, separator, generated = path.read_text(encoding="utf-8").partition(DELIMITER)
    if not separator or generated.count(STATE_START) != 1 or not generated.rstrip().endswith(STATE_END):
        raise ValueError(f"{path} is not a recognized generated snapshot. Move or repair it before refreshing.")
    state = generated.split(STATE_START, 1)[1].rsplit(STATE_END, 1)[0]
    stored = json.loads(state)
    audit = stored.pop("catalog_audit", None)
    return baseline, normalize(stored), audit


def render_audit(audit):
    status = "complete against registered sources" if audit["complete"] else "incomplete"
    lines = ["", "### Latest catalog check", "", f'{audit["checked_on"]} · Coverage {status}.']
    if "selected_models" in audit:
        choices = ", ".join(f"`{model}`" for model in audit["selected_models"]) or "none"
        lines.append(f"Selected for this refresh: {choices}.")
    if audit["missing_providers"]:
        lines.append("Unchecked providers: " + ", ".join(audit["missing_providers"]) + ".")
    lines.append("")
    for row in audit["providers"]:
        state = "complete" if row["complete"] else "incomplete"
        lines.append(f'- **{row["id"]}** · {state}. Newer releases verified: {row["newer_releases"]}.')
        for url, source_state in row["sources"].items():
            lines.append(f"  - {source_state} · <{url}>")
        for anchor in row["anchors"]:
            lines.append(f'  - Reference `{anchor["model"]}` · {anchor["released"]} · {source_link(anchor)}')
        if row["missing_anchors"]:
            names = ", ".join(row["missing_anchors"])
            lines.append(f"  - Missing dates for skill reference models: {names}.")
        if row["unresolved"]:
            names = ", ".join(row["unresolved"])
            lines.append(f"  - Unresolved model IDs or release order: {names}.")
    return lines


def catalog_selection(args, providers, incoming):
    if incoming["models"]:
        raise ValueError("In catalog mode, model records come from the verified report.")
    result = verify_scan(read_json(args.catalog_report), providers)
    discovered = {row["model"]: row for row in result["models"]}
    selected = unique_choices(args.select)
    if discovered and not selected:
        raise ValueError("No model selected. Show the verified model list and wait for the user's choice.")
    if selected - discovered.keys():
        raise ValueError("Selections are not in the verified catalog report: " + ", ".join(sorted(selected - discovered.keys())))
    incoming["models"] = [row for model, row in discovered.items() if model in selected]
    audit = result["audit"]
    audit["selected_models"] = sorted(selected)
    return audit


def unique_choices(values):
    choices = set(values or ())
    if values and len(choices) != len(values):
        raise ValueError("The same model ID was selected more than once.")
    return choices


def validate_named_selection(args, providers, local, incoming):
    chosen = unique_choices(args.model)
    supplied = {row["model"] for row in incoming["models"]}
    if len(incoming["models"]) != len(chosen) or chosen != supplied:
        raise ValueError("Supply one documented release record for every selected exact model ID, and no extra model records.")

    entry = None
    if args.provider_entry:
        draft = validate_provider(read_json(args.provider_entry))
        local_by_id = {item["id"]: item for item in local}
        if draft["id"] in providers:
            registered = local_by_id.get(draft["id"])
            if registered is None:
                raise ValueError(f"{draft['id']} is a built-in provider; do not pass --provider-entry.")
            if registered != draft:
                raise ValueError(f"Provider entry for {draft['id']} does not match the registered provider.")
            entry = registered
        elif not args.preview:
            raise ValueError("Register the chosen provider before writing its measurements.")
        else:
            entry = draft
    elif len(chosen) != 1:
        raise ValueError("A named refresh accepts one model. Use a provider entry for multiple models from that provider.")

    for model in incoming["models"]:
        provider_key = model["provider"].lower()
        if entry is not None and entry["id"] != provider_key:
            raise ValueError(f"{model['model']} is not in the chosen provider scope.")
        provider = entry or providers.get(provider_key)
        if provider and not official_url(model["url"], provider):
            raise ValueError(f"{model['model']} needs a release or model page from its provider.")


def scoped_input(args, workspace, incoming):
    if not (args.catalog_report or args.model):
        return None
    providers, local = registry(workspace)
    if args.catalog_report:
        audit = catalog_selection(args, providers, incoming)
    else:
        validate_named_selection(args, providers, local, incoming)
        audit = None
    eligible = {row["model"] for row in incoming["models"]}
    if any(row["model"] not in eligible for row in incoming["measurements"]):
        raise ValueError("Measurements include a model outside the verified refresh scope.")
    require_coverage(incoming, eligible)
    return audit


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, required=True, help="Explicit project root.")
    parser.add_argument("--input", help="Observation JSON file or - for stdin.")
    scope = parser.add_mutually_exclusive_group()
    scope.add_argument("--model", action="append", help="Import this exact model ID. Repeat with --provider-entry.")
    scope.add_argument("--catalog-report", help="Import chosen models from this verified catalog report.")
    parser.add_argument("--select", action="append", help="Exact model ID chosen from --catalog-report. Repeat for each choice.")
    parser.add_argument("--provider-entry", help="Provider registration JSON for a provider-scoped --model import.")
    parser.add_argument("--preview", action="store_true", help="Print the merged document without writing.")
    args = parser.parse_args()
    if args.select and not args.catalog_report:
        parser.error("--select requires --catalog-report.")
    if args.provider_entry and not args.model:
        parser.error("--provider-entry requires one or more --model choices.")
    if args.provider_entry and args.provider_entry == (args.input or "-"):
        parser.error("Use separate inputs for the provider entry and the observations.")
    if args.input == args.catalog_report == "-":
        parser.error("Only one of --input and --catalog-report can use stdin.")
    try:
        workspace = workspace_path(args.workspace)
        output = safe_output(workspace, DESTINATION)
        if args.catalog_report and args.input is None:
            incoming = normalize({})
        else:
            incoming = normalize(read_json(args.input or "-"))
        audit = scoped_input(args, workspace, incoming)
        if audit is None and not any(incoming.values()):
            raise ValueError("No verified release or measurement rows to import.")
        baseline, previous, prior_audit = read_previous(output)
        data = merge(previous, incoming)
        rendered = render(baseline, data, audit if audit is not None else prior_audit)
        if args.preview:
            print(rendered, end="")
        else:
            write_atomic(output, rendered)
            print(f"{output}: {len(data['models'])} releases, {len(data['measurements'])} observations.")
            if audit is not None:
                state = "complete against registered sources" if audit["complete"] else "incomplete"
                print(f"Catalog coverage: {state}. See the Latest catalog check section for details.")
    except (ValueError, OSError, TypeError, KeyError, OverflowError) as error:
        parser.exit(1, f"Refresh failed: {error}\n")


if __name__ == "__main__":
    main()
