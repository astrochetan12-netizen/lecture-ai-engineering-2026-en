"""Agent wiring tests.

TestModel is a fake model that calls all registered tools and returns a dummy answer
without calling a real LLM. Check that tools are registered, called, and return results
to the model, without using an API key or consuming usage allowances.
"""

from pydantic_ai import DeferredToolRequests
from pydantic_ai.messages import ToolCallPart, ToolReturnPart
from pydantic_ai.models.test import TestModel

from app import tools
from app.agent import agent

BASE_TOOLS = {"search_glossary", "get_lecture_summary"}


def _parts(result, kind):
    return [p for m in result.all_messages() for p in m.parts if isinstance(p, kind)]


def test_base_tools_are_registered_and_called():
    model = TestModel()
    with agent.override(model=model):
        result = agent.run_sync("What is LoRA?")

    offered = {t.name for t in model.last_model_request_parameters.function_tools}
    assert BASE_TOOLS <= offered  # Check inclusion so adding tools in the exercises does not break the test

    called = {p.tool_name for p in _parts(result, ToolCallPart)}
    assert BASE_TOOLS <= called
    # Tools requiring approval (requires_approval=True) wait without executing and therefore have no return value
    waiting = len(result.output.approvals) if isinstance(result.output, DeferredToolRequests) else 0
    assert len(_parts(result, ToolReturnPart)) + waiting == len(_parts(result, ToolCallPart))
    assert result.output


def test_glossary_result_reaches_the_model():
    model = TestModel(call_tools=["search_glossary"])
    with agent.override(model=model):
        result = agent.run_sync("What is RAG?")
    returns = _parts(result, ToolReturnPart)
    assert returns and returns[0].tool_name == "search_glossary"


def test_agent_save_learning_log_requires_approval():
    model = TestModel(call_tools=["save_learning_log"])
    with agent.override(model=model):
        result = agent.run_sync("Please save what I learned about LoRA today.")

    assert isinstance(result.output, DeferredToolRequests)
    assert len(result.output.approvals) == 1
    call = result.output.approvals[0]
    assert call.tool_name == "save_learning_log"


def test_agent_save_learning_log_approved_flow(tmp_path, monkeypatch):
    log_dir = tmp_path / "learning_log"
    monkeypatch.setattr(tools, "LOG_DIR", log_dir)

    model = TestModel(call_tools=["save_learning_log"])
    with agent.override(model=model):
        initial = agent.run_sync("Record my learning notes.")
        assert isinstance(initial.output, DeferredToolRequests)
        call = initial.output.approvals[0]

        # User approves the deferred tool execution
        deferred_results = initial.output.build_results(approvals={call.tool_call_id: True})
        final_result = agent.run_sync(
            message_history=initial.all_messages(),
            deferred_tool_results=deferred_results,
            model=model,
        )

    # Verify tool execution occurred after approval
    returns = _parts(final_result, ToolReturnPart)
    save_returns = [r for r in returns if r.tool_name == "save_learning_log"]
    assert len(save_returns) == 1
    assert "Successfully saved" in str(save_returns[0].content)
    assert log_dir.exists()
    assert len(list(log_dir.glob("*.md"))) == 1


def test_agent_save_learning_log_denied_flow(tmp_path, monkeypatch):
    log_dir = tmp_path / "learning_log"
    monkeypatch.setattr(tools, "LOG_DIR", log_dir)

    model = TestModel(call_tools=["save_learning_log"])
    with agent.override(model=model):
        initial = agent.run_sync("Record my learning notes.")
        assert isinstance(initial.output, DeferredToolRequests)
        call = initial.output.approvals[0]

        # User denies the deferred tool execution
        deferred_results = initial.output.build_results(approvals={call.tool_call_id: False})
        final_result = agent.run_sync(
            message_history=initial.all_messages(),
            deferred_tool_results=deferred_results,
            model=model,
        )

    # Verify tool was denied and not executed
    returns = _parts(final_result, ToolReturnPart)
    save_returns = [r for r in returns if r.tool_name == "save_learning_log"]
    assert len(save_returns) == 1
    assert save_returns[0].outcome == "denied"
    assert "denied" in str(save_returns[0].content).lower()
    # Directory should either not exist or have no markdown files saved
    if log_dir.exists():
        assert len(list(log_dir.glob("*.md"))) == 0
