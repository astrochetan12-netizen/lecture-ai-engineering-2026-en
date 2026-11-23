"""Tool tests (no LLM or API key used)."""

import json

from app import tools


def test_glossary_ids_are_unique_and_related_links_exist():
    terms = tools.load_glossary()
    ids = [t["id"] for t in terms]
    assert len(ids) == len(set(ids))
    for t in terms:
        for r in t["related"]:
            assert r in ids, f"{t['id']} has a nonexistent id in related: {r}"


def test_search_finds_term_by_name_and_alias():
    for query in ["LoRA", "lora", "Low-Rank Adaptation"]:
        hits = json.loads(tools.search_glossary(query))
        assert hits[0]["term"] == "LoRA", query


def test_search_finds_course_specific_term():
    hits = json.loads(tools.search_glossary("lecNN-start"))
    assert hits[0]["term"] == "lecNN-start tag"


def test_search_limits_number_of_results():
    hits = json.loads(tools.search_glossary("agent"))
    assert 1 <= len(hits) <= tools.MAX_RESULTS


def test_search_reports_not_found():
    assert "was not found" in tools.search_glossary("nonexistent-term-xyz")


def test_lecture_summary():
    assert "agent" in tools.get_lecture_summary(3)
    assert "not available yet" in tools.get_lecture_summary(99)


def test_default_question_of_lecture1_is_answerable_from_glossary():
    """The Lecture 03 agent can correctly answer the Lecture 01 default question (app.ask) using the glossary."""
    from app.ask import DEFAULT_QUESTION

    assert "3 homework levels" in DEFAULT_QUESTION
    hits = json.loads(tools.search_glossary("3 homework levels"))
    assert hits[0]["term"] == "3 homework levels"


# ------------------------------------------------------------------
# Lecture 05 Advanced: make_quiz
# ------------------------------------------------------------------


def test_make_quiz_returns_valid_json():
    result = tools.make_quiz("MCP")
    parsed = json.loads(result)
    assert "question" in parsed and "choices" in parsed and "answer" in parsed


def test_make_quiz_nonexistent_term():
    result = tools.make_quiz("does-not-exist-xyz")
    assert "not found" in result


def test_make_quiz_bad_num_choices():
    for bad in [1, 7]:
        result = tools.make_quiz("LoRA", num_choices=bad)
        assert "must be between" in result


# ------------------------------------------------------------------
# Lecture 05 Advanced: search_related
# ------------------------------------------------------------------


def test_search_related_returns_connected_terms():
    result = tools.search_related("LoRA", hops=1)
    parsed = json.loads(result)
    assert len(parsed) >= 1


def test_search_related_no_duplicates():
    result = tools.search_related("agent", hops=2)
    parsed = json.loads(result)
    terms = [r["term"] for r in parsed]
    assert len(terms) == len(set(terms))


def test_search_related_missing_term():
    result = tools.search_related("xyz-not-real")
    assert "not found" in result


def test_search_related_invalid_hops():
    for bad in [0, 4]:
        result = tools.search_related("LoRA", hops=bad)
        assert "must be between" in result

