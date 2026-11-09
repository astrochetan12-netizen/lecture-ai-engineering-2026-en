"""Lecture 03: tools for the agent.

Function docstrings and type hints here become the "tool descriptions" presented to the model.
Rewriting descriptions changes whether the model uses a tool and which arguments it supplies.
"""

import json
import random
import re
from datetime import datetime, timezone
from functools import cache
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
LOG_DIR = Path(__file__).resolve().parent.parent / "learning_log"
MAX_RESULTS = 3


@cache
def load_glossary() -> list[dict]:
    with open(DATA_DIR / "glossary.json", encoding="utf-8") as f:
        return json.load(f)["terms"]


def _normalize(text: str) -> str:
    return text.casefold().replace(" ", "").replace("　", "")


def _names(entry: dict) -> list[str]:
    return [_normalize(entry["term"]), _normalize(entry["id"])] + [
        _normalize(a) for a in entry["aliases"]
    ]


def search_glossary(query: str) -> str:
    """Search the course glossary and return definitions and the sessions that cover the terms.

    Use before answering about AI engineering terms or words specific to this course (AIE2026).
    Put only one term to look up in query (for example, "LoRA").
    """
    q = _normalize(query)
    if not q:
        return "The search query is empty. Specify one term to look up."
    glossary = load_glossary()

    exact = [e for e in glossary if q in _names(e)]
    # Exclude short names so aliases such as "r" do not match everything
    partial = [
        e for e in glossary
        if e not in exact and any(q in n or (len(n) >= 3 and n in q) for n in _names(e))
    ]
    in_definition = [
        e for e in glossary
        if e not in exact and e not in partial and q in _normalize(e["definition"])
    ]
    hits = (exact + partial + in_definition)[:MAX_RESULTS]

    if not hits:
        return f"The term '{query}' was not found in the glossary."
    return json.dumps(
        [
            {
                "term": e["term"],
                "lecture": e["lecture"],
                "definition": e["definition"],
                "related": e["related"],
            }
            for e in hits
        ],
        ensure_ascii=False,
    )


def get_lecture_summary(lecture: int) -> str:
    """Return key points from the specified session (an integer starting at 1).

    Use when asked about session content or relationships, such as "What will we learn in Lecture 03?".
    """
    path = DATA_DIR / "lectures" / f"{lecture:02d}.md"
    if not path.exists():
        available = sorted(p.stem for p in (DATA_DIR / "lectures").glob("*.md"))
        return f"Key points for Lecture {lecture:02d} are not available yet. Available sessions: {', '.join(available)}"
    return path.read_text(encoding="utf-8")


def make_quiz(lecture: int) -> str:
    """Generate a review question from the glossary for the specified lecture session (an integer starting at 1).

    Use when asked for a review question, quiz, or check question about a specific lecture (for example, "Give me one review question from Lecture 02").
    """
    glossary = load_glossary()
    terms = [e for e in glossary if e.get("lecture") == lecture]
    if not terms:
        available = sorted(set(e["lecture"] for e in glossary if "lecture" in e))
        available_str = ", ".join(f"{l:02d}" for l in available)
        return f"No terms found for Lecture {lecture:02d}. Available sessions: {available_str}"
    chosen = random.choice(terms)
    return json.dumps(
        {
            "question": f"What does {chosen['term']} mean?",
            "answer": chosen["definition"],
            "term": chosen["term"],
            "lecture": chosen["lecture"],
        },
        ensure_ascii=False,
    )


def save_learning_log(
    topic: str,
    what_learned: str,
    key_points: list[str] | str,
    reflection: str = "",
    filename: str | None = None,
) -> str:
    """Save a learning record to the learning_log/ directory.

    Requires user confirmation before execution because writing a file cannot be easily undone.
    Use when the user explicitly asks to save, record, or log their learning notes, summary, or review.

    Args:
        topic: The title or main subject studied (e.g. "LoRA and PEFT").
        what_learned: Summary of what was learned or understood during the session.
        key_points: Key concepts, takeaways, or bullet points (list of strings or text).
        reflection: Optional personal reflection, next steps, or open questions.
        filename: Optional custom filename within learning_log/ (prevents path traversal).
    """
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    if filename:
        target_path = (LOG_DIR / filename).resolve()
        try:
            target_path.relative_to(LOG_DIR.resolve())
        except ValueError:
            return "Error: Path traversal detected. Learning logs must be saved within the learning_log/ directory."
    else:
        safe_topic = re.sub(r"[^\w\s-]", "", topic).strip()
        safe_topic = re.sub(r"[-\s]+", "_", safe_topic).lower()[:40] or "record"
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        target_path = LOG_DIR / f"{timestamp}_{safe_topic}.md"

    # Avoid silently overwriting existing files
    if target_path.exists():
        stem = target_path.stem
        suffix = target_path.suffix or ".md"
        counter = 1
        while target_path.exists():
            target_path = target_path.parent / f"{stem}_{counter}{suffix}"
            counter += 1

    # Format key points
    if isinstance(key_points, list):
        kp_text = "\n".join(f"- {kp}" for kp in key_points)
    else:
        kp_text = str(key_points).strip()
        if not kp_text.startswith("-") and not kp_text.startswith("*"):
            kp_text = "\n".join(f"- {line.strip()}" for line in kp_text.splitlines() if line.strip())

    reflection_section = f"\n## Reflection\n{reflection.strip()}\n" if reflection.strip() else ""

    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    content = f"""# Learning Log: {topic}

- **Date**: {date_str}
- **Topic**: {topic}

## What I Learned
{what_learned.strip()}

## Key Points
{kp_text}
{reflection_section}"""

    try:
        target_path.write_text(content, encoding="utf-8")
        rel_path = target_path.relative_to(LOG_DIR.parent)
        return f"Successfully saved learning log to {rel_path}."
    except Exception as e:
        return f"Failed to save learning log: {e}"
