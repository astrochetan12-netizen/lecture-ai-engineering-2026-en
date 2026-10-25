"""Tests for app.ask (no external API calls or GEMINI_API_KEY required)."""

import copy
from unittest.mock import MagicMock

from app.ask import ask, chat_turn


class FakeUsageMetadata:
    def __init__(self, prompt_tokens: int = 12, candidates_tokens: int = 8):
        self.prompt_token_count = prompt_tokens
        self.candidates_token_count = candidates_tokens


class FakeResponse:
    def __init__(self, text: str, in_tokens: int = 12, out_tokens: int = 8):
        self.text = text
        self.usage_metadata = FakeUsageMetadata(in_tokens, out_tokens)


class FakeGenAIClient:
    """Mock client that records model and contents passed to generate_content."""

    def __init__(self, responses: list[str] | None = None):
        self.calls: list[dict] = []
        self._responses = list(responses or ["Mock answer 1", "Mock answer 2"])
        self.models = MagicMock()
        self.models.generate_content.side_effect = self._generate_content

    def _generate_content(self, model: str, contents: list | str):
        self.calls.append({"model": model, "contents": copy.deepcopy(contents)})
        text = self._responses.pop(0) if self._responses else "Default answer"
        return FakeResponse(text)


def test_ask_single_turn_calls_model():
    client = FakeGenAIClient(["LoRA is Low-Rank Adaptation."])
    result = ask("What is LoRA?", client=client)

    assert result == "LoRA is Low-Rank Adaptation."
    assert len(client.calls) == 1
    assert client.calls[0]["contents"] == "What is LoRA?"


def test_chat_turn_preserves_conversation_history():
    client = FakeGenAIClient(
        [
            "I will remember your favorite fruit is mango.",
            "Your favorite fruit is mango!",
        ]
    )
    history: list[dict] = []

    # Turn 1
    reply1 = chat_turn(history, "My favorite fruit is mango.", client=client)
    assert reply1 == "I will remember your favorite fruit is mango."
    assert len(history) == 2
    assert history[0]["role"] == "user"
    assert history[0]["parts"][0]["text"] == "My favorite fruit is mango."
    assert history[1]["role"] == "model"
    assert history[1]["parts"][0]["text"] == "I will remember your favorite fruit is mango."

    # Turn 2: Follow-up question
    reply2 = chat_turn(history, "What is my favorite fruit?", client=client)
    assert reply2 == "Your favorite fruit is mango!"
    assert len(client.calls) == 2

    # Verify that the second call received the full history from turn 1 plus the new turn 2 prompt
    second_call_contents = client.calls[1]["contents"]
    assert len(second_call_contents) == 3
    assert second_call_contents[0]["role"] == "user"
    assert second_call_contents[0]["parts"][0]["text"] == "My favorite fruit is mango."
    assert second_call_contents[1]["role"] == "model"
    assert second_call_contents[1]["parts"][0]["text"] == "I will remember your favorite fruit is mango."
    assert second_call_contents[2]["role"] == "user"
    assert second_call_contents[2]["parts"][0]["text"] == "What is my favorite fruit?"
