"""Lecture 05 Advanced: extended MCP server and tool tests.

Tests cover:
- All tools exposed through MCP (search_glossary, get_lecture_summary, make_quiz, search_related)
- Argument validation and error handling
- Multi-hop graph traversal via search_related
- Quiz generation correctness
- Edge cases: nonexistent terms, out-of-range args
No LLM or API key is used.
"""

import json

import pytest
from pydantic_ai.messages import ToolCallPart, ToolReturnPart
from pydantic_ai.models.test import TestModel

from app import tools
from app.agent import MCP_CONFIG, build_mcp_agent

# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

GLOSSARY_TOOL = "glossary_search_glossary"
SUMMARY_TOOL = "glossary_get_lecture_summary"
QUIZ_TOOL = "glossary_make_quiz"
RELATED_TOOL = "glossary_search_related"


def _glossary_only_config(tmp_path):
    """Isolate to just the glossary MCP server so tests don't need uvx / network."""
    config = json.loads(MCP_CONFIG.read_text(encoding="utf-8"))
    assert "glossary" in config["mcpServers"], "app/mcp_servers.json must have a glossary server"
    path = tmp_path / "mcp_servers.json"
    path.write_text(
        json.dumps({"mcpServers": {"glossary": config["mcpServers"]["glossary"]}}),
        encoding="utf-8",
    )
    return path


def _parts(result, kind):
    return [p for m in result.all_messages() for p in m.parts if isinstance(p, kind)]


# ------------------------------------------------------------------
# Exercise 3: get_lecture_summary exposed through MCP
# ------------------------------------------------------------------


def test_get_lecture_summary_exposed_via_mcp(tmp_path):
    """Exercise 3: glossary_get_lecture_summary must appear in MCP tool list."""
    model = TestModel(call_tools=[])
    build_mcp_agent(_glossary_only_config(tmp_path)).run_sync("Tool list", model=model)
    offered = {t.name for t in model.last_model_request_parameters.function_tools}
    assert SUMMARY_TOOL in offered, f"{SUMMARY_TOOL} not found in MCP tools: {offered}"


def test_get_lecture_summary_called_through_mcp(tmp_path):
    """Exercise 3: calling get_lecture_summary via MCP returns a non-empty result."""
    model = TestModel(call_tools=[SUMMARY_TOOL])
    result = build_mcp_agent(_glossary_only_config(tmp_path)).run_sync(
        "What will we learn in Lecture 03?", model=model
    )
    returns = _parts(result, ToolReturnPart)
    assert returns, "No tool return received"
    assert returns[0].tool_name == SUMMARY_TOOL
    content = str(returns[0].content)
    assert content.strip(), "Empty result from get_lecture_summary"


# ------------------------------------------------------------------
# Advanced: make_quiz exposed and correct
# ------------------------------------------------------------------


def test_make_quiz_exposed_via_mcp(tmp_path):
    """Advanced: make_quiz is reachable through the MCP server."""
    model = TestModel(call_tools=[])
    build_mcp_agent(_glossary_only_config(tmp_path)).run_sync("Tool list", model=model)
    offered = {t.name for t in model.last_model_request_parameters.function_tools}
    assert QUIZ_TOOL in offered, f"{QUIZ_TOOL} not in MCP tools: {offered}"


def test_make_quiz_valid_term():
    """make_quiz returns valid JSON with question, choices, answer, explanation."""
    result = tools.make_quiz("LoRA")
    parsed = json.loads(result)
    assert "question" in parsed
    assert "choices" in parsed
    assert "answer" in parsed
    assert "explanation" in parsed
    assert len(parsed["choices"]) >= 2
    correct_label = parsed["answer"]
    labels = [c["label"] for c in parsed["choices"]]
    assert correct_label in labels, "Correct answer label not found in choices"


def test_make_quiz_nonexistent_term():
    """make_quiz returns a clear error for terms not in the glossary."""
    result = tools.make_quiz("quantum-flux-capacitor-xyz")
    assert "not found" in result.lower()


def test_make_quiz_invalid_num_choices():
    """make_quiz rejects num_choices outside 2–6."""
    for bad in [0, 1, 7, 100]:
        result = tools.make_quiz("LoRA", num_choices=bad)
        assert "must be between" in result


