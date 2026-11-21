"""Regression tests for benchmark provenance and compatible lane scoring."""

import copy
import json
from pathlib import Path
import sys
import unittest

from test_resolve_lanes import authorized_lane, profile_text

SCRIPTS = Path(__file__).resolve().parents[1] / "skills" / "update-orchestration-skills" / "scripts"
sys.path.insert(0, str(SCRIPTS))
import resolve_lanes


def observation(model, value, *, metric="coding", cohort="matched", unit="points", source="aa"):
    return {
        "model": model,
        "effort": "high",
        "metric": metric,
        "cohort": cohort,
        "unit": unit,
        "source": source,
        "date": "2026-11-21",
        "value": value,
        "url": "https://example.com/result",
    }


def workspace_candidates(*observations):
    payload = {"measurements": observations}
    text = "<!-- observations:start -->\n```json\n" + json.dumps(payload) + "\n```\n<!-- observations:end -->"
    return resolve_lanes.parse_workspace_observations(text)


def rank_authorized(candidates, *, role="coding", cohort=None):
    lanes = resolve_lanes.parse_authorized_lanes(profile_text(*(
        authorized_lane(resolve_lanes.canonical_model_id(c["model"]), c["effort"], c["pool"], roles=(role,))
        for c in candidates
    )))
    return resolve_lanes.resolve_lanes(candidates, {}, role=role, cohort=cohort, authorized_lanes=lanes)


