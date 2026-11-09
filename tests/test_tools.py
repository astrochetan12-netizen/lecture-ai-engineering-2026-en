"""Tool tests (no LLM or API key used)."""

import json
from pathlib import Path

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


def test_make_quiz_valid_lecture():
    res = tools.make_quiz(2)
    data = json.loads(res)
    assert "question" in data
    assert "answer" in data
    assert data["lecture"] == 2


def test_make_quiz_invalid_lecture():
    res = tools.make_quiz(0)
    assert "No terms found for Lecture 00" in res


def test_save_learning_log_creates_directory_and_file(tmp_path, monkeypatch):
    log_dir = tmp_path / "learning_log"
    monkeypatch.setattr(tools, "LOG_DIR", log_dir)

    result_msg = tools.save_learning_log(
        topic="LoRA Parameter Efficient Fine-Tuning",
        what_learned="Decomposes weight updates into low-rank matrices A and B.",
        key_points=["Freezes pretrained weights", "Reduces trainable parameters drastically"],
        reflection="Next step: study quantization with QLoRA.",
    )
    assert "Successfully saved" in result_msg
    assert log_dir.exists()

    files = list(log_dir.glob("*.md"))
    assert len(files) == 1
    content = files[0].read_text(encoding="utf-8")
    assert "LoRA Parameter Efficient Fine-Tuning" in content
    assert "Decomposes weight updates" in content
    assert "Freezes pretrained weights" in content
    assert "Next step: study quantization with QLoRA." in content


def test_save_learning_log_prevents_silent_overwrite(tmp_path, monkeypatch):
    log_dir = tmp_path / "learning_log"
    monkeypatch.setattr(tools, "LOG_DIR", log_dir)

    tools.save_learning_log("Topic 1", "Learned 1", ["Point 1"], filename="log.md")
    tools.save_learning_log("Topic 2", "Learned 2", ["Point 2"], filename="log.md")

    assert (log_dir / "log.md").exists()
    assert (log_dir / "log_1.md").exists()
    assert "Topic 1" in (log_dir / "log.md").read_text(encoding="utf-8")
    assert "Topic 2" in (log_dir / "log_1.md").read_text(encoding="utf-8")


def test_save_learning_log_prevents_path_traversal(tmp_path, monkeypatch):
    log_dir = tmp_path / "learning_log"
    monkeypatch.setattr(tools, "LOG_DIR", log_dir)

    res = tools.save_learning_log("Evil", "Malicious", ["Exploit"], filename="../../evil.txt")
    assert "Path traversal detected" in res
    assert not (tmp_path / "evil.txt").exists()
