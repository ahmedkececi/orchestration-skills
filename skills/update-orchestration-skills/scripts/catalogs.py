"""Plan and validate model catalog checks, or register a workspace provider."""

import argparse
from datetime import date
import json
import os
from pathlib import Path
import re
import sys
from tempfile import NamedTemporaryFile
from urllib.parse import urlsplit


BUILTIN = Path(__file__).resolve().parents[1] / "references" / "provider-catalogs.json"
REGISTRY = Path(".orchestration/provider-catalogs.json")
IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/+-]{0,127}")
SLUG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
ENV_NAME = re.compile(r"[A-Z][A-Z0-9_]{2,63}")
SOURCE_STATES = {"read", "partial", "unavailable"}


def valid_date(value):
    return isinstance(value, str) and date.fromisoformat(value).isoformat() == value


def valid_url(value):
    if not isinstance(value, str) or re.search(r"[\s<>|\\]", value):
        return False
    url = urlsplit(value)
    return url.scheme == "https" and bool(url.hostname) and not url.username and not url.password


def read_json(path):
    return json.loads(sys.stdin.read() if path == "-" else Path(path).read_text(encoding="utf-8"))


def workspace_path(path):
    root = path.resolve(strict=True)
    if not root.is_dir():
        raise ValueError("The workspace must be a directory.")
    return root


def safe_output(workspace, relative):
    output = workspace / relative
    if output.is_symlink() or output.parent.is_symlink():
        raise ValueError(f"{relative} may not use symlinks.")
    return output


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


def fields(value, expected, context):
    if not isinstance(value, dict) or value.keys() != set(expected.split()):
        raise ValueError(f"{context} requires: {expected}.")


def rows(value, context):
    if not isinstance(value, list):
        raise ValueError(f"{context} must be a list.")
    return value


def identifier(value, context, pattern=IDENTIFIER):
    if not isinstance(value, str) or not pattern.fullmatch(value):
        raise ValueError(f"Invalid {context}: {value!r}.")
    return value


def https_urls(value, context):
    if not rows(value, context) or not all(valid_url(url) for url in value):
        raise ValueError(f"{context} requires public HTTPS documentation URLs.")
    if len(set(value)) != len(value):
        raise ValueError(f"{context} contains duplicate URLs.")
    return value


def validate_provider(entry):
    fields(entry, "id catalogs release_notes usage_docs since runtime", "Provider")
    identifier(entry["id"], "provider ID", SLUG)
    for key in ("catalogs", "release_notes", "usage_docs"):
        https_urls(entry[key], key)
    if not valid_date(entry["since"]):
        raise ValueError("The provider requires an ISO date in since.")
    runtime = entry["runtime"]
    fields(runtime, "mode entrypoint auth credential_env model", "Provider runtime")
    mode = runtime["mode"]
    identifier(runtime["model"], "documented example model ID")
    if mode == "api":
        if not valid_url(runtime["entrypoint"]):
            raise ValueError("An API entry point requires a public HTTPS URL.")
    elif mode in ("cli", "managed-client"):
        identifier(runtime["entrypoint"], "runner name")
    else:
        raise ValueError("Use api, cli or managed-client for runtime.mode.")
    if runtime["auth"] not in ("api-key", "oauth", "account-session", "platform-managed", "none"):
        raise ValueError("Use a documented runtime authentication mode.")
    if runtime["credential_env"] is not None:
        identifier(runtime["credential_env"], "credential environment variable name", ENV_NAME)
    return entry


def registry(workspace):
    builtin = read_json(BUILTIN)
    providers = {
        entry["id"]: {**entry, "since": builtin["baseline_date"]}
        for entry in builtin["providers"]
    }
    path = safe_output(workspace, REGISTRY)
    local = []
    if path.exists():
        stored = read_json(path)
        fields(stored, "version providers", "Provider registry")
        if stored["version"] != 1:
            raise ValueError("Unsupported provider registry version.")
        for entry in rows(stored["providers"], "Workspace providers"):
            validate_provider(entry)
            if entry["id"] in providers:
                raise ValueError(f"Duplicate or built-in provider: {entry['id']}.")
            local.append(entry)
            providers[entry["id"]] = {**entry, "anchors": {}}
    return providers, local


def official_url(url, provider):
    urls = provider["catalogs"] + provider["release_notes"] + provider.get("usage_docs", [])
    hosts = {urlsplit(u).hostname for u in urls} | set(provider.get("official_hosts", []))
    return valid_url(url) and urlsplit(url).hostname in hosts


