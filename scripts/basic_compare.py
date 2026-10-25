"""Basic level: ask the same question 3 times for each model and save results."""

import json
import os
import sys
import time
from pathlib import Path

from google import genai
from google.genai import errors

MODELS = [
    "gemini-3.5-flash-lite",
    "gemini-3.5-flash",
    "gemini-3.1-flash-lite",
]

QUESTION = "Explain LoRA in 3 sentences."
REPEATS = 3
OUT_DIR = Path(__file__).resolve().parent / "out"
OUT_FILE = OUT_DIR / "basic_results.json"


def call_with_retry(client: genai.Client, model: str, prompt: str, max_retries: int = 5):
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(model=model, contents=prompt)
            in_tokens = response.usage_metadata.prompt_token_count if response.usage_metadata else None
            out_tokens = response.usage_metadata.candidates_token_count if response.usage_metadata else None
            return {
                "text": response.text or "",
                "in_tokens": in_tokens,
                "out_tokens": out_tokens,
                "error": None,
                "attempts": attempt + 1,
            }
        except errors.APIError as e:
            if e.code in (429, 503) and attempt < max_retries - 1:
                wait_time = (2 ** attempt) * 2 + 1
                print(f"[retry] Model {model} hit {e.code}. Waiting {wait_time}s before attempt {attempt + 2}...")
                time.sleep(wait_time)
            else:
                return {
                    "text": None,
                    "in_tokens": None,
                    "out_tokens": None,
                    "error": f"APIError {e.code}: {e.message}",
                    "attempts": attempt + 1,
                }
        except Exception as e:
            return {
                "text": None,
                "in_tokens": None,
                "out_tokens": None,
                "error": str(e),
                "attempts": attempt + 1,
            }


def main():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY environment variable is not set.", file=sys.stderr)
        sys.exit(1)

    client = genai.Client(api_key=api_key)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Running Basic Comparison: 3 models x {REPEATS} repeats")
    print(f"Question: \"{QUESTION}\"\n")

    results = []

    for model in MODELS:
        print(f"=== Model: {model} ===")
        for run_idx in range(1, REPEATS + 1):
            print(f"  Run {run_idx}/{REPEATS}...", end=" ", flush=True)
            t0 = time.perf_counter()
            res = call_with_retry(client, model, QUESTION)
            elapsed = time.perf_counter() - t0
            res["model"] = model
            res["run"] = run_idx
            res["elapsed_sec"] = round(elapsed, 3)
            results.append(res)

            if res["error"]:
                print(f"FAILED ({res['error']}) in {elapsed:.2f}s")
            else:
                print(f"OK ({res['out_tokens']} tokens, {elapsed:.2f}s)")
            time.sleep(1)  # small pause to be gentle with rate limits

    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(
            {
                "question": QUESTION,
                "models": MODELS,
                "repeats": REPEATS,
                "results": results,
            },
            f,
            indent=2,
            ensure_ascii=False,
        )

    print(f"\nAll results saved to {OUT_FILE}")


if __name__ == "__main__":
    main()
