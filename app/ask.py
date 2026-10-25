"""Lecture 01: a script that asks a bare LLM a single question or chats interactively.

Usage:
    uv run python -m app.ask "What is LoRA?"
    uv run python -m app.ask            # Ask a course-specific question if none is supplied
    uv run python -m app.ask --chat     # Interactive chat mode keeping conversation history

A "bare" call with no tools or conversation history.
Check that, when asked about course-specific information, it either says "I don't know"
or gives a plausible general answer (which differs from the actual course).
(In Lecture 03, improve it by making an agent that can search the glossary.)
"""

import argparse
import sys

from google import genai
from google.genai import errors

from app.config import MODEL, api_error_message, get_api_key

# A course-specific question. The correct answer is in homework-levels in data/glossary.json
DEFAULT_QUESTION = "What are the 3 homework levels in the AIE2026 course?"


def _display_tokens(response) -> None:
    """Helper to display input and output token counts if usage metadata is available."""
    metadata = getattr(response, "usage_metadata", None)
    if metadata:
        in_tokens = getattr(metadata, "prompt_token_count", 0)
        out_tokens = getattr(metadata, "candidates_token_count", 0)
        print(f"[tokens] input: {in_tokens}, output: {out_tokens}")


def ask(question: str, client: genai.Client | None = None, model: str = MODEL) -> str:
    if client is None:
        client = genai.Client(api_key=get_api_key())
    response = client.models.generate_content(model=model, contents=question)

    # TODO(Lecture 01 exercise): use response.usage_metadata to
    #   display input and output token counts (you may ask Copilot)
    _display_tokens(response)

    return response.text or ""


def chat_turn(
    history: list[dict],
    user_message: str,
    client: genai.Client | None = None,
    model: str = MODEL,
) -> str:
    """Execute a single turn in a conversation, updating the provided history list in place."""
    if client is None:
        client = genai.Client(api_key=get_api_key())

    history.append({"role": "user", "parts": [{"text": user_message}]})
    response = client.models.generate_content(model=model, contents=history)
    answer = response.text or ""
    history.append({"role": "model", "parts": [{"text": answer}]})

    _display_tokens(response)
    return answer


def chat_loop(client: genai.Client | None = None, model: str = MODEL) -> None:
    """Run an interactive chat loop that keeps conversation history across turns."""
    if client is None:
        client = genai.Client(api_key=get_api_key())

    print(f"[model] {model}")
    print("Interactive chat mode. Type 'exit', 'quit' or press Ctrl-D / Ctrl-Z to quit.\n")

    history: list[dict] = []
    while True:
        try:
            user_input = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting chat.")
            break

        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit"):
            print("Exiting chat.")
            break

        try:
            answer = chat_turn(history, user_input, client=client, model=model)
            print(f"\n{answer}\n")
        except errors.APIError as e:
            print(api_error_message(e.code, e.message))


def main() -> None:
    parser = argparse.ArgumentParser(description="Ask a bare LLM a question")
    parser.add_argument("question", nargs="?", default=DEFAULT_QUESTION)
    parser.add_argument(
        "--chat",
        action="store_true",
        help="Interactive mode: keep conversation history for follow-up questions",
    )
    args = parser.parse_args()

    if args.chat:
        chat_loop()
        return

    print(f"[model] {MODEL}")
    print(f"[question] {args.question}\n")
    try:
        print(ask(args.question))
    except errors.APIError as e:
        print(api_error_message(e.code, e.message))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