def verify_scan(report, providers):
    fields(report, "checked_on providers", "Catalog report")
    as_of = report["checked_on"]
    if not valid_date(as_of):
        raise ValueError("checked_on must be an ISO date.")
    scanned = {}
    selected = {}
    for scan in rows(report["providers"], "Provider reports"):
        fields(scan, "id sources anchors releases", "Provider report")
        pid = identifier(scan["id"], "provider ID", SLUG)
        if pid not in providers or pid in scanned:
            raise ValueError(f"Unknown or duplicated scan provider: {pid}.")
        provider = providers[pid]
        expected_urls = set(provider["catalogs"] + provider["release_notes"])
        expected_anchors = provider["anchors"]
        baseline_ids = set(expected_anchors.values())
        sources = {}
        seen = set()
        for source in rows(scan["sources"], "Sources"):
            fields(source, "url status seen", "Source audit")
            url, status = source["url"], source["status"]
            if url not in expected_urls or url in sources or status not in SOURCE_STATES:
                raise ValueError(f"Unknown, invalid or duplicated source audit for {pid}.")
            ids = {identifier(model, "model ID") for model in rows(source["seen"], "Seen model IDs")}
            if status == "unavailable" and ids:
                raise ValueError(f"Unavailable source {url} cannot report observed IDs.")
            sources[url] = status
            seen.update(ids - baseline_ids)

        anchors = {}
        anchor_evidence = []
        for row in rows(scan["anchors"], "Anchors"):
            fields(row, "family model released url", "Anchor")
            family = identifier(row["family"], "model family", SLUG)
            if family in anchors or expected_anchors.get(family) != row["model"]:
                raise ValueError(f"Unexpected or duplicated release anchor {pid}/{family}.")
            if not valid_date(row["released"]) or row["released"] > as_of or not official_url(row["url"], provider):
                raise ValueError(f"Invalid date or source for anchor {pid}/{family}.")
            anchors[family] = row["released"]
            anchor_evidence.append(row)

        releases = {}
        unresolved = set()
        count = 0
        for row in rows(scan["releases"], "Releases"):
            fields(row, "model family released url", "Release")
            model = identifier(row["model"], "model ID")
            family = identifier(row["family"], "model family", SLUG)
            if family not in expected_anchors and family not in ("other", "unknown"):
                raise ValueError(f"Unrecognized model family {pid}/{family}. Use other or unknown.")
            if not official_url(row["url"], provider) or model in releases:
                raise ValueError(f"Release {model} needs a unique record and an official source.")
            released = row["released"]
            if released is not None and (not valid_date(released) or released > as_of):
                raise ValueError(f"Invalid release date for {model}.")
            releases[model] = row
            if model in baseline_ids:
                continue
            cutoff = anchors.get(family) if family in expected_anchors else provider["since"]
            if model not in seen or family == "unknown" or cutoff is None or released is None:
                unresolved.add(model)
                continue
            if released == cutoff:
                unresolved.add(model)
                continue
            if released < cutoff:
                continue
            if model in selected:
                raise ValueError(f"Ambiguous model ID across providers: {model}. Use qualified IDs.")
            selected[model] = {"model": model, "provider": pid, "released": released, "url": row["url"]}
            count += 1

        missing_sources = sorted(url for url in expected_urls if sources.get(url) != "read")
        missing_anchors = sorted(baseline_ids - {expected_anchors[family] for family in anchors})
        unresolved.update(seen - releases.keys())
        scanned[pid] = {
            "id": pid,
            "complete": not (missing_sources or missing_anchors or unresolved),
            "sources": {url: sources.get(url, "unchecked") for url in sorted(expected_urls)},
            "anchors": sorted(anchor_evidence, key=lambda row: row["family"]),
            "missing_anchors": missing_anchors,
            "unresolved": sorted(unresolved),
            "newer_releases": count,
        }

    missing_providers = sorted(providers.keys() - scanned.keys())
    audit = {
        "checked_on": as_of,
        "complete": not missing_providers and all(row["complete"] for row in scanned.values()),
        "missing_providers": missing_providers,
        "providers": [scanned[pid] for pid in sorted(scanned)],
    }
    return {"models": list(selected.values()), "audit": audit}


def register(workspace, entry):
    validate_provider(entry)
    providers, local = registry(workspace)
    if entry["id"] in providers:
        if entry in local:
            return
        raise ValueError(f"{entry['id']} is already registered.")
    path = safe_output(workspace, REGISTRY)
    write_atomic(path, json.dumps({"version": 1, "providers": local + [entry]}, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("plan", "verify", "register"))
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--input", default="-", help="JSON document or - for stdin.")
    args = parser.parse_args()
    try:
        workspace = workspace_path(args.workspace)
        if args.action == "register":
            entry = read_json(args.input)
            register(workspace, entry)
            print(f"Registered {entry['id']} in {workspace / REGISTRY}.")
            return
        providers, _ = registry(workspace)
        data = list(providers.values()) if args.action == "plan" else verify_scan(read_json(args.input), providers)
        print(json.dumps(data, indent=2))
    except (ValueError, OSError, TypeError, KeyError) as error:
        parser.exit(1, f"Catalog operation failed: {error}\n")


if __name__ == "__main__":
    main()
