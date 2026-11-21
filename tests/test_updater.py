"""Zero-dependency unit and CLI tests for update-orchestration-skills."""

import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "skills" / "update-orchestration-skills" / "scripts"
REFS_DIR = REPO_ROOT / "skills" / "update-orchestration-skills" / "references"
EXAMPLE_MEASUREMENTS = REPO_ROOT / "examples" / "measurements.json"

sys.path.insert(0, str(SCRIPTS_DIR))
import benchmarks  # noqa: E402
import catalogs  # noqa: E402
import refresh  # noqa: E402


def run_script(script_name, *args, stdin_text=None):
    return subprocess.run(
        [sys.executable, "-B", str(SCRIPTS_DIR / script_name), *args],
        input=stdin_text,
        capture_output=True,
        text=True,
    )


def sample_provider(provider_id="xai"):
    return {
        "id": provider_id,
        "catalogs": ["https://docs.x.ai/docs/models"],
        "release_notes": ["https://docs.x.ai/docs/release-notes"],
        "usage_docs": ["https://docs.x.ai/docs/overview"],
        "since": "2026-11-19",
        "runtime": {
            "mode": "api",
            "entrypoint": "https://api.x.ai/v1",
            "auth": "api-key",
            "credential_env": "XAI_API_KEY",
            "model": "grok-4",
        },
    }


def sample_check(model="grok-4.1", effort="high", check_date="2026-11-21", sources=None):
    return {
        "model": model,
        "effort": effort,
        "date": check_date,
        "checked": list(benchmarks.UNITS),
        "sources": [] if sources is None else sources,
    }


def sample_measurement(
    model="m1",
    effort="high",
    metric="frontiercode-aa-2.0",
    cohort="c1",
    unit="percent",
    source="s1",
    obs_date="2026-11-21",
    value=75,
    url="https://example.com/",
):
    return {
        "model": model,
        "effort": effort,
        "metric": metric,
        "cohort": cohort,
        "unit": unit,
        "source": source,
        "date": obs_date,
        "value": value,
        "url": url,
    }


class ValidationTests(unittest.TestCase):
    def test_valid_date_returns_bool_without_raising(self):
        self.assertTrue(catalogs.valid_date("2026-11-19"))
        for bad in ("not-a-date", "2026-13-45", "2026-02-30", "20261119", "", None, 20261119):
            self.assertFalse(catalogs.valid_date(bad), f"Expected False for {bad!r}")

    def test_contextual_date_error_preserved(self):
        with self.assertRaisesRegex(ValueError, "Each benchmark check needs an ISO date"):
            benchmarks.normalize_check(sample_check(check_date="not-a-date"))

        with self.assertRaisesRegex(ValueError, "checked_on must be an ISO date"):
            catalogs.verify_scan({"checked_on": "bad-date", "providers": []}, {})

    def test_valid_url_accepts_public_https(self):
        for good in (
            "https://example.com/",
            "https://example.com:443/path?a=1#frag",
            "https://developers.openai.com/api/docs/models",
            "https://1.1.1.1/docs",
        ):
            self.assertTrue(catalogs.valid_url(good), f"Expected True for {good!r}")

    def test_valid_url_rejects_unsafe_or_malformed_urls(self):
        bad_urls = (
            None,
            123,
            "http://example.com/",
            "https://[::1/bad",
            "https://example.com:notaport/",
            "https://example.com:99999/",
            "https://user:pass@example.com/",
            "https://@example.com/",
            "https://:@example.com/",
            "https://example.com/\x1b[31mred",
            "https://example.com/\x00null",
            "https://example.com/\x7fdel",
            "https://example.com/a|b",
            "https://example.com/a b",
            "https://localhost/api",
            "https://sub.localhost/api",
            "https://printer.local/api",
            "https://internal/api",
            "https://127.0.0.1/api",
            "https://[::1]/api",
            "https://0.0.0.0/api",
            "https://169.254.169.254/latest/meta-data/",
            "https://10.0.0.1/api",
            "https://192.168.1.1/api",
            "https://172.16.0.1/api",
            "https://[::ffff:127.0.0.1]/api",
        )
        for bad in bad_urls:
            self.assertFalse(catalogs.valid_url(bad), f"Expected False for {bad!r}")

    def test_official_hosts_include_openai_and_google_docs(self):
        with tempfile.TemporaryDirectory() as td:
            providers, _ = catalogs.registry(Path(td))
        self.assertTrue(catalogs.official_url("https://www.openai.com/index/gpt/", providers["openai"]))
        self.assertTrue(catalogs.official_url("https://platform.openai.com/docs/models", providers["openai"]))
        self.assertTrue(catalogs.official_url("https://ai.google.dev/gemini-api/docs/models", providers["google"]))
        self.assertTrue(catalogs.official_url("https://developers.googleblog.com/en/gemini/", providers["google"]))
        self.assertFalse(catalogs.official_url("https://evil.example.com/docs", providers["openai"]))


