"""Merge sourced model observations into one workspace Markdown file."""

import argparse
from collections import defaultdict
from datetime import date
import json
import math
import os
from pathlib import Path
import re
import statistics
import sys
from tempfile import NamedTemporaryFile
from urllib.parse import urlsplit


SKILL = Path(__file__).resolve().parents[1]
BASELINE = SKILL / "references" / "model-measurements.md"
DESTINATION = Path(".orchestration/model-measurements.md")
DELIMITER = "\n<!-- workspace-measurements:v1 -->\n"
STATE_START = "\n<!-- observations:start -->\n```json\n"
STATE_END = "\n```\n<!-- observations:end -->"
IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/+-]{0,127}")
UNITS = {"points", "percent", "elo", "seconds", "usd", "tokens"}
KEYS = {
    "models": ("model",),
    "measurements": ("model", "effort", "metric", "cohort", "unit", "source"),
}


def valid_date(value):
    return date.fromisoformat(value).isoformat() == value


def valid_url(value):
    url = urlsplit(value)
    return (
        url.scheme == "https"
        and bool(url.hostname)
        and not url.username
        and not url.password
        and re.search(r"[\s<>|\\]", value) is None
    )


def normalize(payload):
    if not isinstance(payload, dict) or payload.keys() - KEYS.keys():
        raise ValueError("Expected a JSON object with models and/or measurements arrays.")
    data = {}
    for group, key_fields in KEYS.items():
        rows = payload.get(group, [])
        if not isinstance(rows, list):
            raise ValueError(f"{group} must be an array.")
        entries = []
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
            if group == "models":
                if row["released"] is not None and not valid_date(row["released"]):
                    raise ValueError("released must be an ISO date or null.")
            else:
                if not valid_date(row["date"]) or row["unit"] not in UNITS:
                    raise ValueError("Each measurement needs an ISO date and a supported unit.")
                value = row["value"]
                if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
                    raise ValueError("Measurements must be finite, nonnegative numbers.")
                if row["unit"] == "percent" and value > 100:
                    raise ValueError("A percentage must be between 0 and 100.")
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
            if group == "measurements" and old and row["date"] < old["date"]:
                continue
            if group == "models" and old and row["released"] is None:
                row = {**row, "released": old["released"]}
            rows[key] = row
        merged[group] = [row for _, row in sorted(rows.items())]
    return merged


def source_link(row):
    return f'<{row["url"]}>'


def display(value):
    return format(value, ".10g")


def render(baseline, data):
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
    state = json.dumps(data, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False)
    return baseline.rstrip() + "\n" + DELIMITER + "\n".join(lines) + "\n" + STATE_START + state + STATE_END + "\n"


def read_previous(path):
    if not path.exists():
        return BASELINE.read_text(encoding="utf-8"), normalize({})
    baseline, separator, generated = path.read_text(encoding="utf-8").partition(DELIMITER)
    if not separator or generated.count(STATE_START) != 1 or not generated.rstrip().endswith(STATE_END):
        raise ValueError(f"{path} is not a recognized generated snapshot. Move or repair it before refreshing.")
    state = generated.split(STATE_START, 1)[1].rsplit(STATE_END, 1)[0]
    return baseline, normalize(json.loads(state))


def write_atomic(path, contents):
    path.parent.mkdir(exist_ok=True)
    with NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as file:
        temp = Path(file.name)
        try:
            file.write(contents)
            file.close()
            os.replace(temp, path)
        finally:
            temp.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, required=True, help="Explicit project root.")
    parser.add_argument("--input", default="-", help="JSON input file, or - for stdin.")
    parser.add_argument("--preview", action="store_true", help="Print the merged document without writing.")
    args = parser.parse_args()
    try:
        workspace = args.workspace.resolve(strict=True)
        if not workspace.is_dir():
            raise ValueError("The workspace must be a directory.")
        output = workspace / DESTINATION
        if output.is_symlink() or output.parent.is_symlink():
            raise ValueError("The workspace measurement path may not use symlinks.")
        incoming_text = sys.stdin.read() if args.input == "-" else Path(args.input).read_text(encoding="utf-8")
        incoming = normalize(json.loads(incoming_text))
        if not any(incoming.values()):
            raise ValueError("No verified release or measurement rows to import.")
        baseline, previous = read_previous(output)
        data = merge(previous, incoming)
        rendered = render(baseline, data)
        if args.preview:
            print(rendered, end="")
        else:
            write_atomic(output, rendered)
            print(f"{output}: {len(data['models'])} releases, {len(data['measurements'])} observations.")
    except (ValueError, OSError, TypeError, OverflowError) as error:
        parser.exit(1, f"Refresh failed: {error}\n")


if __name__ == "__main__":
    main()
