"""
Unit tests for the state management in src/open_canvas/state.py

Tests cover:
- _is_summary_message detection
- _messages_reducer custom reducer behavior
- Summary message clearing history
"""

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from src.constants import OC_SUMMARIZED_MESSAGE_KEY


# ============================================
# Tests for _is_summary_message()
# ============================================


@pytest.mark.unit
class TestIsSummaryMessage:
    """Tests for summary message detection."""

    def test_detect_summary_message_with_additional_kwargs(self):
        """Should detect summary message via additional_kwargs."""
        from src.open_canvas.state import _is_summary_message

        msg = AIMessage(
            content="Summary of conversation...",
            additional_kwargs={OC_SUMMARIZED_MESSAGE_KEY: True},
        )

        assert _is_summary_message(msg) is True

    def test_detect_summary_message_dict_format(self):
        """Should detect summary message in dict format."""
        from src.open_canvas.state import _is_summary_message

        msg = {
            "content": "Summary...",
            "additional_kwargs": {OC_SUMMARIZED_MESSAGE_KEY: True},
        }

        assert _is_summary_message(msg) is True

    def test_non_summary_message(self):
        """Should return False for regular messages."""
        from src.open_canvas.state import _is_summary_message

        msg = AIMessage(content="Regular response")

        assert _is_summary_message(msg) is False

    def test_non_summary_message_with_other_kwargs(self):
        """Should return False for messages with other additional_kwargs."""
        from src.open_canvas.state import _is_summary_message

        msg = AIMessage(
            content="Response",
            additional_kwargs={"some_other_key": True},
        )

        assert _is_summary_message(msg) is False

    def test_summary_message_false_value(self):
        """Should return False when summary key is False."""
        from src.open_canvas.state import _is_summary_message

        msg = AIMessage(
            content="Not a summary",
            additional_kwargs={OC_SUMMARIZED_MESSAGE_KEY: False},
        )

        assert _is_summary_message(msg) is False

    def test_non_message_object(self):
        """Should return False for non-message objects."""
        from src.open_canvas.state import _is_summary_message

        assert _is_summary_message("just a string") is False
        assert _is_summary_message(123) is False
        assert _is_summary_message(None) is False

    def test_empty_dict(self):
        """Should return False for empty dict."""
        from src.open_canvas.state import _is_summary_message

        assert _is_summary_message({}) is False

    def test_nested_kwargs_format(self):
        """Should detect summary message with nested kwargs format."""
        from src.open_canvas.state import _is_summary_message

        # Some serialization formats use kwargs.additional_kwargs
        msg = {
            "kwargs": {"additional_kwargs": {OC_SUMMARIZED_MESSAGE_KEY: True}},
        }

        assert _is_summary_message(msg) is True


# ============================================
# Tests for _messages_reducer()
# ============================================


@pytest.mark.unit
class TestMessagesReducer:
    """Tests for the custom messages reducer."""

    def test_normal_message_append(self):
        """Normal messages should be appended to existing list."""
        from src.open_canvas.state import _messages_reducer

        existing = [HumanMessage(content="Hello")]
        new = AIMessage(content="Hi there!")

        result = _messages_reducer(existing, new)

        assert len(result) == 2
        assert result[0].content == "Hello"
        assert result[1].content == "Hi there!"

    def test_append_list_of_messages(self):
        """List of messages should be appended."""
        from src.open_canvas.state import _messages_reducer

        existing = [HumanMessage(content="Hello")]
        new = [
            AIMessage(content="Hi!"),
            HumanMessage(content="How are you?"),
        ]

        result = _messages_reducer(existing, new)

        assert len(result) == 3

    def test_summary_message_clears_history(self):
        """Summary message should clear existing history."""
        from src.open_canvas.state import _messages_reducer

        # Existing conversation history
        existing = [
            HumanMessage(content="First message"),
            AIMessage(content="First response"),
            HumanMessage(content="Second message"),
            AIMessage(content="Second response"),
        ]

        # New summary message
        summary_msg = AIMessage(
            content="Summary: User discussed topics A and B.",
            additional_kwargs={OC_SUMMARIZED_MESSAGE_KEY: True},
        )

        result = _messages_reducer(existing, summary_msg)

        # History should be cleared, only summary remains
        assert len(result) == 1
        assert result[0].content == "Summary: User discussed topics A and B."
        assert result[0].additional_kwargs.get(OC_SUMMARIZED_MESSAGE_KEY) is True

    def test_summary_message_in_list(self):
        """Summary message at end of list should clear history."""
        from src.open_canvas.state import _messages_reducer

        existing = [HumanMessage(content="Old message")]

        new_messages = [
            HumanMessage(content="New question"),
            AIMessage(
                content="Summary...",
                additional_kwargs={OC_SUMMARIZED_MESSAGE_KEY: True},
            ),
        ]

        result = _messages_reducer(existing, new_messages)

        # Only the new messages should remain
        assert len(result) == 2
        assert result[0].content == "New question"
        assert result[1].content == "Summary..."

    def test_empty_new_messages(self):
        """Empty new messages should not modify existing."""
        from src.open_canvas.state import _messages_reducer

        existing = [HumanMessage(content="Hello")]
        new = []

        result = _messages_reducer(existing, new)

        assert len(result) == 1
        assert result[0].content == "Hello"

    def test_empty_existing_messages(self):
        """Should handle empty existing messages list."""
        from src.open_canvas.state import _messages_reducer

        existing = []
        new = HumanMessage(content="First message")

        result = _messages_reducer(existing, new)

        assert len(result) == 1
        assert result[0].content == "First message"

    def test_non_summary_last_message(self):
        """Non-summary last message should append normally."""
        from src.open_canvas.state import _messages_reducer

        existing = [HumanMessage(content="Hello")]
        new = [
            AIMessage(
                content="Summary...",
                additional_kwargs={OC_SUMMARIZED_MESSAGE_KEY: True},
            ),
            HumanMessage(content="New question after summary"),
        ]

        # The last message is NOT a summary, so normal append
        result = _messages_reducer(existing, new)

        # Both should be appended (since last message is not summary)
        assert len(result) == 3


# ============================================
# Tests for OpenCanvasState structure
# ============================================


@pytest.mark.unit
class TestOpenCanvasStateStructure:
    """Tests for OpenCanvasState TypedDict structure."""

    def test_state_has_required_fields(self):
        """State should have all required camelCase fields."""
        from src.open_canvas.state import OpenCanvasState

        # Check annotations exist for expected fields
        annotations = OpenCanvasState.__annotations__

        assert "messages" in annotations
        assert "_messages" in annotations
        assert "highlightedCode" in annotations
        assert "highlightedText" in annotations
        assert "artifact" in annotations
        assert "next" in annotations
        assert "language" in annotations
        assert "artifactLength" in annotations
        assert "regenerateWithEmojis" in annotations
        assert "readingLevel" in annotations
        assert "addComments" in annotations
        assert "addLogs" in annotations
        assert "portLanguage" in annotations
        assert "fixBugs" in annotations
        assert "customQuickActionId" in annotations
        assert "webSearchEnabled" in annotations
        assert "webSearchResults" in annotations

    def test_state_uses_camel_case(self):
        """All field names should use camelCase (no snake_case)."""
        from src.open_canvas.state import OpenCanvasState

        annotations = OpenCanvasState.__annotations__

        for field_name in annotations:
            # Skip private fields starting with _
            if field_name.startswith("_"):
                continue
            # Check no underscores in middle of name (snake_case indicator)
            assert "_" not in field_name, f"Field {field_name} uses snake_case"