class StorageAndRegistryTests(unittest.TestCase):
    def test_write_atomic_respects_umask_and_preserves_existing_mode(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / ".orchestration" / "out.md"
            old_mask = os.umask(0o022)
            try:
                catalogs.write_atomic(target, "first\n")
            finally:
                os.umask(old_mask)
            self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o644)

            os.chmod(target, 0o640)
            catalogs.write_atomic(target, "second\n")
            self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o640)
            self.assertEqual(target.read_text(encoding="utf-8"), "second\n")

    def test_registry_rejects_boolean_version(self):
        with tempfile.TemporaryDirectory() as td:
            ws = Path(td)
            (ws / ".orchestration").mkdir()
            (ws / ".orchestration" / "provider-catalogs.json").write_text(
                '{"version": true, "providers": []}', encoding="utf-8"
            )
            with self.assertRaisesRegex(ValueError, "Unsupported provider registry version"):
                catalogs.registry(ws)

    def test_verify_scan_and_unhashable_source_guard(self):
        with tempfile.TemporaryDirectory() as td:
            ws = Path(td)
            catalogs.register(ws, sample_provider("xai"))
            providers, _ = catalogs.registry(ws)

        bad_report = {
            "checked_on": "2026-11-21",
            "providers": [
                {
                    "id": "xai",
                    "sources": [{"url": ["unhashable"], "status": "read", "seen": []}],
                    "anchors": [],
                    "releases": [],
                }
            ],
        }
        with self.assertRaises(ValueError):
            catalogs.verify_scan(bad_report, providers)

        good_report = {
            "checked_on": "2026-11-21",
            "providers": [
                {
                    "id": "xai",
                    "sources": [
                        {"url": "https://docs.x.ai/docs/models", "status": "read", "seen": ["grok-4.1", "grok-4.0", "grok-same"]},
                        {"url": "https://docs.x.ai/docs/release-notes", "status": "read", "seen": ["grok-4.1"]},
                    ],
                    "anchors": [],
                    "releases": [
                        {"model": "grok-4.1", "family": "other", "released": "2026-11-20", "url": "https://docs.x.ai/docs/models"},
                        {"model": "grok-4.0", "family": "other", "released": "2026-11-10", "url": "https://docs.x.ai/docs/models"},
                        {"model": "grok-same", "family": "other", "released": "2026-11-19", "url": "https://docs.x.ai/docs/models"},
                    ],
                }
            ],
        }
        result = catalogs.verify_scan(good_report, providers)
        self.assertEqual([m["model"] for m in result["models"]], ["grok-4.1"])
        xai_audit = next(p for p in result["audit"]["providers"] if p["id"] == "xai")
        self.assertEqual(xai_audit["unresolved"], ["grok-same"])
        self.assertFalse(xai_audit["complete"])


class BenchmarkAndRefreshUnitTests(unittest.TestCase):
    def test_normalize_check_rejects_unhashable_checked_items(self):
        row = sample_check()
        row["checked"] = [{"metric": "frontiercode-aa-2.0"}]
        with self.assertRaisesRegex(ValueError, "benchmark-suite.json"):
            benchmarks.normalize_check(row)

    def test_normalize_enforces_suite_unit_even_unscoped(self):
        payload = {
            "measurements": [sample_measurement(metric="frontiercode-aa-2.0", unit="points")]
        }
        with self.assertRaisesRegex(ValueError, "must use the percent unit"):
            refresh.normalize(payload)

    def test_normalize_rejects_duplicates_and_normalizes_negative_zero(self):
        dup_models = {
            "models": [
                {"model": "m1", "provider": "p1", "released": None, "url": "https://example.com/"},
                {"model": "m1", "provider": "p1", "released": None, "url": "https://example.com/"},
            ]
        }
        with self.assertRaisesRegex(ValueError, "Duplicate models entry"):
            refresh.normalize(dup_models)

        dup_meas = {
            "measurements": [
                sample_measurement(value=50),
                sample_measurement(value=60),
            ]
        }
        with self.assertRaisesRegex(ValueError, "Duplicate measurements entry"):
            refresh.normalize(dup_meas)

        neg_zero = refresh.normalize({"measurements": [sample_measurement(value=-0.0)]})
        val = neg_zero["measurements"][0]["value"]
        self.assertEqual(refresh.display(val), "0")

    def test_merge_keeps_latest_and_checks_provider_conflict(self):
        prev = refresh.normalize(
            {
                "models": [{"model": "m1", "provider": "OpenAI", "released": "2026-11-19", "url": "https://openai.com/"}],
                "measurements": [sample_measurement(obs_date="2026-11-21", value=70)],
            }
        )
        older = refresh.normalize(
            {
                "models": [{"model": "m1", "provider": "openai", "released": None, "url": "https://openai.com/"}],
                "measurements": [sample_measurement(obs_date="2026-11-20", value=50)],
            }
        )
        merged = refresh.merge(prev, older)
        self.assertEqual(merged["models"][0]["released"], "2026-11-19")
        self.assertEqual(merged["measurements"][0]["value"], 70)

        conflict = refresh.normalize(
            {"models": [{"model": "m1", "provider": "anthropic", "released": None, "url": "https://anthropic.com/"}]}
        )
        with self.assertRaisesRegex(ValueError, "Conflicting providers"):
            refresh.merge(prev, conflict)

    def test_render_omits_empty_measurement_tables(self):
        data = refresh.normalize(
            {
                "models": [{"model": "m1", "provider": "p1", "released": "2026-11-20", "url": "https://example.com/"}],
                "benchmark_checks": [sample_check(model="m1")],
            }
        )
        rendered = refresh.render("# Baseline\n", data, None)
        self.assertIn("### Benchmark coverage by model and effort", rendered)
        self.assertNotIn("### Scores and profile averages", rendered)
        self.assertNotIn("### Source observations", rendered)

    def test_require_coverage_and_matrix_suffixes(self):
        data = refresh.normalize(
            {
                "models": [{"model": "m1", "provider": "p1", "released": "2026-11-20", "url": "https://example.com/"}],
                "benchmark_checks": [sample_check(model="m1", effort="high")],
                "measurements": [
                    sample_measurement(model="m1", effort="high", metric="aa-briefcase-v1.1", unit="elo", value=1600)
                ],
            }
        )
        benchmarks.require_coverage(data, {"m1"})
        grouped = {("m1", "high", "aa-briefcase-v1.1", "c1", "elo"): data["measurements"]}
        table = "\n".join(benchmarks.matrix(data, grouped))
        self.assertIn("1600 Elo (`c1`)", table)
        self.assertEqual(benchmarks.UNIT_SUFFIXES["points"], " pts")