class BenchmarkProvenanceTests(unittest.TestCase):
    def test_unmatched_cohort_or_unit_cannot_inflate_the_selected_score(self):
        models = workspace_candidates(
            observation("sample-a", 85),
            observation("sample-b", 80),
            observation("sample-b", 130, cohort="different-scale"),
            observation("sample-b", 999, unit="usd"),
        )
        report = rank_authorized(models, cohort="matched")
        self.assertEqual(report["score_cohort"], "matched")
        self.assertEqual([(c["model"], c["score"]) for c in report["ranked"]], [
            ("sample-a", 85.0), ("sample-b", 80.0),
        ])

        automatic = rank_authorized(models)
        self.assertIsNone(automatic["recommended"])
        self.assertTrue(any("Multiple live coding cohorts" in warning for warning in automatic["warnings"]))

    def test_only_sources_shared_on_the_selected_profile_are_averaged(self):
        models = workspace_candidates(
            observation("sample-a", 85),
            observation("sample-b", 80),
            observation("sample-b", 100, source="different-source"),
        )
        report = rank_authorized(models)
        self.assertEqual(report["recommended"]["model"], "sample-a")
        self.assertEqual(report["ranked"][1]["score"], 80.0)

    def test_single_live_cohort_does_not_compare_against_archived_scores(self):
        archive = resolve_lanes.parse_historical_candidates(resolve_lanes.BUNDLED_MEASUREMENTS.read_text())
        live = workspace_candidates(observation("sample-a", 35))
        report = rank_authorized(resolve_lanes.merge_candidates(archive, live))
        self.assertEqual(report["score_basis"], "workspace")
        self.assertEqual(report["recommended"]["model"], "sample-a")
        self.assertTrue(all(c["score"] is None for c in report["ranked"][1:]))

    def test_review_components_cannot_be_combined_across_cohorts(self):
        models = workspace_candidates(
            observation("sample-a", 90, metric="accuracy"),
            observation("sample-a", 90, metric="reasoning", cohort="different-scale"),
            observation("sample-b", 70, metric="accuracy"),
            observation("sample-b", 70, metric="reasoning"),
        )
        report = rank_authorized(models, role="review")
        self.assertEqual(report["recommended"]["model"], "sample-b")
        self.assertIsNone(report["ranked"][1]["score"])

    def test_timing_breaks_a_tie_only_on_matched_measurements(self):
        common = [
            observation("sample-a", 85),
            observation("sample-b", 85),
            observation("sample-a", 20, metric="seconds-per-task", cohort="latency-suite", unit="seconds"),
        ]
        for metric, cohort, winner in [
            ("seconds-per-task", "different-suite", "sample-a"),
            ("estimated-seconds-per-task", "latency-suite", "sample-a"),
            ("seconds-per-task", "latency-suite", "sample-b"),
        ]:
            with self.subTest(metric=metric, cohort=cohort):
                models = workspace_candidates(
                    *common,
                    observation("sample-b", 10, metric=metric, cohort=cohort, unit="seconds"),
                )
                report = rank_authorized(models)
                self.assertEqual(report["recommended"]["model"], winner)

    def test_model_ids_with_different_punctuation_remain_separate(self):
        models = workspace_candidates(observation("owner/model", 85), observation("owner-model", 90))
        report = rank_authorized(resolve_lanes.merge_candidates([], models))
        self.assertEqual([(c["model"], c["score"]) for c in report["ranked"]], [
            ("owner-model", 90.0), ("owner/model", 85.0),
        ])

    def test_timing_tie_break_isolated_per_pre_latency_bucket_and_unavailable_cohort_markdown(self):
        models = workspace_candidates(
            observation("claude-a-slow", 85),
            observation("claude-z-fast", 85),
            observation("gpt-other-bucket", 85),
            observation("claude-a-slow", 40, metric="seconds-per-task", cohort="lat", unit="seconds"),
            observation("claude-z-fast", 15, metric="seconds-per-task", cohort="lat", unit="seconds"),
            observation("gpt-other-bucket", 10, metric="estimated-seconds-per-task", cohort="lat", unit="seconds"),
        )
        now = resolve_lanes.parse_iso_utc("2026-11-21T16:00:00Z")
        states, _ = resolve_lanes.parse_provider_state(
            {
                "claude": {"weekly_pct": 20, "observed_at": "2026-11-21T15:59:00Z"},
                "codex": {"weekly_pct": 88, "observed_at": "2026-11-21T15:59:00Z"},
            },
            now,
            5,
        )
        lanes = resolve_lanes.parse_authorized_lanes(profile_text(*(
            authorized_lane(resolve_lanes.canonical_model_id(c["model"]), c["effort"], c["pool"], roles=("coding",))
            for c in models
        )))
        report = resolve_lanes.resolve_lanes(
            models, states, role="coding", authorized_lanes=lanes, state_loaded=True
        )
        self.assertEqual(
            [c["model"] for c in report["ranked"]],
            ["claude-z-fast", "claude-a-slow", "gpt-other-bucket"],
        )

    def test_l1_unshared_source_outlier_does_not_wipe_out_matched_live_scores(self):
        archive = resolve_lanes.parse_historical_candidates(resolve_lanes.BUNDLED_MEASUREMENTS.read_text())
        live = workspace_candidates(
            observation("claude-opus-5-5", 99, cohort="aa-v6", source="aa"),
            observation("gpt-6.2-sol", 85, cohort="aa-v6", source="aa"),
            observation("deepseek-v4.1-flash-1017", 60, cohort="aa-v6", source="vendor-blog"),
        )
        merged = resolve_lanes.merge_candidates(archive, live)
        lanes = resolve_lanes.parse_authorized_lanes(profile_text(
            authorized_lane("claude-opus-5-5", "high", "claude", roles=("coding",)),
            authorized_lane("gpt-6.2-sol", "high", "codex", roles=("coding",)),
            authorized_lane("deepseek-v4.1-flash-1017", "high", "deepseek", roles=("coding",)),
        ))

        for cohort in (None, "aa-v6"):
            with self.subTest(cohort=cohort):
                report = resolve_lanes.resolve_lanes(merged, {}, role="coding", cohort=cohort, authorized_lanes=lanes)
                self.assertEqual(report["score_basis"], "workspace")
                self.assertEqual(report["score_cohort"], "aa-v6")
                self.assertEqual(report["recommended"]["model"], "claude-opus-5-5")
                by_model = {r["model"]: r for r in report["ranked"]}
                self.assertEqual(by_model["claude-opus-5-5"]["score"], 99.0)
                self.assertEqual(by_model["gpt-6.2-sol"]["score"], 85.0)
                self.assertIsNone(by_model["deepseek-v4.1-flash-1017"]["score"])
                self.assertEqual(by_model["deepseek-v4.1-flash-1017"]["tier"], "unmeasured")
                self.assertTrue(any("excluded unshared-source" in w for w in report["warnings"]))

    def test_l1_comparable_subset_deterministic_tie_break(self):
        # 2 models share 2 sources (zz, yy) vs 2 models share 1 source (aa) -> larger shared source count wins
        models = workspace_candidates(
            observation("m1", 80, cohort="c1", source="zz"),
            observation("m1", 82, cohort="c1", source="yy"),
            observation("m2", 78, cohort="c1", source="zz"),
            observation("m2", 80, cohort="c1", source="yy"),
            observation("m3", 99, cohort="c1", source="aa"),
            observation("m4", 98, cohort="c1", source="aa"),
        )
        report = rank_authorized(models, cohort="c1")
        by_model = {r["model"]: r for r in report["ranked"]}
        self.assertEqual(by_model["m1"]["score"], 81.0)
        self.assertEqual(by_model["m2"]["score"], 79.0)
        self.assertIsNone(by_model["m3"]["score"])
        self.assertIsNone(by_model["m4"]["score"])

        # Same candidate count & same shared source count -> lexicographically smaller source tuple ('aa' < 'zz') wins
        tie_models = workspace_candidates(
            observation("a1", 80, cohort="c1", source="zz"),
            observation("a2", 75, cohort="c1", source="zz"),
            observation("b1", 90, cohort="c1", source="aa"),
            observation("b2", 85, cohort="c1", source="aa"),
        )
        tie_report = rank_authorized(tie_models, cohort="c1")
        tie_by_model = {r["model"]: r for r in tie_report["ranked"]}
        self.assertEqual(tie_by_model["b1"]["score"], 90.0)
        self.assertEqual(tie_by_model["b2"]["score"], 85.0)
        self.assertIsNone(tie_by_model["a1"]["score"])

    def test_l4_direct_review_metric_survives_unmatched_accuracy_and_reasoning(self):
        models = workspace_candidates(
            observation("claude-opus-5-5", 88, metric="review", cohort="rev-v1", source="aa"),
            observation("gpt-6.2-sol", 82, metric="review", cohort="rev-v1", source="aa"),
            observation("claude-opus-5-5", 70, metric="accuracy", cohort="rev-v1", source="src-a"),
            observation("claude-opus-5-5", 70, metric="reasoning", cohort="rev-v1", source="src-a"),
            observation("deepseek-v4.1-flash-1017", 60, metric="accuracy", cohort="rev-v1", source="src-b"),
            observation("deepseek-v4.1-flash-1017", 60, metric="reasoning", cohort="rev-v1", source="src-b"),
        )
        report = rank_authorized(models, role="review", cohort="rev-v1")
        self.assertEqual(report["score_basis"], "workspace")
        self.assertEqual(report["recommended"]["model"], "claude-opus-5-5")
        by_model = {r["model"]: r for r in report["ranked"]}
        self.assertEqual(by_model["claude-opus-5-5"]["score"], 88.0)
        self.assertEqual(by_model["gpt-6.2-sol"]["score"], 82.0)
        self.assertIsNone(by_model["deepseek-v4.1-flash-1017"]["score"])

    def test_l2_single_live_same_family_reviewer_cannot_beat_cross_family_reviewers(self):
        archive = resolve_lanes.parse_historical_candidates(resolve_lanes.BUNDLED_MEASUREMENTS.read_text())
        live = workspace_candidates(
            observation("claude-opus-5-5", 30, metric="accuracy", cohort="live-1", source="aa"),
            observation("claude-opus-5-5", 30, metric="reasoning", cohort="live-1", source="aa"),
        )
        merged = resolve_lanes.merge_candidates(archive, live)
        lanes = resolve_lanes.parse_authorized_lanes(profile_text(
            authorized_lane("claude-opus-5-5", "high", "claude", roles=("review",)),
            authorized_lane("gpt-6.2-sol", "high", "codex", roles=("review",)),
        ))

        # Auto-cohort falls back to historical so cross-family gpt-6.2-sol wins fairly.
        auto = resolve_lanes.resolve_lanes(
            merged, {}, role="review", author_family="claude", authorized_lanes=lanes
        )
        self.assertEqual(auto["score_basis"], "historical")
        self.assertEqual(auto["recommended"]["model"], "gpt-6.2-sol")
        self.assertFalse(auto["recommended"]["same_family"])
        self.assertTrue(any("falling back to historical" in w for w in auto["warnings"]))

        # Explicit --cohort keeps live cohort, warns, puts cross-family first, and never recommends same-family.
        explicit = resolve_lanes.resolve_lanes(
            merged, {}, role="review", author_family="claude", cohort="live-1", authorized_lanes=lanes
        )
        self.assertEqual(explicit["score_basis"], "workspace")
        self.assertIsNone(explicit["recommended"])
        self.assertEqual(explicit["ranked"][0]["model"], "gpt-6.2-sol")
        self.assertEqual(explicit["ranked"][1]["model"], "claude-opus-5-5")
        self.assertTrue(any("no measured cross-family reviewers" in w for w in explicit["warnings"]))

    def test_l10_excluded_lanes_use_active_live_cohort_scores_not_stale_history(self):
        archive = resolve_lanes.parse_historical_candidates(resolve_lanes.BUNDLED_MEASUREMENTS.read_text())
        live = workspace_candidates(
            observation("claude-opus-5-5", 91, cohort="live-v2", source="aa"),
            observation("gpt-6.2-sol", 98, cohort="live-v2", source="aa"),
            observation("brand-new-model", 99, cohort="live-v2", source="aa"),
        )
        merged = resolve_lanes.merge_candidates(archive, live)
        now = resolve_lanes.parse_iso_utc("2026-11-21T16:00:00Z")
        states, _ = resolve_lanes.parse_provider_state(
            {
                "claude": {"weekly_pct": 20, "observed_at": "2026-11-21T15:59:00Z"},
                "codex": {"weekly_pct": 92, "observed_at": "2026-11-21T15:59:00Z"},
            },
            now,
            5,
        )
        lanes = resolve_lanes.parse_authorized_lanes(profile_text(
            authorized_lane("claude-opus-5-5", "high", "claude", roles=("coding",)),
            authorized_lane("gpt-6.2-sol", "high", "codex", roles=("coding",)),
        ))
        report = resolve_lanes.resolve_lanes(
            merged, states, role="coding", authorized_lanes=lanes, state_loaded=True
        )
        self.assertEqual(report["score_basis"], "workspace")
        excluded_by_key = {(r["model"], r["effort"]): r for r in report["excluded"]}
        self.assertEqual(excluded_by_key[("gpt-6.2-sol", "high")]["score"], 98.0)
        self.assertEqual(excluded_by_key[("gpt-6.2-sol", "high")]["source"], "workspace")
        self.assertEqual(excluded_by_key[("brand-new-model", "high")]["score"], 99.0)
        # Historical-only excluded lane must NOT display stale historical score during active live cohort.
        self.assertIsNone(excluded_by_key[("Haiku 5.5", "high")]["score"])

        # Unavailable named cohort clears excluded scores too.
        unavail = resolve_lanes.resolve_lanes(
            merged, states, role="coding", cohort="missing-cohort", authorized_lanes=lanes, state_loaded=True
        )
        self.assertEqual(unavail["score_basis"], "unavailable")
        self.assertTrue(all(r["score"] is None for r in unavail["excluded"]))

    def test_l11_historical_review_consistent_formula_when_knowledge_missing(self):
        candidates = [
            {
                "model": "with-knowledge",
                "effort": "high",
                "pool": "claude",
                "family": "claude",
                "provider_label": "claude",
                "profiles": {"coding": None, "reasoning": 80.0, "accuracy": 80.0, "knowledge": 40.0},
                "review_override": None,
                "index": None,
                "latency_s": None,
                "source": "historical",
            },
            {
                "model": "no-knowledge",
                "effort": "high",
                "pool": "codex",
                "family": "openai",
                "provider_label": "codex",
                "profiles": {"coding": None, "reasoning": 80.0, "accuracy": 80.0, "knowledge": None},
                "review_override": None,
                "index": None,
                "latency_s": None,
                "source": "historical",
            },
        ]
        res = resolve_lanes.resolve_lanes(candidates, {}, role="review")
        by_model = {r["model"]: r for r in res["ranked"]}
        self.assertEqual(by_model["with-knowledge"]["score"], 80.0)
        self.assertEqual(by_model["no-knowledge"]["score"], 80.0)

    def test_l12_latency_uses_requested_cohort_and_merge_does_not_mutate_inputs(self):
        models = workspace_candidates(
            observation("sample-a", 85, cohort="c2"),
            observation("sample-b", 85, cohort="c2"),
            observation("sample-a", 10, metric="seconds-per-task", cohort="c1", unit="seconds"),
            observation("sample-a", 40, metric="seconds-per-task", cohort="c2", unit="seconds"),
            observation("sample-b", 50, metric="seconds-per-task", cohort="c1", unit="seconds"),
            observation("sample-b", 15, metric="seconds-per-task", cohort="c2", unit="seconds"),
        )
        report = rank_authorized(models, cohort="c2")
        self.assertEqual(report["recommended"]["model"], "sample-b")
        by_model = {r["model"]: r for r in report["ranked"]}
        self.assertEqual(by_model["sample-a"]["latency_s"], 40.0)
        self.assertEqual(by_model["sample-b"]["latency_s"], 15.0)

        # merge_candidates does not mutate caller dicts and overwrites equal dates (>=).
        first = workspace_candidates(observation("sample-a", 80, cohort="c1"))
        second = workspace_candidates(observation("sample-a", 95, cohort="c1"))
        snapshot_before = copy.deepcopy(first)
        merged = resolve_lanes.merge_candidates(first, second)
        self.assertEqual(first, snapshot_before)
        self.assertEqual(
            merged[0]["observations"]["coding"][("c1", "points")]["aa"]["value"],
            95.0,
        )

    def test_l14_parse_workspace_observations_post_delimiter_and_duplicate_block_rejection(self):
        decoy = json.dumps({"measurements": [observation("decoy-model", 99)]})
        real = json.dumps({"measurements": [observation("real-model", 85)]})
        md = (
            "# Baseline\n"
            f"<!-- observations:start -->\n```json\n{decoy}\n```\n<!-- observations:end -->\n"
            "<!-- workspace-measurements:v1 -->\n"
            f"<!-- observations:start -->\n```json\n{real}\n```\n<!-- observations:end -->\n"
        )
        parsed = resolve_lanes.parse_workspace_observations(md)
        self.assertEqual([c["model"] for c in parsed], ["real-model"])

        dup_blocks = (
            "<!-- workspace-measurements:v1 -->\n"
            f"<!-- observations:start -->\n```json\n{real}\n```\n<!-- observations:end -->\n"
            f"<!-- observations:start -->\n```json\n{decoy}\n```\n<!-- observations:end -->\n"
        )
        with self.assertRaisesRegex(ValueError, "multiple observations:start"):
            resolve_lanes.parse_workspace_observations(dup_blocks)

    def test_redteam_cross_family_comparable_group_and_rubric_priority(self):
        # 3 same-family lanes share 'a_src' while 2 cross-family lanes share 'z_src':
        # cross-family review must choose the group containing cross-family reviewers.
        models = workspace_candidates(
            observation("claude-opus-5-5", 90, metric="review", cohort="c1", source="a_src"),
            observation("claude-sonnet-5-5", 88, metric="review", cohort="c1", source="a_src"),
            observation("claude-haiku-5-5", 80, metric="review", cohort="c1", source="a_src"),
            observation("gpt-6.2-sol", 84, metric="review", cohort="c1", source="z_src"),
            observation("gemini-4-neon", 82, metric="review", cohort="c1", source="z_src"),
        )
        lanes = resolve_lanes.parse_authorized_lanes(profile_text(*(
            authorized_lane(c["model"], c["effort"], c["pool"], roles=("review",))
            for c in models
        )))
        report = resolve_lanes.resolve_lanes(
            models, {}, role="review", author_family="claude", cohort="c1", authorized_lanes=lanes
        )
        self.assertEqual(report["recommended"]["model"], "gpt-6.2-sol")
        by_model = {r["model"]: r for r in report["ranked"]}
        self.assertEqual(by_model["gpt-6.2-sol"]["score"], 84.0)
        self.assertEqual(by_model["gemini-4-neon"]["score"], 82.0)
        self.assertIsNone(by_model["claude-opus-5-5"]["score"])

        # accuracy+reasoning covers only same-family while direct review covers cross-family:
        # direct review must be chosen so cross-family reviewers are scored.
        rubric_models = workspace_candidates(
            observation("claude-opus-5-5", 90, metric="accuracy", cohort="c2", source="a_src"),
            observation("claude-opus-5-5", 90, metric="reasoning", cohort="c2", source="a_src"),
            observation("claude-sonnet-5-5", 85, metric="accuracy", cohort="c2", source="a_src"),
            observation("claude-sonnet-5-5", 85, metric="reasoning", cohort="c2", source="a_src"),
            observation("gpt-6.2-sol", 86, metric="review", cohort="c2", source="z_src"),
            observation("gemini-4-neon", 83, metric="review", cohort="c2", source="z_src"),
        )
        rubric_lanes = resolve_lanes.parse_authorized_lanes(profile_text(*(
            authorized_lane(c["model"], c["effort"], c["pool"], roles=("review",))
            for c in rubric_models
        )))
        rubric_report = resolve_lanes.resolve_lanes(
            rubric_models, {}, role="review", author_family="claude", cohort="c2", authorized_lanes=rubric_lanes
        )
        self.assertEqual(rubric_report["recommended"]["model"], "gpt-6.2-sol")
        self.assertEqual(rubric_report["recommended"]["score"], 86.0)

    def test_redteam_excluded_live_review_does_not_mix_knowledge_formulas(self):
        models = workspace_candidates(
            observation("claude-opus-5-5", 80, metric="accuracy", cohort="rev", source="aa"),
            observation("claude-opus-5-5", 80, metric="reasoning", cohort="rev", source="aa"),
            observation("claude-opus-5-5", 40, metric="knowledge", cohort="rev", source="aa"),
            observation("gemini-4-neon", 80, metric="accuracy", cohort="rev", source="aa"),
            observation("gemini-4-neon", 80, metric="reasoning", cohort="rev", source="aa"),
            observation("gemini-4-neon", 50, metric="knowledge", cohort="rev", source="aa"),
            observation("gpt-6.2-sol", 80, metric="accuracy", cohort="rev", source="aa"),
            observation("gpt-6.2-sol", 80, metric="reasoning", cohort="rev", source="aa"),
        )
        now = resolve_lanes.parse_iso_utc("2026-11-21T16:00:00Z")
        states, _ = resolve_lanes.parse_provider_state(
            {
                "claude": {"weekly_pct": 20, "observed_at": "2026-11-21T15:59:00Z"},
                "gemini": {"weekly_pct": 20, "observed_at": "2026-11-21T15:59:00Z"},
                "codex": {"weekly_pct": 95, "observed_at": "2026-11-21T15:59:00Z"},
            },
            now,
            5,
        )
        report = resolve_lanes.resolve_lanes(models, states, role="review", cohort="rev", state_loaded=True)
        # Eligible lanes used 0.5/0.3/0.2 with knowledge; excluded gpt-6.2-sol lacks knowledge -> must be None, not 80.0.
        self.assertEqual(report["ranked"][0]["score"], 74.0)
        self.assertEqual(report["ranked"][1]["score"], 72.0)
        self.assertEqual(report["excluded"][0]["model"], "gpt-6.2-sol")
        self.assertIsNone(report["excluded"][0]["score"])

    def test_redteam_workspace_observations_case_insensitive_model_provider_lookup(self):
        payload = {
            "models": [
                {
                    "model": "GPT-7-Custom",
                    "provider": "myprov",
                    "released": "2026-11-21",
                    "url": "https://example.com/model",
                }
            ],
            "measurements": [
                observation("gpt-7-custom", 91, metric="coding", cohort="c1", source="aa"),
            ],
        }
        md = (
            "<!-- workspace-measurements:v1 -->\n"
            "<!-- observations:start -->\n```json\n"
            + json.dumps(payload)
            + "\n```\n<!-- observations:end -->\n"
        )
        parsed = resolve_lanes.parse_workspace_observations(md)
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0]["model"], "GPT-7-Custom")
        self.assertEqual(parsed[0]["effort"], "high")
        self.assertEqual(parsed[0]["pool"], "myprov")
        self.assertEqual(parsed[0]["family"], "myprov")

    def test_redteam_case_insensitive_cohort_and_source_matching(self):
        models = workspace_candidates(
            observation("claude-opus-5-5", 90, metric="coding", cohort="C1", source="AA"),
            observation("gpt-6.2-sol", 84, metric="coding", cohort="c1", source="aa"),
            observation("claude-opus-5-5", 20, metric="seconds-per-task", cohort="C1", unit="seconds", source="AA"),
            observation("gpt-6.2-sol", 10, metric="seconds-per-task", cohort="c1", unit="seconds", source="aa"),
        )
        # Auto-cohort must recognize C1 and c1 as a single cohort and AA/aa as a shared source.
        auto = rank_authorized(models)
        self.assertEqual(auto["score_basis"], "workspace")
        self.assertEqual(auto["score_cohort"], "c1")
        self.assertEqual(auto["recommended"]["model"], "claude-opus-5-5")
        self.assertEqual([(r["model"], r["score"]) for r in auto["ranked"]], [
            ("claude-opus-5-5", 90.0), ("gpt-6.2-sol", 84.0),
        ])
        self.assertEqual(auto["warnings"], [])

        # Explicit mixed-case --cohort C1 matches canonical cohort c1 and resolves latency.
        explicit = rank_authorized(models, cohort="C1")
        self.assertEqual(explicit["score_basis"], "workspace")
        self.assertEqual(explicit["score_cohort"], "c1")
        self.assertEqual(explicit["ranked"][0]["latency_s"], 20.0)
        self.assertEqual(explicit["ranked"][1]["latency_s"], 10.0)

        # Unavailable mixed-case --cohort preserves requested name in report.
        missing = rank_authorized(models, cohort="Missing-Cohort")
        self.assertEqual(missing["score_basis"], "unavailable")
        self.assertEqual(missing["score_cohort"], "Missing-Cohort")


if __name__ == "__main__":
    unittest.main()
