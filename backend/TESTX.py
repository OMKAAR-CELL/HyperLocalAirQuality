
import os
from pathlib import Path

from dotenv import load_dotenv
from groq import Groq
from groq import APIConnectionError, APIStatusError

# Load .env from the project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

api_key = os.getenv("GROQ_API_KEY")

if not api_key:
    raise SystemExit(
        "ERROR: GROQ_API_KEY was not found in the project root .env file."
    )

client = Groq(api_key=api_key)

print("Testing Groq API connection...")

try:
    response = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {
                "role": "system",
                "content": "You are an assistant for an air quality monitoring system."
            },
            {
                "role": "user",
                "content": "Reply with exactly: Groq API connected successfully!"
            },
        ],
        max_completion_tokens=60,
    )

    print("\nSUCCESS!")
    print("Model:", response.model)
    print("Response:", response.choices[0].message.content)

except APIStatusError as exc:
    print(f"\nGroq API returned HTTP {exc.status_code}.")
    print("Details:", exc.message)

except APIConnectionError as exc:
    print("\nCould not connect to Groq.")
    print("Check your internet connection.")
    print("Details:", exc)

except Exception as exc:
    print(f"\nUnexpected error: {type(exc).__name__}: {exc}")
