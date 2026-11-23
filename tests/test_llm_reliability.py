"""Offline tests for Groq retry handling. Place in tests/."""
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import llm_engine


def successful_completion():
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="Safe response"))],
        model="openai/gpt-oss-20b",
        usage=SimpleNamespace(prompt_tokens=10, completion_tokens=5, total_tokens=15),
    )


class TestLLMReliability(unittest.TestCase):
    @patch("llm_engine.client.chat.completions.create")
    def test_success_preserves_response_schema(self, create):
        create.return_value = successful_completion()
        result = llm_engine.generate_response("system", "query")
        self.assertEqual(result["response"], "Safe response")
        self.assertEqual(result["total_tokens"], 15)
        self.assertEqual(result["provider"], "Groq")
        self.assertEqual(create.call_count, 1)

    @patch("llm_engine.time.sleep")
    @patch("llm_engine._retry_delay", return_value=0.5)
    @patch("llm_engine.client.chat.completions.create")
    def test_transient_error_retries(self, create, delay, sleep):
        from groq import APIConnectionError
        import httpx
        request = httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")
        create.side_effect = [APIConnectionError(request=request), successful_completion()]
        result = llm_engine.generate_response("system", "query")
        self.assertEqual(result["response"], "Safe response")
        self.assertEqual(create.call_count, 2)
        sleep.assert_called_once_with(0.5)

    @patch("llm_engine.time.sleep")
    @patch("llm_engine._retry_delay", return_value=0)
    @patch("llm_engine.client.chat.completions.create")
    def test_exhausted_retries_raise_specific_error(self, create, delay, sleep):
        from groq import APIConnectionError
        import httpx
        request = httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")
        create.side_effect = APIConnectionError(request=request)
        with self.assertRaises(llm_engine.LLMServiceUnavailable):
            llm_engine.generate_response("system", "query")
        self.assertEqual(create.call_count, llm_engine.MAX_ATTEMPTS)

    @patch("llm_engine.client.chat.completions.create")
    def test_non_retryable_error_is_not_retried(self, create):
        from groq import BadRequestError
        import httpx
        request = httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")
        response = httpx.Response(400, request=request, json={"error": {"message": "invalid"}})
        create.side_effect = BadRequestError("invalid", response=response, body=None)
        with self.assertRaises(BadRequestError):
            llm_engine.generate_response("system", "query")
        self.assertEqual(create.call_count, 1)

    def test_retry_after_header(self):
        error = SimpleNamespace(response=SimpleNamespace(headers={"retry-after": "3"}))
        self.assertEqual(llm_engine._retry_delay(error, 1), 3.0)


if __name__ == "__main__":
    unittest.main()
