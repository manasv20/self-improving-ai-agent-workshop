"""Unit tests for participant-friendly doctor diagnostics."""

from __future__ import annotations

import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import Mock

from parcelco.doctor import (
    DoctorProbes,
    DoctorSettings,
    check_setup,
    main,
    run_doctor,
)

SETTINGS = DoctorSettings(
    python_version="3.12.6",
    chat_model="qwen3.5-4b",
    embedding_model="nomic-embed",
    base_url="http://127.0.0.1:1234/v1",
)
DATASET = {
    "mode": "demo",
    "active_total": 47,
    "active_improve": 28,
    "active_holdout": 19,
    "catalog_total": 1000,
    "catalog_improve": 700,
    "catalog_holdout": 300,
}


def probes(**overrides: object) -> DoctorProbes:
    values = {
        "chat_reply": Mock(return_value="pong"),
        "embedding_vector": Mock(return_value=[0.1, 0.2, 0.3]),
        "vector_documents": Mock(return_value=["policy", "refunds"]),
        "keyword_documents": Mock(return_value=["policy"]),
        "dataset_info": Mock(return_value=DATASET),
    }
    values.update(overrides)
    return DoctorProbes(**values)  # type: ignore[arg-type]


class DoctorTests(unittest.TestCase):
    def test_success_reports_configuration_counts_and_ready(self):
        report = run_doctor(settings=SETTINGS, probes=probes())

        self.assertTrue(report.ready)
        self.assertEqual(report.exit_code, 0)
        self.assertEqual(report.retrieval_mode, "vector")
        output = report.render()
        self.assertIn("PASS Python: 3.12.6", output)
        self.assertIn("chat=qwen3.5-4b", output)
        self.assertIn("base_url=http://127.0.0.1:1234/v1", output)
        self.assertIn("active=47 (improve=28, holdout=19)", output)
        self.assertIn("catalog=1,000 (improve=700, holdout=300)", output)
        self.assertIn("PASS Chat model", output)
        self.assertIn("PASS Embeddings", output)
        self.assertIn("PASS Chroma", output)
        self.assertIn("Ready: chat and vector retrieval are working.", output)

    def test_chat_connection_failure_is_actionable_and_fatal(self):
        local_probes = probes(
            chat_reply=Mock(side_effect=ConnectionRefusedError("Connection refused"))
        )

        report = run_doctor(settings=SETTINGS, probes=local_probes)

        self.assertFalse(report.ready)
        self.assertEqual(report.exit_code, 1)
        output = report.render()
        self.assertIn("FAIL Chat model", output)
        self.assertIn("cannot reach LM Studio", output)
        self.assertIn("Start the local server", output)
        self.assertIn("OPENAI_BASE_URL", output)
        self.assertIn("Not ready:", output)
        self.assertNotIn("Traceback", output)

    def test_wrong_chat_model_points_to_exact_api_id(self):
        local_probes = probes(
            chat_reply=Mock(
                side_effect=RuntimeError(
                    "The model qwen-old was not found on the server"
                )
            )
        )

        report = run_doctor(settings=SETTINGS, probes=local_probes)

        self.assertFalse(report.ready)
        output = report.render()
        self.assertIn("model 'qwen3.5-4b' is not available", output)
        self.assertIn("PARCELCO_MODEL", output)
        self.assertIn("/v1/models", output)

    def test_missing_embedding_model_warns_and_confirms_keyword_fallback(self):
        vector_probe = Mock(return_value=["should not run"])
        local_probes = probes(
            embedding_vector=Mock(side_effect=RuntimeError("model not found")),
            vector_documents=vector_probe,
            keyword_documents=Mock(return_value=["policy", "faq"]),
        )

        report = run_doctor(settings=SETTINGS, probes=local_probes)

        self.assertTrue(report.ready)
        self.assertEqual(report.exit_code, 0)
        self.assertEqual(report.retrieval_mode, "keyword")
        output = report.render()
        self.assertIn("WARN Embeddings", output)
        self.assertIn("PARCELCO_EMBED_MODEL", output)
        self.assertIn("WARN Chroma: skipped", output)
        self.assertIn("PASS Keyword fallback: confirmed", output)
        self.assertIn(
            "Ready: chat is working; keyword retrieval fallback is confirmed.", output
        )
        vector_probe.assert_not_called()

    def test_strict_embedding_failure_is_fatal_even_with_keyword_fallback(self):
        local_probes = probes(
            embedding_vector=Mock(side_effect=TimeoutError("request timed out")),
            keyword_documents=Mock(return_value=["policy"]),
        )

        report = run_doctor(
            strict_embeddings=True, settings=SETTINGS, probes=local_probes
        )

        self.assertFalse(report.ready)
        self.assertEqual(report.exit_code, 1)
        output = report.render()
        self.assertIn("FAIL Embeddings", output)
        self.assertIn("FAIL Chroma: skipped", output)
        self.assertIn("PASS Keyword fallback", output)
        self.assertIn("Not ready:", output)

    def test_chroma_failure_warns_normally_and_fails_in_strict_mode(self):
        chroma_failure = Mock(
            side_effect=RuntimeError("embedding dimension does not match collection")
        )
        local_probes = probes(
            vector_documents=chroma_failure,
            keyword_documents=Mock(return_value=["policy"]),
        )

        normal = run_doctor(settings=SETTINGS, probes=local_probes)
        strict = run_doctor(
            strict_embeddings=True, settings=SETTINGS, probes=local_probes
        )

        self.assertTrue(normal.ready)
        self.assertIn("WARN Chroma", normal.render())
        self.assertIn("rebuild_index", normal.render())
        self.assertFalse(strict.ready)
        self.assertIn("FAIL Chroma", strict.render())

    def test_check_setup_prints_only_concise_report(self):
        stream = io.StringIO()
        local_probes = probes(
            chat_reply=Mock(side_effect=RuntimeError("bad\n" + "x" * 500))
        )

        with redirect_stdout(stream):
            report = check_setup(settings=SETTINGS, probes=local_probes)

        self.assertFalse(report.ready)
        self.assertNotIn("Traceback", stream.getvalue())
        self.assertLess(max(map(len, stream.getvalue().splitlines())), 400)

    def test_main_returns_nonzero_for_required_failure(self):
        # Cover CLI plumbing without invoking any external service.
        from parcelco import doctor

        original = doctor.check_setup
        doctor.check_setup = Mock(
            return_value=run_doctor(
                strict_embeddings=True,
                settings=SETTINGS,
                probes=probes(
                    embedding_vector=Mock(side_effect=RuntimeError("model not found"))
                ),
            )
        )
        try:
            self.assertEqual(main(["--strict-embeddings"]), 1)
            doctor.check_setup.assert_called_once_with(strict_embeddings=True)
        finally:
            doctor.check_setup = original


if __name__ == "__main__":
    unittest.main()
