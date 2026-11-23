"""Lecture 03 / 05: tools for the agent.

Function docstrings and type hints here become the "tool descriptions" presented to the model.
Rewriting descriptions changes whether the model uses a tool and which arguments it supplies.

Lecture 05 Advanced additions:
- make_quiz: generate a multiple-choice quiz question from a glossary term.
- search_related: follow glossary relationship links to find connected concepts.
"""

import json
import random
from functools import cache
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
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


def make_quiz(term: str, num_choices: int = 4) -> str:
    """Generate a multiple-choice quiz question for a glossary term.

    Creates one question with distractors drawn from other glossary entries.
    Use when the learner wants to self-test on a specific concept.
    num_choices must be between 2 and 6.
    """
    if num_choices < 2 or num_choices > 6:
        return "num_choices must be between 2 and 6."

    glossary = load_glossary()
    q_norm = _normalize(term)
    matches = [e for e in glossary if q_norm in _names(e)]
    if not matches:
        return f"The term '{term}' was not found in the glossary. Cannot generate a quiz."

    target = matches[0]
    # Distractors: other entries in the same lecture or any other lecture
    pool = [e for e in glossary if e["id"] != target["id"]]
    num_distractors = min(num_choices - 1, len(pool))
    distractors = random.sample(pool, num_distractors)

    choices = [{"label": "A", "text": target["definition"], "correct": True}]
    labels = ["B", "C", "D", "E", "F"]
    for i, d in enumerate(distractors):
        choices.append({"label": labels[i], "text": d["definition"], "correct": False})

    random.shuffle(choices)
    for i, c in enumerate(choices):
        c["label"] = chr(ord("A") + i)

    correct_label = next(c["label"] for c in choices if c["correct"])

    return json.dumps(
        {
            "question": f"Which of the following best describes '{target['term']}'?",
            "choices": [{"label": c["label"], "text": c["text"]} for c in choices],
            "answer": correct_label,
            "explanation": f"See Lecture {target['lecture']}: {target['definition']}",
        },
        ensure_ascii=False,
        indent=2,
    )


def search_related(term: str, hops: int = 1) -> str:
    """Follow 'related' links in the glossary to find concepts connected to the given term.

    Use when asked about relationships between concepts or when a single glossary entry
    is not enough — this walks the relationship graph up to `hops` steps (1–3).
    Returns each discovered term with its definition and lecture number.
    """
    if hops < 1 or hops > 3:
        return "hops must be between 1 and 3."

    glossary = load_glossary()
    index = {e["id"]: e for e in glossary}

    q_norm = _normalize(term)
    seeds = [e for e in glossary if q_norm in _names(e)]
    if not seeds:
        return f"The term '{term}' was not found in the glossary."

    visited: dict[str, dict] = {}
    frontier = {seeds[0]["id"]}

    for _ in range(hops):
        next_frontier: set[str] = set()
        for node_id in frontier:
            if node_id in visited or node_id not in index:
                continue
            entry = index[node_id]
            visited[node_id] = entry
            for related_id in entry.get("related", []):
                if related_id not in visited:
                    next_frontier.add(related_id)
        frontier = next_frontier

    results = [
        {
            "term": e["term"],
            "lecture": e["lecture"],
            "definition": e["definition"],
            "distance_hops": "seed" if e["id"] == seeds[0]["id"] else "related",
        }
        for e in visited.values()
    ]
    if not results:
        return f"No related terms found for '{term}'."
    return json.dumps(results, ensure_ascii=False, indent=2)
