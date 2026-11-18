
import os
import time
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def generate_response(
    system_prompt: str,
    user_query: str,
    model: str = "openai/gpt-oss-20b"
) -> dict:

    start_time = time.perf_counter()

    completion = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": user_query
            }
        ],
        temperature=0.2,
        max_completion_tokens=1024
    )

    latency = round(
        (time.perf_counter() - start_time) * 1000, 2
    )

    return {
        "response": completion.choices[0].message.content,
        "model": completion.model,
        "provider": "Groq",
        "latency_ms": latency,
        "prompt_tokens": completion.usage.prompt_tokens,
        "completion_tokens": completion.usage.completion_tokens,
        "total_tokens": completion.usage.total_tokens,
        "system_prompt": system_prompt,
        "user_query": user_query
    }
