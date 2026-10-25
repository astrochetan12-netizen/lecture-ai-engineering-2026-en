"""Advanced benchmark script for measuring latency and token usage across models and question types."""

import csv
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

QUESTIONS = [
    ("factual", "What does the abbreviation LoRA stand for?"),
    ("explanatory", "Explain what Low-Rank Adaptation (LoRA) is and why it reduces GPU memory usage."),
    (
        "long_form",
        "Write a detailed guide comparing full parameter fine-tuning, LoRA, and prompt engineering, covering memory and performance trade-offs.",
    ),
    (
        "reasoning",
        "A 70B model has 80 weight matrices of size 8192x8192. If LoRA is applied with rank r=8, calculate the exact parameter count of these LoRA adapters (A and B matrices) and show steps.",
    ),
]

REPEATS = 3
OUT_DIR = Path(__file__).resolve().parent / "out"
CSV_FILE = OUT_DIR / "benchmark.csv"


def call_with_backoff(client: genai.Client, model: str, prompt: str, max_retries: int = 5):
    retries = 0
    for attempt in range(max_retries):
        try:
            t0 = time.perf_counter()
            response = client.models.generate_content(model=model, contents=prompt)
            latency = time.perf_counter() - t0

            in_tokens = response.usage_metadata.prompt_token_count if response.usage_metadata else 0
            out_tokens = response.usage_metadata.candidates_token_count if response.usage_metadata else 0
            total_tokens = response.usage_metadata.total_token_count if response.usage_metadata else 0

            return {
                "latency_sec": round(latency, 4),
                "in_tokens": in_tokens,
                "out_tokens": out_tokens,
                "total_tokens": total_tokens,
                "retries": retries,
                "error": None,
            }
        except errors.APIError as e:
            if e.code in (429, 503) and attempt < max_retries - 1:
                retries += 1
                wait_time = (2 ** attempt) * 2 + 1
                print(f" [Rate-limit {e.code}: waiting {wait_time}s]", end="", flush=True)
                time.sleep(wait_time)
            else:
                return {
                    "latency_sec": None,
                    "in_tokens": None,
                    "out_tokens": None,
                    "total_tokens": None,
                    "retries": retries,
                    "error": f"APIError_{e.code}",
                }
        except Exception as e:
            return {
                "latency_sec": None,
                "in_tokens": None,
                "out_tokens": None,
                "total_tokens": None,
                "retries": retries,
                "error": str(e),
            }


def main():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY environment variable is not set.", file=sys.stderr)
        sys.exit(1)

    client = genai.Client(api_key=api_key)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    total_runs = len(MODELS) * len(QUESTIONS) * REPEATS
    print(f"Starting Benchmark: {len(MODELS)} models x {len(QUESTIONS)} questions x {REPEATS} repeats = {total_runs} total calls")
    print(f"Results will be written to {CSV_FILE}\n")

    records = []
    current_call = 0

    for model in MODELS:
        print(f"\n==================== Model: {model} ====================")
        for q_type, q_text in QUESTIONS:
            for rep in range(1, REPEATS + 1):
                current_call += 1
                print(f"[{current_call:02d}/{total_runs}] {model} | {q_type:<11} | run {rep}...", end=" ", flush=True)

                res = call_with_backoff(client, model, q_text)
                record = {
                    "model": model,
                    "question_type": q_type,
                    "question_text": q_text,
                    "repeat": rep,
                    "latency_sec": res["latency_sec"],
                    "in_tokens": res["in_tokens"],
                    "out_tokens": res["out_tokens"],
                    "total_tokens": res["total_tokens"],
                    "retries": res["retries"],
                    "error": res["error"],
                }
                records.append(record)

                if res["error"]:
                    print(f"FAILED ({res['error']}) retries={res['retries']}")
                else:
                    print(f"OK: {res['latency_sec']:.2f}s, in={res['in_tokens']}, out={res['out_tokens']} tokens (retries={res['retries']})")

                # Respect rate limits between calls
                time.sleep(1.2)

    # Write CSV
    with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
        fieldnames = [
            "model",
            "question_type",
            "question_text",
            "repeat",
            "latency_sec",
            "in_tokens",
            "out_tokens",
            "total_tokens",
            "retries",
            "error",
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)

    # Print Summary Tables
    print("\n" + "=" * 80)
    print("BENCHMARK SUMMARY BY MODEL")
    print("=" * 80)
    print(f"{'Model':<25} | {'Count':<5} | {'Mean Latency':<12} | {'Min Latency':<11} | {'Max Latency':<11} | {'Mean Out Tok':<12} | {'Retries':<7}")
    print("-" * 95)

    for m in MODELS:
        m_recs = [r for r in records if r["model"] == m and not r["error"]]
        if m_recs:
            latencies = [r["latency_sec"] for r in m_recs]
            out_toks = [r["out_tokens"] for r in m_recs]
            retries = sum(r["retries"] for r in m_recs)
            mean_lat = sum(latencies) / len(latencies)
            min_lat = min(latencies)
            max_lat = max(latencies)
            mean_tok = sum(out_toks) / len(out_toks)
            print(f"{m:<25} | {len(m_recs):<5} | {mean_lat:>10.2f}s | {min_lat:>9.2f}s | {max_lat:>9.2f}s | {mean_tok:>12.1f} | {retries:>7}")
        else:
            print(f"{m:<25} | All calls failed")

    print("\n" + "=" * 80)
    print("BENCHMARK SUMMARY BY QUESTION TYPE")
    print("=" * 80)
    print(f"{'Question Type':<15} | {'Count':<5} | {'Mean Latency':<12} | {'Mean In Tok':<11} | {'Mean Out Tok':<12}")
    print("-" * 65)

    for q_type, _ in QUESTIONS:
        q_recs = [r for r in records if r["question_type"] == q_type and not r["error"]]
        if q_recs:
            latencies = [r["latency_sec"] for r in q_recs]
            in_toks = [r["in_tokens"] for r in q_recs]
            out_toks = [r["out_tokens"] for r in q_recs]
            mean_lat = sum(latencies) / len(latencies)
            mean_in = sum(in_toks) / len(in_toks)
            mean_out = sum(out_toks) / len(out_toks)
            print(f"{q_type:<15} | {len(q_recs):<5} | {mean_lat:>10.2f}s | {mean_in:>11.1f} | {mean_out:>12.1f}")

    print(f"\nFull CSV output saved to {CSV_FILE}")


if __name__ == "__main__":
    main()
