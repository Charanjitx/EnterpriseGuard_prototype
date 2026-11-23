"""Shared Groq LLM client with bounded retries for transient failures."""

import os
import random
import re
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

from dotenv import load_dotenv
from groq import APIConnectionError, APITimeoutError, Groq, InternalServerError, RateLimitError

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"), max_retries=0)

MAX_ATTEMPTS = 4
MAX_WAIT_SECONDS = 60.0


class LLMServiceUnavailable(RuntimeError):
    """Transient provider failure persisted after the retry budget."""


def _retry_delay(exc: Exception, retry_number: int) -> float:
    """Use provider retry guidance when available, otherwise bounded backoff."""
    response = getattr(exc, "response", None)
    headers = getattr(response, "headers", {}) or {}

    retry_ms = headers.get("retry-after-ms")
    if retry_ms is not None:
        try:
            return min(MAX_WAIT_SECONDS, max(0.0, float(retry_ms) / 1000))
        except (ValueError, TypeError):
            pass

    retry_after = headers.get("retry-after")
    if retry_after is not None:
        try:
            return min(MAX_WAIT_SECONDS, max(0.0, float(retry_after)))
        except (ValueError, TypeError):
            try:
                date = parsedate_to_datetime(retry_after)
                if date.tzinfo is None:
                    date = date.replace(tzinfo=timezone.utc)
                return min(MAX_WAIT_SECONDS, max(0.0, (date - datetime.now(timezone.utc)).total_seconds()))
            except (ValueError, TypeError, OverflowError):
                pass

    # Groq errors may include "Please try again in 862.5ms" in the message.
    match = re.search(r"try again in\s+([\d.]+)\s*(ms|s)\b", str(exc), re.IGNORECASE)
    if match:
        delay = float(match.group(1)) / (1000 if match.group(2).lower() == "ms" else 1)
        return min(MAX_WAIT_SECONDS, max(0.0, delay))

    return min(MAX_WAIT_SECONDS, (2 ** (retry_number - 1)) + random.uniform(0, 0.5))


def generate_response(
    system_prompt: str,
    user_query: str,
    model: str = "openai/gpt-oss-20b",
) -> dict:
    start_time = time.perf_counter()
    retryable = (RateLimitError, APIConnectionError, APITimeoutError, InternalServerError)

    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            completion = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_query},
                ],
                temperature=0.2,
                max_completion_tokens=1024,
            )
            break
        except retryable as exc:
            if attempt == MAX_ATTEMPTS:
                raise LLMServiceUnavailable(
                    f"Groq request failed after {MAX_ATTEMPTS} attempts "
                    f"for model {model}: {type(exc).__name__}"
                ) from exc
            delay = _retry_delay(exc, attempt)
            print(f"Groq temporary failure ({type(exc).__name__}); retrying in {delay:.2f}s (attempt {attempt + 1}/{MAX_ATTEMPTS}).")
            time.sleep(delay)

    latency = round((time.perf_counter() - start_time) * 1000, 2)
    usage = completion.usage
    return {
        "response": completion.choices[0].message.content,
        "finish_reason": getattr(completion.choices[0], "finish_reason", None),
        "model": completion.model,
        "provider": "Groq",
        "latency_ms": latency,
        "prompt_tokens": usage.prompt_tokens if usage else None,
        "completion_tokens": usage.completion_tokens if usage else None,
        "total_tokens": usage.total_tokens if usage else None,
        "system_prompt": system_prompt,
        "user_query": user_query,
    }
