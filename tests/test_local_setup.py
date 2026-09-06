"""Local server contracts that otherwise silently trigger keyword fallback."""
import os
import unittest
from unittest.mock import patch

import httpx
from langchain_openai import OpenAIEmbeddings

from parcelco.llm import embed_model, model_name
from parcelco.rag import _embedding_text


class LocalSetupTests(unittest.TestCase):
    def test_default_model_and_override(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(model_name(), "qwen3.5-4b")
        with patch.dict(os.environ, {"PARCELCO_MODEL": "custom-loaded-id"}):
            self.assertEqual(model_name(), "custom-loaded-id")

    def test_embeddings_send_strings_over_http(self):
        import json

        def handle(request):
            body = json.loads(request.content)
            self.assertEqual(body["input"], ["search_query: refund"])
            return httpx.Response(200, json={
                "data": [{"index": 0, "embedding": [0.1, 0.2, 0.3]}],
                "usage": {"prompt_tokens": 3, "total_tokens": 3},
            })

        config = embed_model()
        with httpx.Client(transport=httpx.MockTransport(handle)) as client:
            emb = OpenAIEmbeddings(
                model=config.model, api_key="test", base_url="http://localhost/v1",
                check_embedding_ctx_length=config.check_embedding_ctx_length,
                http_client=client,
            )
            self.assertEqual(emb.embed_query("search_query: refund"), [0.1, 0.2, 0.3])

    def test_nomic_task_prefixes(self):
        model = "text-embedding-nomic-embed-text-v1.5"
        self.assertEqual(_embedding_text("refund", query=True, model=model), "search_query: refund")
        self.assertEqual(_embedding_text("policy", query=False, model=model), "search_document: policy")
        self.assertEqual(_embedding_text("policy", query=False, model="other"), "policy")