class CliIntegrationTests(unittest.TestCase):
    def test_preview_and_idempotent_round_trip_with_example_measurements(self):
        preview = run_script(
            "refresh.py",
            "--workspace",
            str(REPO_ROOT),
            "--input",
            str(EXAMPLE_MEASUREMENTS),
            "--preview",
        )
        self.assertEqual(preview.returncode, 0, preview.stderr)
        self.assertIn("### Benchmark coverage by model and effort", preview.stdout)
        self.assertIn("72% (`demo-fixture`)", preview.stdout)

        with tempfile.TemporaryDirectory() as td:
            ws = Path(td)
            first = run_script(
                "refresh.py", "--workspace", str(ws), "--input", str(EXAMPLE_MEASUREMENTS)
            )
            self.assertEqual(first.returncode, 0, first.stderr)
            out_file = ws / ".orchestration" / "model-measurements.md"
            self.assertTrue(out_file.exists())
            first_contents = out_file.read_text(encoding="utf-8")

            second = run_script(
                "refresh.py", "--workspace", str(ws), "--input", str(EXAMPLE_MEASUREMENTS)
            )
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertEqual(out_file.read_text(encoding="utf-8"), first_contents)

    def test_named_model_enforces_official_url_case_insensitively(self):
        with tempfile.TemporaryDirectory() as td:
            ws = Path(td)
            obs = {
                "models": [
                    {
                        "model": "gpt-7-test",
                        "provider": "OpenAI",
                        "released": "2026-11-21",
                        "url": "https://evil.example.com/fake-gpt",
                    }
                ],
                "benchmark_checks": [sample_check(model="gpt-7-test")],
                "measurements": [],
            }
            obs_path = ws / "obs.json"
            obs_path.write_text(json.dumps(obs), encoding="utf-8")
            bad = run_script(
                "refresh.py",
                "--workspace",
                str(ws),
                "--model",
                "gpt-7-test",
                "--input",
                str(obs_path),
                "--preview",
            )
            self.assertEqual(bad.returncode, 1)
            self.assertIn("needs a release or model page from its provider", bad.stderr)

            obs["models"][0]["url"] = "https://www.openai.com/index/gpt-7/"
            obs_path.write_text(json.dumps(obs), encoding="utf-8")
            good = run_script(
                "refresh.py",
                "--workspace",
                str(ws),
                "--model",
                "gpt-7-test",
                "--input",
                str(obs_path),
                "--preview",
            )
            self.assertEqual(good.returncode, 0, good.stderr)

    def test_provider_entry_workflow_and_mismatch_guards(self):
        with tempfile.TemporaryDirectory() as td:
            ws = Path(td)
            prov = sample_provider("xai")
            prov_path = ws / "xai.json"
            prov_path.write_text(json.dumps(prov), encoding="utf-8")

            obs = {
                "models": [
                    {
                        "model": "grok-4.1",
                        "provider": "xai",
                        "released": "2026-11-20",
                        "url": "https://docs.x.ai/docs/models",
                    }
                ],
                "benchmark_checks": [sample_check(model="grok-4.1")],
                "measurements": [],
            }
            obs_path = ws / "obs.json"
            obs_path.write_text(json.dumps(obs), encoding="utf-8")

            # Preview before registration works
            prev = run_script(
                "refresh.py",
                "--workspace",
                str(ws),
                "--provider-entry",
                str(prov_path),
                "--model",
                "grok-4.1",
                "--input",
                str(obs_path),
                "--preview",
            )
            self.assertEqual(prev.returncode, 0, prev.stderr)

            # Write before registration fails
            pre_write = run_script(
                "refresh.py",
                "--workspace",
                str(ws),
                "--provider-entry",
                str(prov_path),
                "--model",
                "grok-4.1",
                "--input",
                str(obs_path),
            )
            self.assertEqual(pre_write.returncode, 1)
            self.assertIn("Register the chosen provider", pre_write.stderr)

            # Register provider and write
            reg = run_script("catalogs.py", "register", "--workspace", str(ws), "--input", str(prov_path))
            self.assertEqual(reg.returncode, 0, reg.stderr)

            post_write = run_script(
                "refresh.py",
                "--workspace",
                str(ws),
                "--provider-entry",
                str(prov_path),
                "--model",
                "grok-4.1",
                "--input",
                str(obs_path),
            )
            self.assertEqual(post_write.returncode, 0, post_write.stderr)

            # Mismatched draft fails
            mutated = sample_provider("xai")
            mutated["since"] = "2026-11-01"
            mutated_path = ws / "xai-diff.json"
            mutated_path.write_text(json.dumps(mutated), encoding="utf-8")
            mismatch = run_script(
                "refresh.py",
                "--workspace",
                str(ws),
                "--provider-entry",
                str(mutated_path),
                "--model",
                "grok-4.1",
                "--input",
                str(obs_path),
                "--preview",
            )
            self.assertEqual(mismatch.returncode, 1)
            self.assertIn("does not match the registered provider", mismatch.stderr)

            # Built-in provider via --provider-entry fails
            builtin_draft = sample_provider("openai")
            builtin_path = ws / "openai.json"
            builtin_path.write_text(json.dumps(builtin_draft), encoding="utf-8")
            obs["models"][0]["provider"] = "openai"
            obs["models"][0]["url"] = "https://developers.openai.com/api/docs/models"
            obs_path.write_text(json.dumps(obs), encoding="utf-8")
            builtin_res = run_script(
                "refresh.py",
                "--workspace",
                str(ws),
                "--provider-entry",
                str(builtin_path),
                "--model",
                "grok-4.1",
                "--input",
                str(obs_path),
                "--preview",
            )
            self.assertEqual(builtin_res.returncode, 1)
            self.assertIn("built-in provider", builtin_res.stderr)

    def test_catalog_report_verify_and_select_cli_workflow(self):
        with tempfile.TemporaryDirectory() as td:
            ws = Path(td)
            prov_path = ws / "xai.json"
            prov_path.write_text(json.dumps(sample_provider("xai")), encoding="utf-8")
            reg = run_script("catalogs.py", "register", "--workspace", str(ws), "--input", str(prov_path))
            self.assertEqual(reg.returncode, 0, reg.stderr)

            scan = {
                "checked_on": "2026-11-21",
                "providers": [
                    {
                        "id": "xai",
                        "sources": [
                            {"url": "https://docs.x.ai/docs/models", "status": "read", "seen": ["grok-4.1"]},
                            {"url": "https://docs.x.ai/docs/release-notes", "status": "read", "seen": ["grok-4.1"]},
                        ],
                        "anchors": [],
                        "releases": [
                            {
                                "model": "grok-4.1",
                                "family": "other",
                                "released": "2026-11-20",
                                "url": "https://docs.x.ai/docs/models",
                            }
                        ],
                    }
                ],
            }
            scan_path = ws / "scan.json"
            scan_path.write_text(json.dumps(scan), encoding="utf-8")
            verified = run_script("catalogs.py", "verify", "--workspace", str(ws), "--input", str(scan_path))
            self.assertEqual(verified.returncode, 0, verified.stderr)
            self.assertEqual([m["model"] for m in json.loads(verified.stdout)["models"]], ["grok-4.1"])

            obs = {
                "benchmark_checks": [sample_check(model="grok-4.1", sources=["https://artificialanalysis.ai/leaderboards/models"])],
                "measurements": [sample_measurement(model="grok-4.1", value=52.5)],
            }
            obs_path = ws / "obs.json"
            obs_path.write_text(json.dumps(obs), encoding="utf-8")
            ref = run_script(
                "refresh.py",
                "--workspace",
                str(ws),
                "--catalog-report",
                str(scan_path),
                "--select",
                "grok-4.1",
                "--input",
                str(obs_path),
            )
            self.assertEqual(ref.returncode, 0, ref.stderr)
            out = (ws / ".orchestration" / "model-measurements.md").read_text(encoding="utf-8")
            self.assertIn("### Latest catalog check", out)
            self.assertIn("Selected for this refresh: `grok-4.1`.", out)

    def test_cli_argument_error_consistency(self):
        with tempfile.TemporaryDirectory() as td:
            ws = Path(td)
            r1 = run_script("refresh.py", "--workspace", str(ws), "--catalog-report", "-", "--input", "-")
            self.assertEqual(r1.returncode, 2)
            r2 = run_script("refresh.py", "--workspace", str(ws), "--provider-entry", "-", "--model", "m1", "--input", "-")
            self.assertEqual(r2.returncode, 2)
            r3 = run_script("catalogs.py", "plan", "--workspace", str(ws), "--input", "unused.json")
            self.assertEqual(r3.returncode, 2)

    def test_named_model_canonicalizes_builtin_provider_aliases(self):
        cases = (
            ("chatgpt", "https://developers.openai.com/api/docs/models"),
            ("codex", "https://www.openai.com/index/gpt-7/"),
            ("Codex", "https://platform.openai.com/docs/models"),
            ("claude", "https://platform.claude.com/docs/en/models/overview"),
            ("CLAUDE", "https://www.anthropic.com/news/claude"),
            ("gemini", "https://ai.google.dev/gemini-api/docs/models"),
            ("agy", "https://antigravity.google/docs/models"),
            ("Antigravity", "https://deepmind.google/models/gemini/"),
        )
        with tempfile.TemporaryDirectory() as td:
            ws = Path(td)
            obs_path = ws / "obs.json"
            for alias, official in cases:
                with self.subTest(alias=alias):
                    obs = {
                        "models": [
                            {
                                "model": "alias-test-model",
                                "provider": alias,
                                "released": "2026-11-21",
                                "url": "https://unverified-blog.example/fake",
                            }
                        ],
                        "benchmark_checks": [sample_check(model="alias-test-model")],
                        "measurements": [],
                    }
                    obs_path.write_text(json.dumps(obs), encoding="utf-8")
                    bad = run_script(
                        "refresh.py",
                        "--workspace",
                        str(ws),
                        "--model",
                        "alias-test-model",
                        "--input",
                        str(obs_path),
                        "--preview",
                    )
                    self.assertEqual(bad.returncode, 1)
                    self.assertIn("needs a release or model page from its provider", bad.stderr)

                    obs["models"][0]["url"] = official
                    obs_path.write_text(json.dumps(obs), encoding="utf-8")
                    good = run_script(
                        "refresh.py",
                        "--workspace",
                        str(ws),
                        "--model",
                        "alias-test-model",
                        "--input",
                        str(obs_path),
                        "--preview",
                    )
                    self.assertEqual(good.returncode, 0, good.stderr)

            # Built-in provider aliases cannot be registered or passed as --provider-entry
            alias_prov = ws / "codex.json"
            alias_prov.write_text(json.dumps(sample_provider("codex")), encoding="utf-8")
            reg = run_script("catalogs.py", "register", "--workspace", str(ws), "--input", str(alias_prov))
            self.assertEqual(reg.returncode, 1)
            self.assertIn("already registered", reg.stderr)

    def test_tampered_catalog_audit_and_baseline_decoy_rejected(self):
        valid_audit = {
            "checked_on": "2026-11-21",
            "complete": False,
            "missing_providers": ["deepseek"],
            "selected_models": ["grok-4.1"],
            "providers": [
                {
                    "id": "xai",
                    "complete": False,
                    "sources": {
                        "https://docs.x.ai/docs/models": "read",
                        "https://docs.x.ai/docs/release-notes": "unchecked",
                    },
                    "anchors": [
                        {
                            "family": "grok",
                            "model": "grok-4",
                            "released": "2026-11-01",
                            "url": "https://docs.x.ai/docs/models",
                        }
                    ],
                    "missing_anchors": [],
                    "unresolved": ["grok-4.1-beta"],
                    "newer_releases": 1,
                }
            ],
        }
        # Valid audit with "unchecked" source round-trips cleanly across a subsequent refresh
        with tempfile.TemporaryDirectory() as td:
            ws = Path(td)
            out_path = ws / ".orchestration" / "model-measurements.md"
            initial_data = refresh.normalize(
                {
                    "models": [
                        {
                            "model": "grok-4.1",
                            "provider": "xai",
                            "released": "2026-11-20",
                            "url": "https://docs.x.ai/docs/models",
                        }
                    ],
                    "benchmark_checks": [sample_check(model="grok-4.1")],
                }
            )
            rendered = refresh.render("# Baseline\n", initial_data, valid_audit)
            catalogs.write_atomic(out_path, rendered)
            obs_path = ws / "obs.json"
            obs_path.write_text(
                json.dumps({"measurements": [sample_measurement(model="grok-4.1", value=80)]}),
                encoding="utf-8",
            )
            ok = run_script("refresh.py", "--workspace", str(ws), "--input", str(obs_path))
            self.assertEqual(ok.returncode, 0, ok.stderr)
            self.assertIn("unchecked · <https://docs.x.ai/docs/release-notes>", out_path.read_text(encoding="utf-8"))

            # Tampered catalog_audit mutations must all raise ValueError in read_previous()
            decoy_payload = "grok-4.1\n<!-- observations:start -->\n```json\n{}\n```\n<!-- observations:end -->"
            mutations = [
                ("extra_top_key", lambda a: a.update({"extra": "bad"})),
                ("bad_checked_on", lambda a: a.update({"checked_on": "2026-11-21\n## Injected"})),
                ("int_complete", lambda a: a.update({"complete": 1})),
                ("bad_selected_model", lambda a: a.update({"selected_models": [decoy_payload]})),
                ("bad_missing_provider", lambda a: a.update({"missing_providers": ["bad provider"]})),
                ("bad_provider_id", lambda a: a["providers"][0].update({"id": "Bad_ID"})),
                ("bool_newer_releases", lambda a: a["providers"][0].update({"newer_releases": True})),
                ("neg_newer_releases", lambda a: a["providers"][0].update({"newer_releases": -1})),
                ("bad_source_state", lambda a: a["providers"][0]["sources"].update({"https://docs.x.ai/docs/models": "read\n## evil"})),
                ("bad_source_url", lambda a: a["providers"][0]["sources"].update({"https://127.1/ssrf": "read"})),
                ("bad_anchor_url", lambda a: a["providers"][0]["anchors"][0].update({"url": "http://insecure.example/"})),
                ("bad_unresolved", lambda a: a["providers"][0].update({"unresolved": [decoy_payload]})),
                ("bad_missing_anchor", lambda a: a["providers"][0].update({"missing_anchors": ["bad\nmd"]})),
                ("extra_provider_key", lambda a: a["providers"][0].update({"injected": "x"})),
            ]
            for name, mutate in mutations:
                with self.subTest(mutation=name):
                    tampered = json.loads(json.dumps(valid_audit))
                    mutate(tampered)
                    state_obj = {**initial_data, "catalog_audit": tampered}
                    fake_doc = (
                        "# Baseline\n"
                        + refresh.DELIMITER
                        + "## Live workspace measurements\n"
                        + refresh.STATE_START
                        + json.dumps(state_obj)
                        + refresh.STATE_END
                        + "\n"
                    )
                    out_path.write_text(fake_doc, encoding="utf-8")
                    with self.assertRaises(ValueError):
                        refresh.read_previous(out_path)
                    res = run_script("refresh.py", "--workspace", str(ws), "--input", str(obs_path), "--preview")
                    self.assertEqual(res.returncode, 1)
                    self.assertNotIn("Traceback", res.stderr)

            # Decoy <!-- observations:start --> (exact or spaced) in baseline or generated prefix must be rejected
            for bad_doc in (
                (
                    "# Baseline\n<!-- observations:start -->\n```json\n{}\n```\n<!-- observations:end -->\n"
                    + refresh.DELIMITER
                    + "## Live workspace measurements\n"
                    + refresh.STATE_START
                    + json.dumps(initial_data)
                    + refresh.STATE_END
                    + "\n"
                ),
                (
                    "# Baseline\n<!--  observations:start  -->\n```json\n{}\n```\n<!--  observations:end  -->\n"
                    + refresh.DELIMITER
                    + "## Live workspace measurements\n"
                    + refresh.STATE_START
                    + json.dumps(initial_data)
                    + refresh.STATE_END
                    + "\n"
                ),
                (
                    "# Baseline\n"
                    + refresh.DELIMITER
                    + "## Live workspace measurements\n<!--  observations:start  -->\n"
                    + refresh.STATE_START
                    + json.dumps(initial_data)
                    + refresh.STATE_END
                    + "\n"
                ),
            ):
                out_path.write_text(bad_doc, encoding="utf-8")
                with self.assertRaises(ValueError):
                    refresh.read_previous(out_path)

    def test_case_insensitive_collision_rejection_and_merge_and_profile_units(self):
        # Single input with case-colliding benchmark checks rejected
        with self.assertRaisesRegex(ValueError, "Duplicate benchmark check"):
            refresh.normalize(
                {
                    "benchmark_checks": [
                        sample_check(model="m1", effort="High"),
                        sample_check(model="m1", effort="high"),
                    ]
                }
            )

        # Single input with case-colliding measurement keys rejected
        with self.assertRaisesRegex(ValueError, "Duplicate measurements entry"):
            refresh.normalize(
                {
                    "measurements": [
                        sample_measurement(model="m1", effort="High", metric="coding", unit="points", value=95),
                        sample_measurement(model="m1", effort="high", metric="coding", unit="points", value=70),
                    ]
                },
                strict_units=True,
            )

        # Single input with case-colliding model IDs rejected
        with self.assertRaisesRegex(ValueError, "Duplicate models entry"):
            refresh.normalize(
                {
                    "models": [
                        {"model": "M1", "provider": "p1", "released": None, "url": "https://example.com/"},
                        {"model": "m1", "provider": "p1", "released": None, "url": "https://example.com/"},
                    ]
                }
            )

        # merge() matches case-insensitively on effort/model so older High is replaced by newer high
        prev = refresh.normalize(
            {
                "benchmark_checks": [sample_check(model="m1", effort="High", check_date="2026-11-20")],
                "measurements": [
                    sample_measurement(model="m1", effort="High", metric="coding", unit="points", obs_date="2026-11-20", value=70)
                ],
            },
            strict_units=True,
        )
        incoming = refresh.normalize(
            {
                "benchmark_checks": [sample_check(model="m1", effort="high", check_date="2026-11-21")],
                "measurements": [
                    sample_measurement(model="m1", effort="high", metric="coding", unit="points", obs_date="2026-11-21", value=95)
                ],
            },
            strict_units=True,
        )
        merged = refresh.merge(prev, incoming)
        self.assertEqual(len(merged["benchmark_checks"]), 1)
        self.assertEqual(merged["benchmark_checks"][0]["effort"], "high")
        self.assertEqual(len(merged["measurements"]), 1)
        self.assertEqual(merged["measurements"][0]["effort"], "high")
        self.assertEqual(merged["measurements"][0]["value"], 95)

        # Case-insensitive grouping in render() and benchmarks.matrix(), plus mixed-case suite metrics
        mixed_sources = refresh.normalize(
            {
                "models": [
                    {"model": "GPT-7-Custom", "provider": "myprov", "released": "2026-11-21", "url": "https://example.com/"}
                ],
                "benchmark_checks": [sample_check(model="GPT-7-Custom", effort="high")],
                "measurements": [
                    sample_measurement(
                        model="GPT-7-Custom", effort="High", metric="Terminal-Bench-4.0", cohort="c1", unit="percent", source="s1", value=80
                    ),
                    sample_measurement(
                        model="gpt-7-custom", effort="high", metric="terminal-bench-4.0", cohort="c1", unit="percent", source="s2", value=90
                    ),
                    sample_measurement(
                        model="GPT-7-Custom", effort="High", metric="coding", cohort="c1", unit="points", source="s1", value=80
                    ),
                    sample_measurement(
                        model="gpt-7-custom", effort="high", metric="coding", cohort="c1", unit="points", source="s2", value=90
                    ),
                ],
            },
            strict_units=True,
        )
        benchmarks.require_coverage(mixed_sources, {"GPT-7-Custom"})
        rendered = refresh.render("# Baseline\n", mixed_sources, None)
        summary_tables = rendered.split("### Source observations", 1)[0]
        self.assertIn("| `GPT-7-Custom` | high | 2026-11-21 | - | 85% (`c1`) |", summary_tables)
        self.assertIn("| `GPT-7-Custom` | high | coding | c1 | points | 85 | 2 | 80–90 | 2026-11-21 |", summary_tables)
        self.assertIn("| `GPT-7-Custom` | high | terminal-bench-4.0 | c1 | percent | 85 | 2 | 80–90 | 2026-11-21 |", summary_tables)
        self.assertNotIn("| `GPT-7-Custom` | High |", summary_tables)
        self.assertNotIn("| `GPT-7-Custom` | unspecified |", summary_tables)

        # Profile and latency metric unit enforcement in benchmarks.validate_metric_unit & refresh.py CLI
        for metric in ("coding", "reasoning", "accuracy", "knowledge", "knowledge-work", "review"):
            with self.subTest(profile_metric=metric):
                benchmarks.validate_metric_unit(metric, "points")
                with self.assertRaisesRegex(ValueError, "must use the points unit"):
                    benchmarks.validate_metric_unit(metric, "percent")
        for metric in ("seconds-per-task", "s-per-task", "latency-seconds", "estimated-seconds-per-task"):
            with self.subTest(latency_metric=metric):
                benchmarks.validate_metric_unit(metric, "seconds")
                with self.assertRaisesRegex(ValueError, "must use the seconds unit"):
                    benchmarks.validate_metric_unit(metric, "points")

        with tempfile.TemporaryDirectory() as td:
            ws = Path(td)
            obs_path = ws / "bad-unit.json"
            obs_path.write_text(
                json.dumps({"measurements": [sample_measurement(metric="coding", unit="percent", value=80)]}),
                encoding="utf-8",
            )
            bad = run_script("refresh.py", "--workspace", str(ws), "--input", str(obs_path), "--preview")
            self.assertEqual(bad.returncode, 1)
            self.assertIn("must use the points unit", bad.stderr)

            obs_path.write_text(
                json.dumps({"measurements": [sample_measurement(metric="seconds-per-task", unit="points", value=120)]}),
                encoding="utf-8",
            )
            bad_lat = run_script("refresh.py", "--workspace", str(ws), "--input", str(obs_path), "--preview")
            self.assertEqual(bad_lat.returncode, 1)
            self.assertIn("must use the seconds unit", bad_lat.stderr)

        collection_doc = (REFS_DIR / "collection.md").read_text(encoding="utf-8")
        self.assertIn('`unit: "points"`', collection_doc)
        self.assertIn('`unit: "seconds"`', collection_doc)

    def test_hardened_url_slug_managed_client_and_adversarial_json_errors(self):
        # F1 + L16 + H3: hardened host/URL validation
        for good in (
            "https://[2606:4700:4700::1111]/docs",
            "https://xn--bcher-kva.example/models",
        ):
            self.assertTrue(catalogs.valid_url(good), f"Expected True for {good!r}")

        hardened_bad_urls = (
            "https://example.com:0/",
            "https://docs.example.com./models",
            "https://.a/",
            "https://a..b/",
            "https://-bad.example.com/",
            "https://bad-.example.com/",
            "https://127.1/",
            "https://127.0.1/",
            "https://0177.0.0.1/",
            "https://0x7f.0.0.1/",
            "https://0x7f.1/",
            "https://169.254.43518/latest/meta-data/",
            "https://0xa9.0xfe.0xa9.0xfe/latest/meta-data/",
            "https://10.1/",
            "https://192.168.1/",
            "https://172.16.1/",
            "https://0.1/",
            "https://100.64.0.1/",
            "https://100.100.100.200/latest/meta-data/",
            "https://[::ffff:100.64.0.1]/",
            "https://[2002:7f00:0001::]/",
            "https://[2002:a9fe:a9fe::]/",
            "https://[2002:6440:0001::]/",
            "https://[2001:0000:4136:e378:8000:63bf:3fff:fdd2]/",
            "https://[2001:0000:7f00:0001:0000:0000:80ff:fffe]/",
            "https://224.0.0.1/",
            "https://[ff0e::1]/",
            "https://127\u30020\u30020.1/",
            "https://\uff11\uff12\uff17.0.0.1/",
            "https://example\u3002com/",
            "https://foo.\uff49\uff4e\uff54\uff45\uff52\uff4e\uff41\uff4c/",
            "https://metadata.google.internal/",
            "https://router.home.arpa/",
            "https://home.arpa/",
            "https://example.com/\x80c1",
            "https://example.com/\x9b31m",
            "https://example.com/\u202eevil",
            "https://example.com/\u2066bidi",
        )
        for bad in hardened_bad_urls:
            self.assertFalse(catalogs.valid_url(bad), f"Expected False for {bad!r}")

        # official_url strips trailing dot on host comparison, while rejecting trailing-dot candidate URLs
        prov_dot = {
            "catalogs": ["https://docs.example.com./models"],
            "release_notes": [],
            "official_hosts": ["api.example.com."],
        }
        self.assertTrue(catalogs.official_url("https://docs.example.com/models", prov_dot))
        self.assertTrue(catalogs.official_url("https://api.example.com/v1", prov_dot))
        self.assertFalse(catalogs.official_url("https://docs.example.com./models", prov_dot))

        # H3: SLUG max length bound (<= 128)
        self.assertIsNotNone(catalogs.SLUG.fullmatch("a" * 128))
        self.assertIsNone(catalogs.SLUG.fullmatch("a" * 129))

        # L16: managed-client permits single spaces in client names; cli does not
        mc = sample_provider("acme")
        mc["runtime"] = {
            "mode": "managed-client",
            "entrypoint": "Acme Studio",
            "auth": "account-session",
            "credential_env": None,
            "model": "acme-1",
        }
        catalogs.validate_provider(mc)
        mc_bad = json.loads(json.dumps(mc))
        mc_bad["runtime"]["entrypoint"] = "Acme\nStudio"
        with self.assertRaises(ValueError):
            catalogs.validate_provider(mc_bad)
        cli_bad = json.loads(json.dumps(mc))
        cli_bad["runtime"]["mode"] = "cli"
        with self.assertRaises(ValueError):
            catalogs.validate_provider(cli_bad)

        # F7: RecursionError and OverflowError exit cleanly with code 1 and no traceback
        nested_json = "[" * 2000 + "]" * 2000
        huge_int_json = json.dumps({"measurements": [sample_measurement(value=10**400)]})
        with tempfile.TemporaryDirectory() as td:
            ws = Path(td)
            cat_rec = run_script("catalogs.py", "verify", "--workspace", str(ws), "--input", "-", stdin_text=nested_json)
            self.assertEqual(cat_rec.returncode, 1)
            self.assertIn("Catalog operation failed", cat_rec.stderr)
            self.assertNotIn("Traceback", cat_rec.stderr)

            ref_rec = run_script("refresh.py", "--workspace", str(ws), "--input", "-", stdin_text=nested_json)
            self.assertEqual(ref_rec.returncode, 1)
            self.assertIn("Refresh failed", ref_rec.stderr)
            self.assertNotIn("Traceback", ref_rec.stderr)

            ref_ovf = run_script("refresh.py", "--workspace", str(ws), "--input", "-", stdin_text=huge_int_json)
            self.assertEqual(ref_ovf.returncode, 1)
            self.assertIn("Refresh failed", ref_ovf.stderr)
            self.assertNotIn("Traceback", ref_ovf.stderr)


if __name__ == "__main__":
    unittest.main()
