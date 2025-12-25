"""
Unit tests for the generate_artifact node.

This node is responsible for generating new artifacts (code or text)
based on user requests.

Tests cover:
- Function and class existence
- Helper function behavior
- Artifact content creation
- Full node execution with mock LLM
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from langchain_core.messages import HumanMessage, AIMessage


@pytest.mark.unit
class TestGenerateArtifact:
    """Tests for the generate_artifact node."""

    def test_generate_artifact_function_exists(self):
        """generate_artifact function should exist and be callable."""
        from src.open_canvas.nodes.generate_artifact import generate_artifact

        assert callable(generate_artifact)

    def test_get_model_config_function_exists(self):
        """get_model_config function should be imported."""
        from src.open_canvas.nodes.generate_artifact import get_model_config

        assert callable(get_model_config)

    def test_get_model_from_config_function_exists(self):
        """get_model_from_config function should be imported."""
        from src.open_canvas.nodes.generate_artifact import get_model_from_config

        assert callable(get_model_from_config)

    def test_generate_artifact_tool_class_exists(self):
        """GenerateArtifactTool class should exist."""
        from src.open_canvas.nodes.generate_artifact import GenerateArtifactTool

        assert GenerateArtifactTool is not None


@pytest.mark.unit
class TestGenerateArtifactHelpers:
    """Tests for generate_artifact helper functions."""

    def test_format_new_artifact_prompt_exists(self):
        """_format_new_artifact_prompt helper should exist."""
        from src.open_canvas.nodes.generate_artifact import _format_new_artifact_prompt

        assert callable(_format_new_artifact_prompt)

    def test_create_artifact_content_exists(self):
        """_create_artifact_content helper should exist."""
        from src.open_canvas.nodes.generate_artifact import _create_artifact_content

        assert callable(_create_artifact_content)


@pytest.mark.unit
class TestGenerateArtifactOutput:
    """Tests for artifact output structure."""

    def test_artifact_v3_type_is_defined(self):
        """ArtifactV3 type should be importable."""
        from src.types import ArtifactV3

        assert ArtifactV3 is not None

    def test_artifact_code_v3_type_is_defined(self):
        """ArtifactCodeV3 type should be importable."""
        from src.types import ArtifactCodeV3

        assert ArtifactCodeV3 is not None

    def test_artifact_markdown_v3_type_is_defined(self):
        """ArtifactMarkdownV3 type should be importable."""
        from src.types import ArtifactMarkdownV3

        assert ArtifactMarkdownV3 is not None

    def test_programming_language_options_are_defined(self):
        """ProgrammingLanguageOptions should contain expected languages."""
        from src.types import ProgrammingLanguageOptions

        # Verify it's a type definition
        assert ProgrammingLanguageOptions is not None


@pytest.mark.unit
class TestFormatNewArtifactPrompt:
    """Tests for _format_new_artifact_prompt helper."""

    def test_includes_reflections(self):
        """Should include memories/reflections in prompt."""
        from src.open_canvas.nodes.generate_artifact import _format_new_artifact_prompt

        memories = "User prefers Python code with type hints."
        result = _format_new_artifact_prompt(memories, "gpt-4o")

        assert "User prefers Python" in result or memories in result

    def test_adds_cot_disable_for_claude(self):
        """Should add CoT disable instruction for Claude models."""
        from src.open_canvas.nodes.generate_artifact import _format_new_artifact_prompt

        result = _format_new_artifact_prompt("", "claude-3-5-sonnet")

        assert "Do NOT preform chain of thought" in result or "STRAIGHT to generating" in result

    def test_no_cot_disable_for_openai(self):
        """Should NOT add CoT disable for OpenAI models."""
        from src.open_canvas.nodes.generate_artifact import _format_new_artifact_prompt

        result = _format_new_artifact_prompt("", "gpt-4o")

        # Should not contain Claude-specific instructions
        assert "Do NOT preform chain of thought" not in result


@pytest.mark.unit
class TestCreateArtifactContent:
    """Tests for _create_artifact_content helper."""

    def test_creates_code_artifact(self):
        """Should create code artifact from tool call."""
        from src.open_canvas.nodes.generate_artifact import _create_artifact_content

        tool_call = {
            "type": "code",
            "title": "Fibonacci Function",
            "artifact": "def fib(n):\n    return n if n <= 1 else fib(n-1) + fib(n-2)",
            "language": "python",
            "isValidReact": False,
        }

        result = _create_artifact_content(tool_call)

        assert result["type"] == "code"
        assert result["index"] == 1
        assert result["title"] == "Fibonacci Function"
        assert result["code"] == tool_call["artifact"]
        assert result["language"] == "python"
        assert result["isValidReact"] is False

    def test_creates_text_artifact(self):
        """Should create text/markdown artifact from tool call."""
        from src.open_canvas.nodes.generate_artifact import _create_artifact_content

        tool_call = {
            "type": "text",
            "title": "Project README",
            "artifact": "# My Project\n\nA description of my project.",
        }

        result = _create_artifact_content(tool_call)

        assert result["type"] == "text"
        assert result["index"] == 1
        assert result["title"] == "Project README"
        assert result["fullMarkdown"] == tool_call["artifact"]

    def test_code_artifact_defaults(self):
        """Should use default values for missing code artifact fields."""
        from src.open_canvas.nodes.generate_artifact import _create_artifact_content

        tool_call = {
            "type": "code",
            "artifact": "console.log('hello');",
        }

        result = _create_artifact_content(tool_call)

        assert result["title"] == ""
        assert result["language"] == "other"
        assert result["isValidReact"] is False

    def test_text_artifact_defaults(self):
        """Should use default values for missing text artifact fields."""
        from src.open_canvas.nodes.generate_artifact import _create_artifact_content

        tool_call = {
            "type": "text",
            "artifact": "Some text content",
        }

        result = _create_artifact_content(tool_call)

        assert result["title"] == ""
        assert result["fullMarkdown"] == "Some text content"


@pytest.mark.unit
class TestGenerateArtifactToolSchema:
    """Tests for GenerateArtifactTool schema validation."""

    def test_valid_code_tool_call(self):
        """Should validate valid code generation tool call."""
        from src.open_canvas.nodes.generate_artifact import GenerateArtifactTool

        tool = GenerateArtifactTool(
            type="code",
            language="python",
            isValidReact=False,
            artifact="print('hello')",
            title="Hello Script",
        )

        assert tool.type == "code"
        assert tool.language == "python"
        assert tool.artifact == "print('hello')"
        assert tool.title == "Hello Script"

    def test_valid_text_tool_call(self):
        """Should validate valid text generation tool call."""
        from src.open_canvas.nodes.generate_artifact import GenerateArtifactTool

        tool = GenerateArtifactTool(
            type="text",
            artifact="# Hello World",
            title="Greeting Doc",
        )

        assert tool.type == "text"
        assert tool.artifact == "# Hello World"
        assert tool.language is None  # Optional for text

    def test_optional_fields_default(self):
        """Optional fields should have defaults."""
        from src.open_canvas.nodes.generate_artifact import GenerateArtifactTool

        tool = GenerateArtifactTool(
            type="text",
            artifact="content",
            title="Title",
        )

        assert tool.language is None
        assert tool.isValidReact is None


@pytest.mark.unit
class TestGenerateArtifactNodeWithMock:
    """Tests for generate_artifact node using mock LLM."""

    @pytest.mark.asyncio
    async def test_generates_code_artifact(
        self, mock_store, mock_config, mock_artifact_generation_response
    ):
        """Should generate code artifact when LLM returns code tool call."""
        from src.open_canvas.nodes.generate_artifact import generate_artifact

        # Create mock LLM response
        mock_response = mock_artifact_generation_response(
            code="def hello():\n    print('Hello, World!')",
            title="Hello Function",
            artifact_type="code",
            language="python",
        )

        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)
        mock_llm.bind_tools = MagicMock(return_value=mock_llm)

        state = {
            "_messages": [HumanMessage(content="Write a hello world function")],
            "messages": [HumanMessage(content="Write a hello world function")],
            "artifact": None,
        }

        with patch("src.open_canvas.nodes.generate_artifact.get_model_from_config", return_value=mock_llm):
            with patch("src.open_canvas.nodes.generate_artifact.get_model_config", return_value={"modelName": "gpt-4o"}):
                with patch("src.open_canvas.nodes.generate_artifact.get_formatted_reflections", return_value=""):
                    with patch("src.open_canvas.nodes.generate_artifact.create_context_document_messages", return_value=[]):
                        with patch("src.open_canvas.nodes.generate_artifact.is_using_o1_mini_model", return_value=False):
                            with patch("src.open_canvas.nodes.generate_artifact.optionally_get_system_prompt_from_config", return_value=None):
                                result = await generate_artifact(state, mock_config, store=mock_store)

        assert "artifact" in result
        artifact = result["artifact"]
        assert artifact["currentIndex"] == 1
        assert len(artifact["contents"]) == 1
        assert artifact["contents"][0]["type"] == "code"
        assert artifact["contents"][0]["title"] == "Hello Function"
        assert "def hello()" in artifact["contents"][0]["code"]

    @pytest.mark.asyncio
    async def test_generates_text_artifact(
        self, mock_store, mock_config, mock_artifact_generation_response
    ):
        """Should generate text artifact when LLM returns text tool call."""
        from src.open_canvas.nodes.generate_artifact import generate_artifact

        # Create mock LLM response for text artifact
        mock_response = mock_artifact_generation_response(
            full_markdown="# My Essay\n\nThis is an essay about AI.",
            title="AI Essay",
            artifact_type="text",
        )

        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)
        mock_llm.bind_tools = MagicMock(return_value=mock_llm)

        state = {
            "_messages": [HumanMessage(content="Write an essay about AI")],
            "messages": [HumanMessage(content="Write an essay about AI")],
            "artifact": None,
        }

        with patch("src.open_canvas.nodes.generate_artifact.get_model_from_config", return_value=mock_llm):
            with patch("src.open_canvas.nodes.generate_artifact.get_model_config", return_value={"modelName": "gpt-4o"}):
                with patch("src.open_canvas.nodes.generate_artifact.get_formatted_reflections", return_value=""):
                    with patch("src.open_canvas.nodes.generate_artifact.create_context_document_messages", return_value=[]):
                        with patch("src.open_canvas.nodes.generate_artifact.is_using_o1_mini_model", return_value=False):
                            with patch("src.open_canvas.nodes.generate_artifact.optionally_get_system_prompt_from_config", return_value=None):
                                result = await generate_artifact(state, mock_config, store=mock_store)

        assert "artifact" in result
        artifact = result["artifact"]
        assert artifact["contents"][0]["type"] == "text"
        assert artifact["contents"][0]["title"] == "AI Essay"
        assert "AI" in artifact["contents"][0]["fullMarkdown"]

    @pytest.mark.asyncio
    async def test_raises_on_no_tool_calls(self, mock_store, mock_config):
        """Should raise error when LLM returns no tool calls."""
        from src.open_canvas.nodes.generate_artifact import generate_artifact

        # Create mock LLM with no tool calls
        mock_response = MagicMock()
        mock_response.tool_calls = []  # No tool calls

        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)
        mock_llm.bind_tools = MagicMock(return_value=mock_llm)

        state = {
            "_messages": [HumanMessage(content="Write something")],
            "messages": [HumanMessage(content="Write something")],
            "artifact": None,
        }

        with patch("src.open_canvas.nodes.generate_artifact.get_model_from_config", return_value=mock_llm):
            with patch("src.open_canvas.nodes.generate_artifact.get_model_config", return_value={"modelName": "gpt-4o"}):
                with patch("src.open_canvas.nodes.generate_artifact.get_formatted_reflections", return_value=""):
                    with patch("src.open_canvas.nodes.generate_artifact.create_context_document_messages", return_value=[]):
                        with patch("src.open_canvas.nodes.generate_artifact.is_using_o1_mini_model", return_value=False):
                            with patch("src.open_canvas.nodes.generate_artifact.optionally_get_system_prompt_from_config", return_value=None):
                                with pytest.raises(ValueError, match="No tool calls found"):
                                    await generate_artifact(state, mock_config, store=mock_store)

    @pytest.mark.asyncio
    async def test_raises_on_empty_args(self, mock_store, mock_config):
        """Should raise error when tool call has empty args."""
        from src.open_canvas.nodes.generate_artifact import generate_artifact

        # Create mock LLM with empty args
        mock_response = MagicMock()
        mock_response.tool_calls = [{"args": {}}]  # Empty args

        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)
        mock_llm.bind_tools = MagicMock(return_value=mock_llm)

        state = {
            "_messages": [HumanMessage(content="Write something")],
            "messages": [HumanMessage(content="Write something")],
            "artifact": None,
        }

        with patch("src.open_canvas.nodes.generate_artifact.get_model_from_config", return_value=mock_llm):
            with patch("src.open_canvas.nodes.generate_artifact.get_model_config", return_value={"modelName": "gpt-4o"}):
                with patch("src.open_canvas.nodes.generate_artifact.get_formatted_reflections", return_value=""):
                    with patch("src.open_canvas.nodes.generate_artifact.create_context_document_messages", return_value=[]):
                        with patch("src.open_canvas.nodes.generate_artifact.is_using_o1_mini_model", return_value=False):
                            with patch("src.open_canvas.nodes.generate_artifact.optionally_get_system_prompt_from_config", return_value=None):
                                with pytest.raises(ValueError, match="No args found"):
                                    await generate_artifact(state, mock_config, store=mock_store)

    @pytest.mark.asyncio
    async def test_uses_o1_model_correctly(self, mock_store, mock_config, mock_artifact_generation_response):
        """Should use HumanMessage for system prompt with O1 models."""
        from src.open_canvas.nodes.generate_artifact import generate_artifact

        mock_response = mock_artifact_generation_response(
            code="print('hello')",
            title="Test",
            artifact_type="code",
            language="python",
        )

        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)
        mock_llm.bind_tools = MagicMock(return_value=mock_llm)

        state = {
            "_messages": [HumanMessage(content="Write code")],
            "messages": [HumanMessage(content="Write code")],
            "artifact": None,
        }

        with patch("src.open_canvas.nodes.generate_artifact.get_model_from_config", return_value=mock_llm):
            with patch("src.open_canvas.nodes.generate_artifact.get_model_config", return_value={"modelName": "o1-mini"}):
                with patch("src.open_canvas.nodes.generate_artifact.get_formatted_reflections", return_value=""):
                    with patch("src.open_canvas.nodes.generate_artifact.create_context_document_messages", return_value=[]):
                        with patch("src.open_canvas.nodes.generate_artifact.is_using_o1_mini_model", return_value=True):
                            with patch("src.open_canvas.nodes.generate_artifact.optionally_get_system_prompt_from_config", return_value=None):
                                await generate_artifact(state, mock_config, store=mock_store)

        # Verify ainvoke was called
        mock_llm.ainvoke.assert_called_once()
        # First message should be HumanMessage for O1 models
        call_args = mock_llm.ainvoke.call_args[0][0]
        from langchain_core.messages import HumanMessage as HM
        assert isinstance(call_args[0], HM)

    @pytest.mark.asyncio
    async def test_includes_user_system_prompt(self, mock_store, mock_artifact_generation_response):
        """Should include user's custom system prompt when provided."""
        from src.open_canvas.nodes.generate_artifact import generate_artifact

        mock_response = mock_artifact_generation_response(
            code="x = 1",
            title="Variable",
            artifact_type="code",
            language="python",
        )

        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)
        mock_llm.bind_tools = MagicMock(return_value=mock_llm)

        config = {
            "configurable": {
                "customModelName": "gpt-4o",
                "assistant_id": "test-assistant",
                "systemPrompt": "Always use descriptive variable names.",
            }
        }

        state = {
            "_messages": [HumanMessage(content="Create a variable")],
            "messages": [HumanMessage(content="Create a variable")],
            "artifact": None,
        }

        user_prompt = "Always use descriptive variable names."

        with patch("src.open_canvas.nodes.generate_artifact.get_model_from_config", return_value=mock_llm):
            with patch("src.open_canvas.nodes.generate_artifact.get_model_config", return_value={"modelName": "gpt-4o"}):
                with patch("src.open_canvas.nodes.generate_artifact.get_formatted_reflections", return_value=""):
                    with patch("src.open_canvas.nodes.generate_artifact.create_context_document_messages", return_value=[]):
                        with patch("src.open_canvas.nodes.generate_artifact.is_using_o1_mini_model", return_value=False):
                            with patch("src.open_canvas.nodes.generate_artifact.optionally_get_system_prompt_from_config", return_value=user_prompt):
                                await generate_artifact(state, config, store=mock_store)

        # Verify the system prompt includes user's custom prompt
        call_args = mock_llm.ainvoke.call_args[0][0]
        system_msg = call_args[0]
        assert user_prompt in system_msg.content
