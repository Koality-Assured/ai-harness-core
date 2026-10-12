"""Unit tests for adaptive quota management and pacing helper.

tags: [tests, pacing, quota, routing]
routing_hints: [tests, pacing, quota-management]

Run: python -m unittest scripts.tests.test_pacing -v
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_SCRIPTS))
sys.path.insert(0, str(_SCRIPTS / "_lib"))

from pacing import (
    check_secondary_availability,
    chunk_tasks,
    clear_secondary_exhaustion,
    format_schedule_wakeup,
    load_quota_profiles,
    parse_reset_duration,
    record_secondary_exhaustion,
    resolve_quota_profile,
)


class PacingUnitTests(unittest.TestCase):
    def test_parse_reset_duration_hms(self) -> None:
        err = "RESOURCE_EXHAUSTED (code 429): Individual quota reached. Please upgrade your subscription to increase your limits. Resets in 4h57m0s."
        sec = parse_reset_duration(err)
        self.assertEqual(sec, 4 * 3600 + 57 * 60)

    def test_parse_reset_duration_hm(self) -> None:
        err = "Rate limited. Resets in 2h30m."
        sec = parse_reset_duration(err)
        self.assertEqual(sec, 2 * 3600 + 30 * 60)

    def test_parse_reset_duration_minutes_seconds(self) -> None:
        err = "Resets in 45m10s"
        sec = parse_reset_duration(err)
        self.assertEqual(sec, 45 * 60 + 10)

    def test_parse_reset_duration_seconds_only(self) -> None:
        err = "Resets in 30s"
        sec = parse_reset_duration(err)
        self.assertEqual(sec, 30)

    def test_parse_reset_duration_retry_after(self) -> None:
        err = "HTTP 429: Too Many Requests. retry-after: 120"
        sec = parse_reset_duration(err)
        self.assertEqual(sec, 120)

    def test_parse_reset_duration_none(self) -> None:
        self.assertIsNone(parse_reset_duration("Generic 500 internal server error"))
        self.assertIsNone(parse_reset_duration(""))

    def test_resolve_quota_profile_enterprise_cursor(self) -> None:
        self.assertEqual(resolve_quota_profile(host="cursor"), "unmetered")
        self.assertEqual(resolve_quota_profile(host="enterprise"), "unmetered")

    def test_resolve_quota_profile_secondary_antigravity(self) -> None:
        self.assertEqual(
            resolve_quota_profile(host="antigravity", model_name="Claude Opus 4.6 (Thinking)"),
            "metered_secondary",
        )
        self.assertEqual(
            resolve_quota_profile(host="antigravity", model_name="Claude 5.5 Sonnet"),
            "metered_secondary",
        )
        self.assertEqual(
            resolve_quota_profile(host="antigravity", model_name="GPT 6.0 Luna"),
            "metered_secondary",
        )
        self.assertEqual(
            resolve_quota_profile(host="antigravity", model_name="gpt-4o"),
            "metered_secondary",
        )

    def test_resolve_quota_profile_native_antigravity(self) -> None:
        self.assertEqual(
            resolve_quota_profile(host="antigravity", model_name="Gemini 3.8 Flash"),
            "standard",
        )
        self.assertEqual(
            resolve_quota_profile(host="antigravity", model_name="Gemini 3.8 Flash (High)"),
            "standard",
        )
        self.assertEqual(
            resolve_quota_profile(host="antigravity", model_name="Gemini 3.8 Pro"),
            "standard",
        )
        self.assertEqual(
            resolve_quota_profile(host="antigravity", model_name=None),
            "standard",
        )

    def test_quota_state_exhaustion_lifecycle(self) -> None:
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            tmproot = Path(tmpdir)
            # Initially available
            avail, rem = check_secondary_availability(tmproot)
            self.assertTrue(avail)
            self.assertEqual(rem, 0)

            # Record exhaustion for 100 seconds
            record_secondary_exhaustion(100, provider="claude", repo_root=tmproot)
            avail, rem = check_secondary_availability(tmproot)
            self.assertFalse(avail)
            self.assertGreater(rem, 0)
            self.assertLessEqual(rem, 100)

            # Clear exhaustion
            clear_secondary_exhaustion(tmproot)
            avail, rem = check_secondary_availability(tmproot)
            self.assertTrue(avail)
            self.assertEqual(rem, 0)

    def test_resolve_quota_profile_env_override(self) -> None:
        self.assertEqual(
            resolve_quota_profile(
                host="antigravity",
                model_name="Claude Opus 4.6",
                env_override="unmetered",
            ),
            "unmetered",
        )

    def test_chunk_tasks(self) -> None:
        tasks = ["task1", "task2", "task3", "task4", "task5"]
        chunks = chunk_tasks(tasks, max_concurrency=2)
        self.assertEqual(chunks, [["task1", "task2"], ["task3", "task4"], ["task5"]])

    def test_chunk_tasks_single(self) -> None:
        tasks = ["t1", "t2", "t3"]
        chunks = chunk_tasks(tasks, max_concurrency=1)
        self.assertEqual(chunks, [["t1"], ["t2"], ["t3"]])

    def test_format_schedule_wakeup(self) -> None:
        payload = format_schedule_wakeup(17820, "Resume batch 2")
        self.assertEqual(payload["DurationSeconds"], 17820)
        self.assertEqual(payload["Prompt"], "Resume batch 2")
        self.assertEqual(payload["TimerCondition"], "never")

    def test_load_quota_profiles(self) -> None:
        profiles = load_quota_profiles()
        self.assertIn("unmetered", profiles)
        self.assertIn("standard", profiles)
        self.assertIn("metered_secondary", profiles)


if __name__ == "__main__":
    unittest.main()
