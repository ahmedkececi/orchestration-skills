"""Regression tests for benchmark provenance and compatible lane scoring."""

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


if __name__ == "__main__":
    unittest.main()
