"""Lecture 02 homework (Advanced): create Q&A data (JSONL) for SFT from the glossary.

Usage:
    uv run python scripts/make_sft_dataset.py > glossary_sft.jsonl
    # or specify output file directly:
    python scripts/make_sft_dataset.py -o data/glossary_sft.jsonl

Upload the resulting file to Colab and use it as LoRA training data.
Try adding question variations, asking about aliases, or holding out a subset for validation.
"""

import argparse
import json
import sys
from pathlib import Path

GLOSSARY = Path(__file__).resolve().parent.parent / "data" / "glossary.json"
TEMPLATES = [
    "What is {term}?",
    "Briefly explain {term}.",
    "Can you explain the meaning of {term}?",
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Create SFT dataset from glossary")
    parser.add_argument("-o", "--output", type=Path, default=None, help="Output file path (default stdout)")
    args = parser.parse_args()

    terms = json.loads(GLOSSARY.read_text(encoding="utf-8"))["terms"]
    out_f = open(args.output, "w", encoding="utf-8") if args.output else sys.stdout
    try:
        if args.output is None and hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        for t in terms:
            for template in TEMPLATES:
                record = {
                    "messages": [
                        {"role": "user", "content": template.format(term=t["term"])},
                        {"role": "assistant", "content": t["definition"]},
                    ]
                }
                out_f.write(json.dumps(record, ensure_ascii=False) + "\n")
    finally:
        if args.output:
            out_f.close()


if __name__ == "__main__":
    main()
