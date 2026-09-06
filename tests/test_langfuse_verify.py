"""LangFuse is used for shared evidence — not as the policy grader."""
from __future__ import annotations

import unittest
from unittest.mock import patch

from parcelco.tracing import verify_run_against_langfuse


class TestLangfuseVerify(unittest.TestCase):
    def test_confirmed_when_generations_match_heals(self):
        fake = {
            "enabled": True,
            "trace_id": "t1",
            "url": "http://localhost:3000/t1",
            "generation_count": 3,
            "total_latency_s": 12.0,
            "generations": [{}, {}, {}],
            "scores": [],
            "error": None,
        }
        with patch("parcelco.tracing.fetch_trace_evidence", return_value=fake):
            with patch("parcelco.tracing.score_trace"):
                ev = verify_run_against_langfuse("t1", heal_count=2, passed=False)
        self.assertTrue(ev["verified"])
        self.assertEqual(ev["verdict"], "confirmed")
        self.assertEqual(ev["expected_generations"], 3)

    def test_mismatch_when_too_few_generations(self):
        fake = {
            "enabled": True,
            "trace_id": "t1",
            "url": "http://x",
            "generation_count": 1,
            "total_latency_s": 1.0,
            "generations": [{}],
            "scores": [],
            "error": None,
        }
        with patch("parcelco.tracing.fetch_trace_evidence", return_value=fake):
            with patch("parcelco.tracing.score_trace"):
                ev = verify_run_against_langfuse("t1", heal_count=2, passed=False)
        self.assertFalse(ev["verified"])
        self.assertEqual(ev["verdict"], "mismatch")


if __name__ == "__main__":
    unittest.main()
