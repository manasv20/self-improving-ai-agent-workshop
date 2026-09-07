"""Server-side result messages must describe only the current run."""
from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from parcelco.web.app import _publish_ticket_result, _ticket_result_detail, app


def _result(*, enabled: bool = False):
    return SimpleNamespace(
        ticket_id="A01",
        passed=True,
        heal_count=0,
        trace_id="trace-1" if enabled else None,
        langfuse_evidence={"enabled": enabled},
    )


class DashboardResultContractTests(unittest.TestCase):
    def test_completion_reasons_are_distinct_and_truthful(self):
        expected_fragments = {
            "learned": "wrote a lesson",
            "holdout": "holdout: Reflect skipped",
            "clean_pass": "clean PASS: nothing to learn",
            "blocked": "blocked by safety filter",
            "rejected": "produced no safe lesson",
        }
        messages = []
        for reason, fragment in expected_fragments.items():
            message = _ticket_result_detail(
                _result(),
                {"reason": reason},
                trace_available=False,
            )
            self.assertIn(fragment, message)
            self.assertIn("LangFuse off: no trace written", message)
            messages.append(message)
        self.assertEqual(len(set(messages)), len(messages))

    def test_enabled_but_unavailable_trace_is_not_called_ready(self):
        result = _result(enabled=True)
        result.langfuse_evidence["error"] = "read failed"
        message = _ticket_result_detail(
            result,
            {"reason": "clean_pass"},
            trace_available=False,
        )
        self.assertIn("verification unavailable", message)
        self.assertNotIn("trace available", message)

    def test_current_run_does_not_reuse_an_old_trace_link(self):
        result = _result()
        result.checklist = SimpleNamespace(model_dump=lambda: {})
        result.draft = "reply"
        result.retrieved = []
        result.steps = []
        result.attempts = []
        with patch("parcelco.web.app.publish") as publish:
            _publish_ticket_result(
                SimpleNamespace(message="ticket", split="improve"),
                result,
                {"reflected": False, "reason": "clean_pass", "lesson": ""},
            )
        event = publish.call_args.args[0]
        self.assertFalse(event["trace_available"])
        self.assertIsNone(event["langfuse_url"])
        self.assertIn("no trace written", event["stack_detail"])

    def test_run_ticket_rejects_missing_or_inactive_id(self):
        client = app.test_client()
        self.assertEqual(client.post("/api/run-ticket", json={}).status_code, 400)
        response = client.post("/api/run-ticket", json={"ticket_id": "NOT-A-TICKET"})
        self.assertEqual(response.status_code, 404)
        self.assertIn("not in the active suite", response.get_json()["error"])

    def test_expected_result_is_hidden_until_revealed(self):
        html = app.test_client().get("/").get_data(as_text=True)
        self.assertIn('id="expected-details" hidden', html)
        self.assertIn('id="btn-reveal-expect"', html)


if __name__ == "__main__":
    unittest.main()
