"""
Unit tests for the rewrite_artifact node.

This node is responsible for rewriting existing artifacts based on user requests.

Tests cover:
- Function and class existence
- Helper function behavior
- Artifact type detection
- Prompt building
- Full node execution with mock LLM
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from langchain_core.messages import HumanMessage, AIMessage


@pytest.mark.unit
class TestRewriteArtifact:
    """Tests for the rewrite_artifact node."""

    def test_rewrite_artifact_function_exists(self):
        """rewrite_artifact function should exist and be callable."""
        from src.open_canvas.nodes.rewrite_artifact import rewrite_artifact

        assert callable(rewrite_artifact)

    def test_get_model_config_function_exists(self):
        """get_model_config function should be imported."""
        from src.open_canvas.nodes.rewrite_artifact import get_model_config

        assert callable(get_model_config)

    def test_get_model_from_config_function_exists(self):
        """get_model_from_config function should be imported."""
        from src.open_canvas.nodes.rewrite_artifact import get_model_from_config

        assert callable(get_model_from_config)

    def test_update_artifact_meta_tool_class_exists(self):
        """UpdateArtifactMetaTool class should exist."""
        from src.open_canvas.nodes.rewrite_artifact import UpdateArtifactMetaTool

        assert UpdateArtifactMetaTool is not None


@pytest.mark.unit
class TestRewriteArtifactHelpers:
    """Tests for rewrite_artifact helper functions."""

    def test_optionally_update_artifact_meta_exists(self):
        """_optionally_update_artifact_meta helper should exist."""
        from src.open_canvas.nodes.rewrite_artifact import (
            _optionally_update_artifact_meta,
        )

        assert callable(_optionally_update_artifact_meta)

    def test_get_artifact_content_exists(self):
        """_get_artifact_content helper should exist."""
        from src.open_canvas.nodes.rewrite_artifact import _get_artifact_content

        assert callable(_get_artifact_content)

    def test_is_markdown_artifact_exists(self):
        """_is_markdown_artifact helper should exist."""
        from src.open_canvas.nodes.rewrite_artifact import _is_markdown_artifact

        assert callable(_is_markdown_artifact)

    def test_is_code_artifact_exists(self):
        """_is_code_artifact helper should exist."""
        from src.open_canvas.nodes.rewrite_artifact import _is_code_artifact

        assert callable(_is_code_artifact)

    def test_build_prompt_exists(self):
        """_build_prompt helper should exist."""
        from src.open_canvas.nodes.rewrite_artifact import _build_prompt

        assert callable(_build_prompt)

    def test_create_new_artifact_content_exists(self):
        """_create_new_artifact_content helper should exist."""
        from src.open_canvas.nodes.rewrite_artifact import _create_new_artifact_content

        assert callable(_create_new_artifact_content)


@pytest.mark.unit
class TestGetArtifactContent:
    """Tests for _get_artifact_content helper."""

    def test_returns_none_for_none_artifact(self):
        """Should return None for None artifact."""
        from src.open_canvas.nodes.rewrite_artifact import _get_artifact_content

        result = _get_artifact_content(None)
        assert result is None

    def test_returns_content_at_current_index(self):
        """Should return content at currentIndex."""
        from src.open_canvas.nodes.rewrite_artifact import _get_artifact_content

        artifact = {
            "currentIndex": 2,
            "contents": [
                {"index": 1, "type": "code", "code": "v1"},
                {"index": 2, "type": "code", "code": "v2"},
            ],
        }

        result = _get_artifact_content(artifact)
        assert result["index"] == 2
        assert result["code"] == "v2"

    def test_fallback_to_last_content(self):
        """Should fallback to last content if currentIndex not found."""
        from src.open_canvas.nodes.rewrite_artifact import _get_artifact_content

        artifact = {
            "currentIndex": 99,
            "contents": [
                {"index": 1, "code": "first"},
                {"index": 2, "code": "last"},
            ],
        }

        result = _get_artifact_content(artifact)
        assert result["code"] == "last"

    def test_returns_none_for_empty_contents(self):
        """Should return None for empty contents list."""
        from src.open_canvas.nodes.rewrite_artifact import _get_artifact_content

        artifact = {"currentIndex": 1, "contents": []}
        result = _get_artifact_content(artifact)
        assert result is None


@pytest.mark.unit
class TestArtifactTypeDetection:
    """Tests for artifact type detection helpers."""

    def test_is_markdown_artifact_true(self):
        """Should return True for text type."""
        from src.open_canvas.nodes.rewrite_artifact import _is_markdown_artifact

        content = {"type": "text", "fullMarkdown": "# Hello"}
        assert _is_markdown_artifact(content) is True

    def test_is_markdown_artifact_false_for_code(self):
        """Should return False for code type."""
        from src.open_canvas.nodes.rewrite_artifact import _is_markdown_artifact

        content = {"type": "code", "code": "print('hi')"}
        assert _is_markdown_artifact(content) is False

    def test_is_markdown_artifact_false_for_none(self):
        """Should return False for None."""
        from src.open_canvas.nodes.rewrite_artifact import _is_markdown_artifact

        assert _is_markdown_artifact(None) is False

    def test_is_code_artifact_true(self):
        """Should return True for code type."""
        from src.open_canvas.nodes.rewrite_artifact import _is_code_artifact

        content = {"type": "code", "code": "x = 1"}
        assert _is_code_artifact(content) is True

    def test_is_code_artifact_false_for_text(self):
        """Should return False for text type."""
        from src.open_canvas.nodes.rewrite_artifact import _is_code_artifact

        content = {"type": "text", "fullMarkdown": "Hello"}
        assert _is_code_artifact(content) is False

    def test_is_code_artifact_false_for_none(self):
        """Should return False for None."""
        from src.open_canvas.nodes.rewrite_artifact import _is_code_artifact

        assert _is_code_artifact(None) is False


@pytest.mark.unit
class TestBuildPrompt:
    """Tests for _build_prompt helper."""

    def test_includes_artifact_content(self):
        """Should include artifact content in prompt."""
        from src.open_canvas.nodes.rewrite_artifact import _build_prompt

        artifact_content = "def hello(): pass"
        result = _build_prompt(
            artifact_content=artifact_content,
            memories_as_string="",
            is_new_type=False,
            artifact_meta={"type": "code"},
        )

        assert artifact_content in result

    def test_includes_memories(self):
        """Should include memories/reflections in prompt."""
        from src.open_canvas.nodes.rewrite_artifact import _build_prompt

        memories = "User prefers concise code."
        result = _build_prompt(
            artifact_content="code",
            memories_as_string=memories,
            is_new_type=False,
            artifact_meta={"type": "code"},
        )

        assert memories in result

    def test_includes_meta_prompt_for_new_type(self):
        """Should include meta prompt when type changes."""
        from src.open_canvas.nodes.rewrite_artifact import _build_prompt

        result = _build_prompt(
            artifact_content="content",
            memories_as_string="",
            is_new_type=True,
            artifact_meta={"type": "text", "title": "New Title"},
        )

        # Should contain type information
        assert "text" in result.lower()


@pytest.mark.unit
class TestCreateNewArtifactContent:
    """Tests for _create_new_artifact_content helper."""

    def test_creates_code_artifact(self):
        """Should create code artifact correctly."""
        from src.open_canvas.nodes.rewrite_artifact import _create_new_artifact_content

        state = {
            "artifact": {
                "currentIndex": 1,
                "contents": [{"index": 1, "type": "code", "code": "old"}],
            }
        }
        current = {"type": "code", "title": "My Code", "language": "python"}
        meta = {"type": "code", "title": "Updated Code", "language": "python"}

        result = _create_new_artifact_content(
            artifact_type="code",
            state=state,
            current_artifact_content=current,
            artifact_meta=meta,
            new_content="def new_func(): pass",
        )

        assert result["type"] == "code"
        assert result["index"] == 2
        assert result["title"] == "Updated Code"
        assert result["code"] == "def new_func(): pass"
        assert result["language"] == "python"

    def test_creates_text_artifact(self):
        """Should create text artifact correctly."""
        from src.open_canvas.nodes.rewrite_artifact import _create_new_artifact_content

        state = {
            "artifact": {
                "currentIndex": 1,
                "contents": [{"index": 1, "type": "text", "fullMarkdown": "old"}],
            }
        }
        current = {"type": "text", "title": "My Doc"}
        meta = {"type": "text", "title": "Updated Doc"}

        result = _create_new_artifact_content(
            artifact_type="text",
            state=state,
            current_artifact_content=current,
            artifact_meta=meta,
            new_content="# New Document\n\nContent here.",
        )

        assert result["type"] == "text"
        assert result["index"] == 2
        assert result["title"] == "Updated Doc"
        assert result["fullMarkdown"] == "# New Document\n\nContent here."

    def test_defaults_language_to_other(self):
        """Should default language to 'other' for code artifacts."""
        from src.open_canvas.nodes.rewrite_artifact import _create_new_artifact_content

        state = {"artifact": {"currentIndex": 1, "contents": []}}
        current = {"type": "text", "title": "Doc"}  # Converting from text
        meta = {"type": "code", "title": "Code"}  # No language specified

        result = _create_new_artifact_content(
            artifact_type="code",
            state=state,
            current_artifact_content=current,
            artifact_meta=meta,
            new_content="print('hello')",
        )

        assert result["language"] == "other"


@pytest.mark.unit
class TestUpdateArtifactMetaToolSchema:
    """Tests for UpdateArtifactMetaTool schema validation."""

    def test_valid_tool_call(self):
        """Should validate valid tool call."""
        from src.open_canvas.nodes.rewrite_artifact import UpdateArtifactMetaTool

        tool = UpdateArtifactMetaTool(
            type="code",
            title="New Title",
            language="python",
            isValidReact=False,
        )

        assert tool.type == "code"
        assert tool.title == "New Title"
        assert tool.language == "python"

    def test_optional_fields_default_to_none(self):
        """Optional fields should default to None."""
        from src.open_canvas.nodes.rewrite_artifact import UpdateArtifactMetaTool

        tool = UpdateArtifactMetaTool(type="text")

        assert tool.title is None
        assert tool.language is None
        assert tool.isValidReact is None


@pytest.mark.unit
class TestRewriteArtifactNodeWithMock:
    """Tests for rewrite_artifact node using mock LLM."""

    @pytest.mark.asyncio
    async def test_rewrites_code_artifact(self, mock_store, mock_config):
        """Should rewrite code artifact successfully."""
        from src.open_canvas.nodes.rewrite_artifact import rewrite_artifact

        # Mock meta update response
        meta_response = MagicMock()
        meta_response.tool_calls = [{"args": {"type": "code", "title": "Updated"}}]

        # Mock rewrite response
        rewrite_response = MagicMock()
        rewrite_response.content = "def new_func():\n    print('Updated!')"

        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(side_effect=[meta_response, rewrite_response])
        mock_llm.bind_tools = MagicMock(return_value=mock_llm)

        state = {
            "_messages": [HumanMessage(content="Make the function better")],
            "messages": [HumanMessage(content="Make the function better")],
            "artifact": {
                "currentIndex": 1,
                "contents": [
                    {
                        "index": 1,
                        "type": "code",
                        "title": "Original",
                        "code": "def old_func(): pass",
                        "language": "python",
                    }
                ],
            },
        }

        with patch("src.open_canvas.nodes.rewrite_artifact.get_model_from_config", return_value=mock_llm):
            with patch("src.open_canvas.nodes.rewrite_artifact.get_model_config", return_value={"modelName": "gpt-4o"}):
                with patch("src.open_canvas.nodes.rewrite_artifact.get_formatted_reflections", return_value=""):
                    with patch("src.open_canvas.nodes.rewrite_artifact.create_context_document_messages", return_value=[]):
                        with patch("src.open_canvas.nodes.rewrite_artifact.is_using_o1_mini_model", return_value=False):
                            with patch("src.open_canvas.nodes.rewrite_artifact.is_thinking_model", return_value=False):
                                with patch("src.open_canvas.nodes.rewrite_artifact.optionally_get_system_prompt_from_config", return_value=None):
                                    result = await rewrite_artifact(state, mock_config, store=mock_store)

        assert "artifact" in result
        artifact = result["artifact"]
        assert artifact["currentIndex"] == 2
        assert len(artifact["contents"]) == 2
        assert artifact["contents"][1]["type"] == "code"
        assert "new_func" in artifact["contents"][1]["code"]

    @pytest.mark.asyncio
    async def test_rewrites_text_artifact(self, mock_store, mock_config):
        """Should rewrite text artifact successfully."""
        from src.open_canvas.nodes.rewrite_artifact import rewrite_artifact

        # Mock meta update response
        meta_response = MagicMock()
        meta_response.tool_calls = [{"args": {"type": "text", "title": "Updated Essay"}}]

        # Mock rewrite response
        rewrite_response = MagicMock()
        rewrite_response.content = "# New Essay\n\nThis is the rewritten content."

        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(side_effect=[meta_response, rewrite_response])
        mock_llm.bind_tools = MagicMock(return_value=mock_llm)

        state = {
            "_messages": [HumanMessage(content="Rewrite this essay")],
            "messages": [HumanMessage(content="Rewrite this essay")],
            "artifact": {
                "currentIndex": 1,
                "contents": [
                    {
                        "index": 1,
                        "type": "text",
                        "title": "Original Essay",
                        "fullMarkdown": "# Old Essay\n\nOld content.",
                    }
                ],
            },
        }

        with patch("src.open_canvas.nodes.rewrite_artifact.get_model_from_config", return_value=mock_llm):
            with patch("src.open_canvas.nodes.rewrite_artifact.get_model_config", return_value={"modelName": "gpt-4o"}):
                with patch("src.open_canvas.nodes.rewrite_artifact.get_formatted_reflections", return_value=""):
                    with patch("src.open_canvas.nodes.rewrite_artifact.create_context_document_messages", return_value=[]):
                        with patch("src.open_canvas.nodes.rewrite_artifact.is_using_o1_mini_model", return_value=False):
                            with patch("src.open_canvas.nodes.rewrite_artifact.is_thinking_model", return_value=False):
                                with patch("src.open_canvas.nodes.rewrite_artifact.optionally_get_system_prompt_from_config", return_value=None):
                                    result = await rewrite_artifact(state, mock_config, store=mock_store)

        assert "artifact" in result
        artifact = result["artifact"]
        assert artifact["contents"][1]["type"] == "text"
        assert "New Essay" in artifact["contents"][1]["fullMarkdown"]

    @pytest.mark.asyncio
    async def test_handles_type_conversion(self, mock_store, mock_config):
        """Should handle type conversion from text to code."""
        from src.open_canvas.nodes.rewrite_artifact import rewrite_artifact

        # Mock meta update response - changing type to code
        meta_response = MagicMock()
        meta_response.tool_calls = [{"args": {"type": "code", "title": "Converted Code", "language": "python"}}]

        # Mock rewrite response
        rewrite_response = MagicMock()
        rewrite_response.content = "def converted(): pass"

        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(side_effect=[meta_response, rewrite_response])
        mock_llm.bind_tools = MagicMock(return_value=mock_llm)

        state = {
            "_messages": [HumanMessage(content="Convert this to Python code")],
            "messages": [HumanMessage(content="Convert this to Python code")],
            "artifact": {
                "currentIndex": 1,
                "contents": [
                    {
                        "index": 1,
                        "type": "text",
                        "title": "Description",
                        "fullMarkdown": "This is a description of a function.",
                    }
                ],
            },
        }

        with patch("src.open_canvas.nodes.rewrite_artifact.get_model_from_config", return_value=mock_llm):
            with patch("src.open_canvas.nodes.rewrite_artifact.get_model_config", return_value={"modelName": "gpt-4o"}):
                with patch("src.open_canvas.nodes.rewrite_artifact.get_formatted_reflections", return_value=""):
                    with patch("src.open_canvas.nodes.rewrite_artifact.create_context_document_messages", return_value=[]):
                        with patch("src.open_canvas.nodes.rewrite_artifact.is_using_o1_mini_model", return_value=False):
                            with patch("src.open_canvas.nodes.rewrite_artifact.is_thinking_model", return_value=False):
                                with patch("src.open_canvas.nodes.rewrite_artifact.optionally_get_system_prompt_from_config", return_value=None):
                                    result = await rewrite_artifact(state, mock_config, store=mock_store)

        assert "artifact" in result
        artifact = result["artifact"]
        # New content should be code type
        assert artifact["contents"][1]["type"] == "code"
        assert "converted" in artifact["contents"][1]["code"]

    @pytest.mark.asyncio
    async def test_raises_on_no_artifact(self, mock_store, mock_config):
        """Should raise error when no artifact exists."""
        from src.open_canvas.nodes.rewrite_artifact import rewrite_artifact

        mock_llm = AsyncMock()

        state = {
            "_messages": [HumanMessage(content="Rewrite this")],
            "messages": [HumanMessage(content="Rewrite this")],
            "artifact": None,  # No artifact
        }

        with patch("src.open_canvas.nodes.rewrite_artifact.get_model_from_config", return_value=mock_llm):
            with patch("src.open_canvas.nodes.rewrite_artifact.get_model_config", return_value={"modelName": "gpt-4o"}):
                with patch("src.open_canvas.nodes.rewrite_artifact.get_formatted_reflections", return_value=""):
                    with pytest.raises(ValueError, match="No artifact found"):
                        await rewrite_artifact(state, mock_config, store=mock_store)

    @pytest.mark.asyncio
    async def test_raises_on_no_human_message(self, mock_store, mock_config):
        """Should raise error when no human message exists."""
        from src.open_canvas.nodes.rewrite_artifact import rewrite_artifact

        mock_llm = AsyncMock()

        state = {
            "_messages": [],  # No messages
            "messages": [],
            "artifact": {
                "currentIndex": 1,
                "contents": [{"index": 1, "type": "code", "code": "x=1"}],
            },
        }

        with patch("src.open_canvas.nodes.rewrite_artifact.get_model_from_config", return_value=mock_llm):
            with patch("src.open_canvas.nodes.rewrite_artifact.get_model_config", return_value={"modelName": "gpt-4o"}):
                with patch("src.open_canvas.nodes.rewrite_artifact.get_formatted_reflections", return_value=""):
                    with pytest.raises(ValueError, match="No recent human message found"):
                        await rewrite_artifact(state, mock_config, store=mock_store)

    @pytest.mark.asyncio
    async def test_handles_thinking_model_output(self, mock_store, mock_config):
        """Should extract thinking from thinking model output."""
        from src.open_canvas.nodes.rewrite_artifact import rewrite_artifact

        # Mock meta update response
        meta_response = MagicMock()
        meta_response.tool_calls = [{"args": {"type": "code", "title": "Code"}}]

        # Mock rewrite response with thinking tags
        rewrite_response = MagicMock()
        rewrite_response.content = "<think>Thinking about this...</think>def result(): pass"

        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(side_effect=[meta_response, rewrite_response])
        mock_llm.bind_tools = MagicMock(return_value=mock_llm)

        state = {
            "_messages": [HumanMessage(content="Update code")],
            "messages": [HumanMessage(content="Update code")],
            "artifact": {
                "currentIndex": 1,
                "contents": [{"index": 1, "type": "code", "code": "old", "language": "python"}],
            },
        }

        with patch("src.open_canvas.nodes.rewrite_artifact.get_model_from_config", return_value=mock_llm):
            with patch("src.open_canvas.nodes.rewrite_artifact.get_model_config", return_value={"modelName": "deepseek-reasoner"}):
                with patch("src.open_canvas.nodes.rewrite_artifact.get_formatted_reflections", return_value=""):
                    with patch("src.open_canvas.nodes.rewrite_artifact.create_context_document_messages", return_value=[]):
                        with patch("src.open_canvas.nodes.rewrite_artifact.is_using_o1_mini_model", return_value=False):
                            with patch("src.open_canvas.nodes.rewrite_artifact.is_thinking_model", return_value=True):
                                with patch("src.open_canvas.nodes.rewrite_artifact.optionally_get_system_prompt_from_config", return_value=None):
                                    result = await rewrite_artifact(state, mock_config, store=mock_store)

        # Should include thinking message
        if "messages" in result:
            thinking_msg = result["messages"][0]
            assert "Thinking about this" in thinking_msg.content

        # Artifact should not contain thinking tags
        artifact = result["artifact"]
        assert "<think>" not in artifact["contents"][1]["code"]
        assert "def result()" in artifact["contents"][1]["code"]

    @pytest.mark.asyncio
    async def test_preserves_artifact_history(self, mock_store, mock_config):
        """Should preserve existing artifact versions."""
        from src.open_canvas.nodes.rewrite_artifact import rewrite_artifact

        # Mock meta update response
        meta_response = MagicMock()
        meta_response.tool_calls = [{"args": {"type": "code", "title": "v3"}}]

        # Mock rewrite response
        rewrite_response = MagicMock()
        rewrite_response.content = "version 3 code"

        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(side_effect=[meta_response, rewrite_response])
        mock_llm.bind_tools = MagicMock(return_value=mock_llm)

        state = {
            "_messages": [HumanMessage(content="Update again")],
            "messages": [HumanMessage(content="Update again")],
            "artifact": {
                "currentIndex": 2,
                "contents": [
                    {"index": 1, "type": "code", "code": "v1", "language": "python"},
                    {"index": 2, "type": "code", "code": "v2", "language": "python"},
                ],
            },
        }

        with patch("src.open_canvas.nodes.rewrite_artifact.get_model_from_config", return_value=mock_llm):
            with patch("src.open_canvas.nodes.rewrite_artifact.get_model_config", return_value={"modelName": "gpt-4o"}):
                with patch("src.open_canvas.nodes.rewrite_artifact.get_formatted_reflections", return_value=""):
                    with patch("src.open_canvas.nodes.rewrite_artifact.create_context_document_messages", return_value=[]):
                        with patch("src.open_canvas.nodes.rewrite_artifact.is_using_o1_mini_model", return_value=False):
                            with patch("src.open_canvas.nodes.rewrite_artifact.is_thinking_model", return_value=False):
                                with patch("src.open_canvas.nodes.rewrite_artifact.optionally_get_system_prompt_from_config", return_value=None):
                                    result = await rewrite_artifact(state, mock_config, store=mock_store)

        artifact = result["artifact"]
        # Should have 3 versions now
        assert len(artifact["contents"]) == 3
        assert artifact["currentIndex"] == 3
        # Previous versions should still exist
        assert artifact["contents"][0]["code"] == "v1"
        assert artifact["contents"][1]["code"] == "v2"
        assert artifact["contents"][2]["code"] == "version 3 code"
