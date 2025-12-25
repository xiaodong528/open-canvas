"""
Unit tests for the generate_path node.

This node is responsible for routing requests to the appropriate handler
based on the user's input and current state.

Tests cover:
- Helper function existence and basic behavior
- URL extraction functionality
- Routing decision logic (hardcoded paths)
- Artifact content helpers
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from langchain_core.messages import HumanMessage, AIMessage


@pytest.mark.unit
class TestGeneratePath:
    """Tests for the generate_path routing node."""

    def test_generate_path_function_exists(self):
        """generate_path function should exist and be callable."""
        from src.open_canvas.nodes.generate_path import generate_path

        assert callable(generate_path)

    def test_get_model_config_function_exists(self):
        """get_model_config function should exist."""
        from src.open_canvas.nodes.generate_path import get_model_config

        assert callable(get_model_config)

    def test_get_model_from_config_function_exists(self):
        """get_model_from_config function should exist."""
        from src.open_canvas.nodes.generate_path import get_model_from_config

        assert callable(get_model_from_config)

    def test_valid_routing_destinations(self):
        """All valid routing destinations should be documented."""
        # These are the expected routing destinations
        valid_destinations = [
            "generateArtifact",
            "rewriteArtifact",
            "replyToGeneralInput",
            "updateArtifact",
            "updateHighlightedText",
            "customAction",
            "rewriteCodeArtifactTheme",
            "rewriteArtifactTheme",
            "webSearch",
        ]

        # Just verify these are the expected destinations
        # The actual routing logic is tested via integration tests
        assert len(valid_destinations) >= 6


@pytest.mark.unit
class TestGeneratePathHelpers:
    """Tests for generate_path helper functions."""

    def test_extract_urls_exists(self):
        """extract_urls helper should exist."""
        from src.open_canvas.nodes.generate_path import extract_urls

        assert callable(extract_urls)

    def test_extract_urls_basic_functionality(self):
        """extract_urls should find URLs in text."""
        from src.open_canvas.nodes.generate_path import extract_urls

        text = "Check out https://example.com and http://test.org for more info"
        urls = extract_urls(text)

        assert isinstance(urls, list)
        assert "https://example.com" in urls
        assert "http://test.org" in urls

    def test_extract_urls_markdown_links(self):
        """extract_urls should find URLs in markdown links."""
        from src.open_canvas.nodes.generate_path import extract_urls

        text = "See [this link](https://markdown.example.com) for details"
        urls = extract_urls(text)

        assert "https://markdown.example.com" in urls

    def test_extract_urls_mixed_formats(self):
        """extract_urls should handle mixed URL formats."""
        from src.open_canvas.nodes.generate_path import extract_urls

        text = """
        Check [docs](https://docs.example.com) and also https://plain.example.org.
        Another http://third.example.net here.
        """
        urls = extract_urls(text)

        assert len(urls) == 3
        assert "https://docs.example.com" in urls
        assert "https://plain.example.org" in urls
        assert "http://third.example.net" in urls

    def test_extract_urls_no_urls(self):
        """extract_urls should return empty list when no URLs present."""
        from src.open_canvas.nodes.generate_path import extract_urls

        text = "This is plain text without any URLs"
        urls = extract_urls(text)

        assert urls == []

    def test_extract_urls_deduplicates(self):
        """extract_urls should deduplicate URLs."""
        from src.open_canvas.nodes.generate_path import extract_urls

        text = "Visit https://example.com and https://example.com again"
        urls = extract_urls(text)

        # URLs should be unique
        assert len(urls) == len(set(urls))
        assert "https://example.com" in urls

    def test_should_include_url_contents_class_exists(self):
        """ShouldIncludeUrlContents class should exist."""
        from src.open_canvas.nodes.generate_path import ShouldIncludeUrlContents

        assert ShouldIncludeUrlContents is not None

    def test_dynamic_determine_path_exists(self):
        """_dynamic_determine_path function should exist."""
        from src.open_canvas.nodes.generate_path import _dynamic_determine_path

        assert callable(_dynamic_determine_path)


@pytest.mark.unit
class TestGeneratePathArtifactHelpers:
    """Tests for artifact-related helpers in generate_path."""

    def test_get_artifact_content_exists(self):
        """_get_artifact_content helper should exist."""
        from src.open_canvas.nodes.generate_path import _get_artifact_content

        assert callable(_get_artifact_content)

    def test_format_artifact_for_prompt_exists(self):
        """_format_artifact_for_prompt helper should exist."""
        from src.open_canvas.nodes.generate_path import _format_artifact_for_prompt

        assert callable(_format_artifact_for_prompt)

    def test_get_artifact_content_returns_none_for_none(self):
        """_get_artifact_content should return None for None artifact."""
        from src.open_canvas.nodes.generate_path import _get_artifact_content

        result = _get_artifact_content(None)
        assert result is None

    def test_get_artifact_content_finds_current_index(self):
        """_get_artifact_content should return content at currentIndex."""
        from src.open_canvas.nodes.generate_path import _get_artifact_content

        artifact = {
            "currentIndex": 2,
            "contents": [
                {"index": 1, "type": "code", "code": "v1"},
                {"index": 2, "type": "code", "code": "v2"},
            ],
        }

        result = _get_artifact_content(artifact)
        assert result is not None
        assert result["index"] == 2
        assert result["code"] == "v2"

    def test_get_artifact_content_fallback_to_last(self):
        """_get_artifact_content should fallback to last if currentIndex not found."""
        from src.open_canvas.nodes.generate_path import _get_artifact_content

        artifact = {
            "currentIndex": 99,  # Non-existent index
            "contents": [
                {"index": 1, "type": "code", "code": "first"},
                {"index": 2, "type": "code", "code": "last"},
            ],
        }

        result = _get_artifact_content(artifact)
        assert result is not None
        assert result["code"] == "last"

    def test_format_artifact_for_prompt_text(self):
        """_format_artifact_for_prompt should format text artifacts."""
        from src.open_canvas.nodes.generate_path import _format_artifact_for_prompt

        content = {
            "type": "text",
            "fullMarkdown": "# Hello World\n\nThis is content.",
        }

        result = _format_artifact_for_prompt(content)
        assert result == "# Hello World\n\nThis is content."

    def test_format_artifact_for_prompt_code(self):
        """_format_artifact_for_prompt should format code artifacts with fences."""
        from src.open_canvas.nodes.generate_path import _format_artifact_for_prompt

        content = {
            "type": "code",
            "language": "python",
            "code": "def hello():\n    print('Hello')",
        }

        result = _format_artifact_for_prompt(content)
        assert result.startswith("```python\n")
        assert "def hello():" in result
        assert result.endswith("\n```")

    def test_format_artifact_for_prompt_none(self):
        """_format_artifact_for_prompt should return empty string for None."""
        from src.open_canvas.nodes.generate_path import _format_artifact_for_prompt

        result = _format_artifact_for_prompt(None)
        assert result == ""


@pytest.mark.unit
class TestRouteDecisionHardcoded:
    """Tests for hardcoded routing decisions in generate_path."""

    @pytest.mark.asyncio
    async def test_routes_to_update_artifact_with_highlighted_code(self, mock_store, mock_config):
        """Should route to updateArtifact when highlightedCode is present."""
        from src.open_canvas.nodes.generate_path import generate_path

        state = {
            "_messages": [HumanMessage(content="Fix this code")],
            "messages": [HumanMessage(content="Fix this code")],
            "artifact": {"currentIndex": 1, "contents": [{"index": 1, "type": "code", "code": "x=1"}]},
            "highlightedCode": {
                "startCharIndex": 0,
                "endCharIndex": 3,
                "selectedText": "x=1",
            },
            "highlightedText": None,
            "language": None,
            "artifactLength": None,
            "regenerateWithEmojis": None,
            "readingLevel": None,
            "addComments": None,
            "addLogs": None,
            "portLanguage": None,
            "fixBugs": None,
            "customQuickActionId": None,
            "webSearchEnabled": False,
        }

        result = await generate_path(state, mock_config, store=mock_store)

        assert result["next"] == "updateArtifact"

    @pytest.mark.asyncio
    async def test_routes_to_update_highlighted_text(self, mock_store, mock_config):
        """Should route to updateHighlightedText when highlightedText is present."""
        from src.open_canvas.nodes.generate_path import generate_path

        state = {
            "_messages": [HumanMessage(content="Update this text")],
            "messages": [HumanMessage(content="Update this text")],
            "artifact": {"currentIndex": 1, "contents": [{"index": 1, "type": "text", "fullMarkdown": "Hello"}]},
            "highlightedCode": None,
            "highlightedText": {
                "fullMarkdown": "Hello World",
                "markdownBlock": "Hello World",
                "selectedText": "Hello",
            },
            "language": None,
            "artifactLength": None,
            "regenerateWithEmojis": None,
            "readingLevel": None,
            "addComments": None,
            "addLogs": None,
            "portLanguage": None,
            "fixBugs": None,
            "customQuickActionId": None,
            "webSearchEnabled": False,
        }

        result = await generate_path(state, mock_config, store=mock_store)

        assert result["next"] == "updateHighlightedText"

    @pytest.mark.asyncio
    async def test_routes_to_rewrite_artifact_theme_for_language(self, mock_store, mock_config):
        """Should route to rewriteArtifactTheme when language is set."""
        from src.open_canvas.nodes.generate_path import generate_path

        state = {
            "_messages": [HumanMessage(content="Make it formal")],
            "messages": [HumanMessage(content="Make it formal")],
            "artifact": {"currentIndex": 1, "contents": [{"index": 1, "type": "text", "fullMarkdown": "Hi"}]},
            "highlightedCode": None,
            "highlightedText": None,
            "language": "formal",
            "artifactLength": None,
            "regenerateWithEmojis": None,
            "readingLevel": None,
            "addComments": None,
            "addLogs": None,
            "portLanguage": None,
            "fixBugs": None,
            "customQuickActionId": None,
            "webSearchEnabled": False,
        }

        result = await generate_path(state, mock_config, store=mock_store)

        assert result["next"] == "rewriteArtifactTheme"

    @pytest.mark.asyncio
    async def test_routes_to_rewrite_artifact_theme_for_artifact_length(self, mock_store, mock_config):
        """Should route to rewriteArtifactTheme when artifactLength is set."""
        from src.open_canvas.nodes.generate_path import generate_path

        state = {
            "_messages": [HumanMessage(content="Make it shorter")],
            "messages": [HumanMessage(content="Make it shorter")],
            "artifact": {"currentIndex": 1, "contents": [{"index": 1, "type": "text", "fullMarkdown": "Long text"}]},
            "highlightedCode": None,
            "highlightedText": None,
            "language": None,
            "artifactLength": "short",
            "regenerateWithEmojis": None,
            "readingLevel": None,
            "addComments": None,
            "addLogs": None,
            "portLanguage": None,
            "fixBugs": None,
            "customQuickActionId": None,
            "webSearchEnabled": False,
        }

        result = await generate_path(state, mock_config, store=mock_store)

        assert result["next"] == "rewriteArtifactTheme"

    @pytest.mark.asyncio
    async def test_routes_to_rewrite_code_artifact_theme_for_add_comments(self, mock_store, mock_config):
        """Should route to rewriteCodeArtifactTheme when addComments is set."""
        from src.open_canvas.nodes.generate_path import generate_path

        state = {
            "_messages": [HumanMessage(content="Add comments")],
            "messages": [HumanMessage(content="Add comments")],
            "artifact": {"currentIndex": 1, "contents": [{"index": 1, "type": "code", "code": "x=1"}]},
            "highlightedCode": None,
            "highlightedText": None,
            "language": None,
            "artifactLength": None,
            "regenerateWithEmojis": None,
            "readingLevel": None,
            "addComments": True,
            "addLogs": None,
            "portLanguage": None,
            "fixBugs": None,
            "customQuickActionId": None,
            "webSearchEnabled": False,
        }

        result = await generate_path(state, mock_config, store=mock_store)

        assert result["next"] == "rewriteCodeArtifactTheme"

    @pytest.mark.asyncio
    async def test_routes_to_rewrite_code_artifact_theme_for_fix_bugs(self, mock_store, mock_config):
        """Should route to rewriteCodeArtifactTheme when fixBugs is set."""
        from src.open_canvas.nodes.generate_path import generate_path

        state = {
            "_messages": [HumanMessage(content="Fix bugs")],
            "messages": [HumanMessage(content="Fix bugs")],
            "artifact": {"currentIndex": 1, "contents": [{"index": 1, "type": "code", "code": "x=1"}]},
            "highlightedCode": None,
            "highlightedText": None,
            "language": None,
            "artifactLength": None,
            "regenerateWithEmojis": None,
            "readingLevel": None,
            "addComments": None,
            "addLogs": None,
            "portLanguage": None,
            "fixBugs": True,
            "customQuickActionId": None,
            "webSearchEnabled": False,
        }

        result = await generate_path(state, mock_config, store=mock_store)

        assert result["next"] == "rewriteCodeArtifactTheme"

    @pytest.mark.asyncio
    async def test_routes_to_custom_action(self, mock_store, mock_config):
        """Should route to customAction when customQuickActionId is set."""
        from src.open_canvas.nodes.generate_path import generate_path

        state = {
            "_messages": [HumanMessage(content="Run custom action")],
            "messages": [HumanMessage(content="Run custom action")],
            "artifact": {"currentIndex": 1, "contents": [{"index": 1, "type": "code", "code": "x=1"}]},
            "highlightedCode": None,
            "highlightedText": None,
            "language": None,
            "artifactLength": None,
            "regenerateWithEmojis": None,
            "readingLevel": None,
            "addComments": None,
            "addLogs": None,
            "portLanguage": None,
            "fixBugs": None,
            "customQuickActionId": "action-123",
            "webSearchEnabled": False,
        }

        result = await generate_path(state, mock_config, store=mock_store)

        assert result["next"] == "customAction"

    @pytest.mark.asyncio
    async def test_routes_to_web_search(self, mock_store, mock_config):
        """Should route to webSearch when webSearchEnabled is True."""
        from src.open_canvas.nodes.generate_path import generate_path

        state = {
            "_messages": [HumanMessage(content="Search the web")],
            "messages": [HumanMessage(content="Search the web")],
            "artifact": None,
            "highlightedCode": None,
            "highlightedText": None,
            "language": None,
            "artifactLength": None,
            "regenerateWithEmojis": None,
            "readingLevel": None,
            "addComments": None,
            "addLogs": None,
            "portLanguage": None,
            "fixBugs": None,
            "customQuickActionId": None,
            "webSearchEnabled": True,
        }

        result = await generate_path(state, mock_config, store=mock_store)

        assert result["next"] == "webSearch"


@pytest.mark.unit
class TestDynamicRoutingWithMock:
    """Tests for LLM-based dynamic routing using mock."""

    @pytest.mark.asyncio
    async def test_routes_to_generate_artifact_without_existing(
        self, mock_store, mock_config, mock_llm_with_tool_response
    ):
        """Should route to generateArtifact when no artifact exists and LLM decides."""
        from src.open_canvas.nodes.generate_path import generate_path

        # Create mock LLM that returns generateArtifact route
        mock_llm = mock_llm_with_tool_response("generateArtifact")

        state = {
            "_messages": [HumanMessage(content="Write a Python function")],
            "messages": [HumanMessage(content="Write a Python function")],
            "artifact": None,  # No existing artifact
            "highlightedCode": None,
            "highlightedText": None,
            "language": None,
            "artifactLength": None,
            "regenerateWithEmojis": None,
            "readingLevel": None,
            "addComments": None,
            "addLogs": None,
            "portLanguage": None,
            "fixBugs": None,
            "customQuickActionId": None,
            "webSearchEnabled": False,
        }

        with patch("src.open_canvas.nodes.generate_path.get_model_from_config", return_value=mock_llm):
            with patch("src.open_canvas.nodes.generate_path.create_context_document_messages", return_value=[]):
                result = await generate_path(state, mock_config, store=mock_store)

        assert result["next"] == "generateArtifact"

    @pytest.mark.asyncio
    async def test_routes_to_rewrite_artifact_with_existing(
        self, mock_store, mock_config, mock_llm_with_tool_response
    ):
        """Should route to rewriteArtifact when artifact exists and LLM decides."""
        from src.open_canvas.nodes.generate_path import generate_path

        # Create mock LLM that returns rewriteArtifact route
        mock_llm = mock_llm_with_tool_response("rewriteArtifact")

        state = {
            "_messages": [HumanMessage(content="Update the function to handle errors")],
            "messages": [HumanMessage(content="Update the function to handle errors")],
            "artifact": {
                "currentIndex": 1,
                "contents": [{"index": 1, "type": "code", "code": "def hello(): pass"}],
            },
            "highlightedCode": None,
            "highlightedText": None,
            "language": None,
            "artifactLength": None,
            "regenerateWithEmojis": None,
            "readingLevel": None,
            "addComments": None,
            "addLogs": None,
            "portLanguage": None,
            "fixBugs": None,
            "customQuickActionId": None,
            "webSearchEnabled": False,
        }

        with patch("src.open_canvas.nodes.generate_path.get_model_from_config", return_value=mock_llm):
            with patch("src.open_canvas.nodes.generate_path.create_context_document_messages", return_value=[]):
                result = await generate_path(state, mock_config, store=mock_store)

        assert result["next"] == "rewriteArtifact"

    @pytest.mark.asyncio
    async def test_routes_to_reply_general_input(
        self, mock_store, mock_config, mock_llm_with_tool_response
    ):
        """Should route to replyToGeneralInput when LLM decides for general chat."""
        from src.open_canvas.nodes.generate_path import generate_path

        # Create mock LLM that returns replyToGeneralInput route
        mock_llm = mock_llm_with_tool_response("replyToGeneralInput")

        state = {
            "_messages": [HumanMessage(content="What is the weather like?")],
            "messages": [HumanMessage(content="What is the weather like?")],
            "artifact": None,
            "highlightedCode": None,
            "highlightedText": None,
            "language": None,
            "artifactLength": None,
            "regenerateWithEmojis": None,
            "readingLevel": None,
            "addComments": None,
            "addLogs": None,
            "portLanguage": None,
            "fixBugs": None,
            "customQuickActionId": None,
            "webSearchEnabled": False,
        }

        with patch("src.open_canvas.nodes.generate_path.get_model_from_config", return_value=mock_llm):
            with patch("src.open_canvas.nodes.generate_path.create_context_document_messages", return_value=[]):
                result = await generate_path(state, mock_config, store=mock_store)

        assert result["next"] == "replyToGeneralInput"

    @pytest.mark.asyncio
    async def test_fallback_to_general_reply_on_no_tool_calls(self, mock_store, mock_config):
        """Should fallback to replyToGeneralInput when LLM returns no tool calls."""
        from src.open_canvas.nodes.generate_path import generate_path

        # Create mock LLM with no tool calls
        mock_llm = AsyncMock()
        mock_response = MagicMock()
        mock_response.tool_calls = []  # No tool calls
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)
        mock_llm.bind_tools = MagicMock(return_value=mock_llm)

        state = {
            "_messages": [HumanMessage(content="Hello")],
            "messages": [HumanMessage(content="Hello")],
            "artifact": None,
            "highlightedCode": None,
            "highlightedText": None,
            "language": None,
            "artifactLength": None,
            "regenerateWithEmojis": None,
            "readingLevel": None,
            "addComments": None,
            "addLogs": None,
            "portLanguage": None,
            "fixBugs": None,
            "customQuickActionId": None,
            "webSearchEnabled": False,
        }

        with patch("src.open_canvas.nodes.generate_path.get_model_from_config", return_value=mock_llm):
            with patch("src.open_canvas.nodes.generate_path.create_context_document_messages", return_value=[]):
                result = await generate_path(state, mock_config, store=mock_store)

        assert result["next"] == "replyToGeneralInput"


@pytest.mark.unit
class TestMessageHelpers:
    """Tests for message-related helper functions."""

    def test_get_message_content_with_string(self):
        """_get_message_content should return string content directly."""
        from src.open_canvas.nodes.generate_path import _get_message_content

        msg = HumanMessage(content="Hello world")
        result = _get_message_content(msg)

        assert result == "Hello world"

    def test_get_message_content_with_list(self):
        """_get_message_content should extract text from list content."""
        from src.open_canvas.nodes.generate_path import _get_message_content

        msg = HumanMessage(content=[
            {"type": "text", "text": "Part 1"},
            {"type": "text", "text": "Part 2"},
        ])
        result = _get_message_content(msg)

        assert "Part 1" in result
        assert "Part 2" in result

    def test_format_recent_messages(self):
        """_format_recent_messages should format last N messages."""
        from src.open_canvas.nodes.generate_path import _format_recent_messages

        messages = [
            HumanMessage(content="First"),
            AIMessage(content="Second"),
            HumanMessage(content="Third"),
            AIMessage(content="Fourth"),
        ]

        result = _format_recent_messages(messages, count=2)

        assert "Third" in result
        assert "Fourth" in result
        # Should not include earlier messages
        assert "First" not in result

    def test_format_recent_messages_with_less_than_count(self):
        """_format_recent_messages should handle fewer messages than count."""
        from src.open_canvas.nodes.generate_path import _format_recent_messages

        messages = [
            HumanMessage(content="Only one"),
        ]

        result = _format_recent_messages(messages, count=5)

        assert "Only one" in result


@pytest.mark.unit
class TestFindExistingDocMessage:
    """Tests for _find_existing_doc_message helper."""

    def test_finds_document_type_message(self):
        """Should find message with document type content."""
        from src.open_canvas.nodes.generate_path import _find_existing_doc_message

        messages = [
            HumanMessage(content="Plain text"),
            HumanMessage(content=[
                {"type": "text", "text": "With doc"},
                {"type": "document", "source": {"type": "base64", "data": "..."}},
            ]),
        ]

        result = _find_existing_doc_message(messages)

        assert result is not None
        assert isinstance(result.content, list)

    def test_finds_pdf_type_message(self):
        """Should find message with application/pdf type content."""
        from src.open_canvas.nodes.generate_path import _find_existing_doc_message

        messages = [
            HumanMessage(content=[
                {"type": "application/pdf", "data": "base64data"},
            ]),
        ]

        result = _find_existing_doc_message(messages)

        assert result is not None

    def test_returns_none_for_no_doc_messages(self):
        """Should return None when no document messages exist."""
        from src.open_canvas.nodes.generate_path import _find_existing_doc_message

        messages = [
            HumanMessage(content="Plain text only"),
            AIMessage(content="Response"),
        ]

        result = _find_existing_doc_message(messages)

        assert result is None

    def test_returns_none_for_empty_list(self):
        """Should return None for empty message list."""
        from src.open_canvas.nodes.generate_path import _find_existing_doc_message

        result = _find_existing_doc_message([])

        assert result is None