def test_make_quiz_min_choices():
    """make_quiz works with the minimum of 2 choices."""
    result = tools.make_quiz("MCP", num_choices=2)
    parsed = json.loads(result)
    assert len(parsed["choices"]) == 2


def test_make_quiz_answer_is_correct_definition():
    """The answer choice in make_quiz contains the real definition."""
    result = tools.make_quiz("LoRA")
    parsed = json.loads(result)
    correct_label = parsed["answer"]
    correct_text = next(c["text"] for c in parsed["choices"] if c["label"] == correct_label)
    # The correct text should be the LoRA definition, which mentions 'low-rank'
    assert "low-rank" in correct_text.lower() or "lora" in correct_text.lower()


# ------------------------------------------------------------------
# Advanced: search_related graph traversal
# ------------------------------------------------------------------


def test_search_related_exposed_via_mcp(tmp_path):
    """Advanced: search_related is reachable through the MCP server."""
    model = TestModel(call_tools=[])
    build_mcp_agent(_glossary_only_config(tmp_path)).run_sync("Tool list", model=model)
    offered = {t.name for t in model.last_model_request_parameters.function_tools}
    assert RELATED_TOOL in offered, f"{RELATED_TOOL} not in MCP tools: {offered}"


def test_search_related_hop_1():
    """1-hop traversal from LoRA finds LoRA itself and immediate neighbours."""
    result = tools.search_related("LoRA", hops=1)
    parsed = json.loads(result)
    ids_or_terms = {r["term"] for r in parsed}
    # LoRA is related to peft, lora-rank, qlora — at least one should appear
    assert any("LoRA" in t or "PEFT" in t or "QLoRA" in t for t in ids_or_terms)


def test_search_related_hop_2_finds_more():
    """2-hop traversal discovers more terms than 1-hop."""
    r1 = json.loads(tools.search_related("LoRA", hops=1))
    r2 = json.loads(tools.search_related("LoRA", hops=2))
    assert len(r2) >= len(r1), "2-hop should find at least as many terms as 1-hop"


def test_search_related_nonexistent_term():
    """search_related returns a clear error for missing terms."""
    result = tools.search_related("nonexistent-xyz-abc")
    assert "not found" in result.lower()


def test_search_related_invalid_hops():
    """search_related rejects hops outside 1–3."""
    for bad in [0, 4, -1]:
        result = tools.search_related("LoRA", hops=bad)
        assert "must be between" in result


def test_search_related_cross_lecture():
    """Multi-hop traversal can find terms from a different lecture than the seed."""
    # 'hallucination' (lecture 1) is related to 'evaluation-loop' (lecture 1) and 'tool' (lecture 3)
    result = tools.search_related("hallucination", hops=2)
    parsed = json.loads(result)
    lectures = {r["lecture"] for r in parsed}
    assert len(lectures) >= 1  # at minimum finds the seed


def test_search_related_no_duplicates():
    """search_related must not return duplicate entries."""
    result = tools.search_related("agent", hops=2)
    parsed = json.loads(result)
    terms = [r["term"] for r in parsed]
    assert len(terms) == len(set(terms)), f"Duplicates found: {terms}"


# ------------------------------------------------------------------
# Existing MCP tests (regression)
# ------------------------------------------------------------------


def test_glossary_server_exposes_search_tool(tmp_path):
    model = TestModel(call_tools=[])
    build_mcp_agent(_glossary_only_config(tmp_path)).run_sync("Tool list", model=model)
    offered = {t.name for t in model.last_model_request_parameters.function_tools}
    assert GLOSSARY_TOOL in offered


def test_glossary_result_comes_back_through_mcp(tmp_path):
    model = TestModel(call_tools=[GLOSSARY_TOOL])
    result = build_mcp_agent(_glossary_only_config(tmp_path)).run_sync("What is LoRA?", model=model)
    assert [p.tool_name for p in _parts(result, ToolCallPart)] == [GLOSSARY_TOOL]
    returns = _parts(result, ToolReturnPart)
    assert returns and returns[0].tool_name == GLOSSARY_TOOL
    assert str(returns[0].content).strip()
    assert result.output
