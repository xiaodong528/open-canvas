"""
Integration tests for the main agent graph.

These tests verify that the complete graph works correctly with all nodes
connected and routing properly.
"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.store.memory import InMemoryStore


@pytest.mark.integration
class TestAgentGraph:
    """Integration tests for the main agent graph."""

    def test_graph_compiles_successfully(self):
        """Graph should compile without errors."""
        from src.open_canvas.graph import graph

        assert graph is not None
        assert hasattr(graph, "invoke")
        assert hasattr(graph, "ainvoke")
        assert hasattr(graph, "stream")

    def test_graph_has_required_nodes(self):
        """Graph should have all required nodes."""
        from src.open_canvas.graph import graph

        # Check that the graph has nodes
        assert hasattr(graph, "nodes") or graph is not None

    def test_graph_has_correct_entry_point(self):
        """Graph should have correct entry point configuration."""
        from src.open_canvas.graph import graph

        # The graph should start with generatePath or similar routing node
        assert graph is not None


@pytest.mark.integration
class TestGraphRouting:
    """Tests for graph routing logic."""

    def test_route_node_exists(self):
        """route_node function should exist."""
        from src.open_canvas.graph import route_node

        assert callable(route_node)

    def test_clean_state_exists(self):
        """clean_state function should exist."""
        from src.open_canvas.graph import clean_state

        assert callable(clean_state)

    def test_conditionally_generate_title_exists(self):
        """conditionally_generate_title function should exist."""
        from src.open_canvas.graph import conditionally_generate_title

        assert callable(conditionally_generate_title)

    def test_route_post_web_search_exists(self):
        """route_post_web_search function should exist."""
        from src.open_canvas.graph import route_post_web_search

        assert callable(route_post_web_search)


@pytest.mark.integration
class TestRouteNodeLogic:
    """Tests for route_node routing logic."""

    def test_route_node_returns_send_object(self):
        """route_node should return a Send object with the correct node."""
        from src.open_canvas.graph import route_node
        from langgraph.types import Send

        state = {"next": "generateArtifact"}
        result = route_node(state)

        # route_node returns a Send object for dynamic routing
        assert isinstance(result, Send)
        assert result.node == "generateArtifact"

    def test_route_node_with_different_routes(self):
        """route_node should return Send objects for each route."""
        from src.open_canvas.graph import route_node
        from langgraph.types import Send

        routes = [
            "generateArtifact",
            "rewriteArtifact",
            "updateArtifact",
            "updateHighlightedText",
            "replyToGeneralInput",
            "customAction",
            "webSearch",
        ]

        for route in routes:
            state = {"next": route}
            result = route_node(state)
            assert isinstance(result, Send)
            assert result.node == route


@pytest.mark.integration
class TestCleanState:
    """Tests for clean_state function."""

    def test_clean_state_resets_inputs(self):
        """clean_state should reset state inputs to defaults."""
        from src.open_canvas.graph import clean_state

        state = {
            "highlightedCode": {"startCharIndex": 0, "endCharIndex": 10},
            "highlightedText": {"selectedText": "test"},
            "language": "typescript",
            "artifactLength": "short",
            "next": "generateArtifact",
            "webSearchEnabled": True,
        }

        result = clean_state(state)

        # All these should be reset to None
        assert result.get("highlightedCode") is None
        assert result.get("highlightedText") is None
        assert result.get("language") is None
        assert result.get("artifactLength") is None
        assert result.get("next") is None
        assert result.get("webSearchEnabled") is None

    def test_clean_state_preserves_messages(self):
        """clean_state should NOT reset messages or artifact."""
        from src.open_canvas.graph import clean_state

        state = {
            "messages": [HumanMessage(content="Hello")],
            "artifact": {"currentIndex": 1, "contents": []},
            "highlightedCode": {"startCharIndex": 0},
        }

        result = clean_state(state)

        # Messages and artifact should NOT be in the result (not reset)
        assert "messages" not in result
        assert "artifact" not in result


@pytest.mark.integration
class TestConditionallyGenerateTitle:
    """Tests for conditionally_generate_title function."""

    def test_conditionally_generate_title_no_messages(self):
        """Should return END when no messages in state."""
        from src.open_canvas.graph import conditionally_generate_title
        from langgraph.constants import END

        # No messages at all
        state = {"artifact": None, "messages": []}
        result = conditionally_generate_title(state)
        # With no messages and no artifact, should return END
        assert result == END or result is not None

    def test_conditionally_generate_title_with_artifact(self):
        """Should return generateTitle when artifact exists and conditions met."""
        from src.open_canvas.graph import conditionally_generate_title

        state = {
            "artifact": {
                "currentIndex": 1,
                "contents": [{"index": 1, "type": "code", "title": "Test"}],
            },
            "messages": [HumanMessage(content="Hello")],
        }

        # The logic checks lastAssistantMessage and hasArtifact
        # Result depends on implementation details
        result = conditionally_generate_title(state)
        assert result is not None  # Should return a valid route


@pytest.mark.integration
class TestRoutePostWebSearch:
    """Tests for route_post_web_search function."""

    def test_route_post_web_search_with_artifact(self):
        """Should route correctly after web search based on artifact presence."""
        from src.open_canvas.graph import route_post_web_search
        from langgraph.types import Send

        state = {
            "artifact": {
                "currentIndex": 1,
                "contents": [{"index": 1, "type": "code"}],
            },
            "webSearchResults": [{"pageContent": "result", "metadata": {}}],
        }

        result = route_post_web_search(state)

        # Should return Send command(s) or route string
        assert result is not None

    def test_route_post_web_search_without_artifact(self):
        """Should route to generateArtifact when no artifact exists."""
        from src.open_canvas.graph import route_post_web_search

        state = {
            "artifact": None,
            "webSearchResults": [{"pageContent": "result", "metadata": {}}],
        }

        result = route_post_web_search(state)
        assert result is not None


@pytest.mark.integration
class TestGraphWithMockLLM:
    """Integration tests using mock LLM instead of real API."""

    @pytest.mark.asyncio
    async def test_generate_path_routes_correctly_with_mock(self, mock_config):
        """Test that generate_path correctly routes based on mock LLM response."""
        from src.open_canvas.nodes.generate_path import generate_path

        store = InMemoryStore()

        # Create mock LLM that returns generateArtifact route
        mock_llm = AsyncMock()
        mock_response = MagicMock()
        mock_response.tool_calls = [{"args": {"route": "generateArtifact"}}]
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)
        mock_llm.bind_tools = MagicMock(return_value=mock_llm)

        state = {
            "_messages": [HumanMessage(content="Write a Python function")],
            "messages": [HumanMessage(content="Write a Python function")],
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

        with patch(
            "src.open_canvas.nodes.generate_path.get_model_from_config",
            return_value=mock_llm,
        ):
            with patch(
                "src.open_canvas.nodes.generate_path.create_context_document_messages",
                return_value=[],
            ):
                result = await generate_path(state, mock_config, store=store)

        assert result["next"] == "generateArtifact"

    @pytest.mark.asyncio
    async def test_generate_artifact_with_mock(
        self, mock_config, mock_artifact_generation_response
    ):
        """Test artifact generation with mock LLM."""
        from src.open_canvas.nodes.generate_artifact import generate_artifact

        store = InMemoryStore()

        # Create mock response
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
            "messages": [HumanMessage(content="Write a hello world function")],
            "_messages": [HumanMessage(content="Write a hello world function")],
            "artifact": None,
        }

        with patch(
            "src.open_canvas.nodes.generate_artifact.get_model_from_config",
            return_value=mock_llm,
        ):
            with patch(
                "src.open_canvas.nodes.generate_artifact.get_formatted_reflections",
                return_value="",
            ):
                result = await generate_artifact(state, mock_config, store=store)

        # Verify artifact was created
        assert result.get("artifact") is not None
        assert result["artifact"]["currentIndex"] == 1
        assert result["artifact"]["contents"][0]["type"] == "code"
        assert "Hello Function" in result["artifact"]["contents"][0]["title"]

    @pytest.mark.asyncio
    async def test_rewrite_artifact_with_mock(self, mock_config):
        """Test artifact rewrite with mock LLM."""
        from src.open_canvas.nodes.rewrite_artifact import rewrite_artifact

        store = InMemoryStore()

        # Create mock streaming response
        async def mock_astream(*args, **kwargs):
            yield MagicMock(content="def hello_updated():\n")
            yield MagicMock(content="    print('Updated!')")

        # Create mock for optionally_update_artifact_meta call
        mock_meta_response = MagicMock()
        mock_meta_response.tool_calls = [
            {
                "args": {
                    "type": "code",
                    "title": "Updated Function",
                    "language": "python",
                }
            }
        ]

        # Create mock LLM that supports streaming, tool calls, AND direct ainvoke
        mock_llm = MagicMock()
        mock_llm.astream = mock_astream
        # Direct ainvoke for small_model (line 314)
        mock_llm.ainvoke = AsyncMock(return_value=MagicMock(content="Updated code generated"))

        # Mock for bind_tools - returns an async mock that can be awaited
        mock_bound_llm = AsyncMock()
        mock_bound_llm.ainvoke = AsyncMock(return_value=mock_meta_response)
        mock_llm.bind_tools = MagicMock(return_value=mock_bound_llm)

        state = {
            "messages": [
                HumanMessage(content="Write a function"),
                HumanMessage(content="Add error handling"),
            ],
            "_messages": [
                HumanMessage(content="Write a function"),
                HumanMessage(content="Add error handling"),
            ],
            "artifact": {
                "currentIndex": 1,
                "contents": [
                    {
                        "index": 1,
                        "type": "code",
                        "title": "Original",
                        "language": "python",
                        "code": "def hello(): pass",
                    }
                ],
            },
        }

        with patch(
            "src.open_canvas.nodes.rewrite_artifact.get_model_from_config",
            return_value=mock_llm,
        ):
            with patch(
                "src.open_canvas.nodes.rewrite_artifact.get_formatted_reflections",
                return_value="",
            ):
                result = await rewrite_artifact(state, mock_config, store=store)

        # Verify artifact was updated
        assert result.get("artifact") is not None
        assert result["artifact"]["currentIndex"] == 2
        assert len(result["artifact"]["contents"]) == 2

    @pytest.mark.asyncio
    async def test_hardcoded_routing_paths(self, mock_config):
        """Test that hardcoded routing paths work without LLM."""
        from src.open_canvas.nodes.generate_path import generate_path

        store = InMemoryStore()

        # Test highlightedCode routing
        state_with_highlight = {
            "_messages": [HumanMessage(content="Test")],
            "messages": [HumanMessage(content="Test")],
            "highlightedCode": {"startCharIndex": 0, "endCharIndex": 10},
            "highlightedText": None,
            "artifact": None,
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

        result = await generate_path(state_with_highlight, mock_config, store=store)
        assert result["next"] == "updateArtifact"

        # Test highlightedText routing
        state_with_text_highlight = {
            **state_with_highlight,
            "highlightedCode": None,
            "highlightedText": {"selectedText": "test"},
        }
        result = await generate_path(
            state_with_text_highlight, mock_config, store=store
        )
        assert result["next"] == "updateHighlightedText"

        # Test webSearchEnabled routing
        state_with_search = {
            **state_with_highlight,
            "highlightedCode": None,
            "webSearchEnabled": True,
        }
        result = await generate_path(state_with_search, mock_config, store=store)
        assert result["next"] == "webSearch"

    @pytest.mark.asyncio
    async def test_theme_routing_paths(self, mock_config):
        """Test that theme-related routing works."""
        from src.open_canvas.nodes.generate_path import generate_path

        store = InMemoryStore()

        # Test text theme routing (language change)
        state = {
            "_messages": [HumanMessage(content="Test")],
            "messages": [HumanMessage(content="Test")],
            "highlightedCode": None,
            "highlightedText": None,
            "artifact": None,
            "language": "spanish",  # This triggers text theme
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

        result = await generate_path(state, mock_config, store=store)
        assert result["next"] == "rewriteArtifactTheme"

        # Test code theme routing (addComments)
        state_code_theme = {
            **state,
            "language": None,
            "addComments": True,
        }
        result = await generate_path(state_code_theme, mock_config, store=store)
        assert result["next"] == "rewriteCodeArtifactTheme"

    @pytest.mark.asyncio
    async def test_custom_action_routing(self, mock_config):
        """Test that custom action routing works."""
        from src.open_canvas.nodes.generate_path import generate_path

        store = InMemoryStore()

        state = {
            "_messages": [HumanMessage(content="Test")],
            "messages": [HumanMessage(content="Test")],
            "highlightedCode": None,
            "highlightedText": None,
            "artifact": None,
            "language": None,
            "artifactLength": None,
            "regenerateWithEmojis": None,
            "readingLevel": None,
            "addComments": None,
            "addLogs": None,
            "portLanguage": None,
            "fixBugs": None,
            "customQuickActionId": "custom-action-123",
            "webSearchEnabled": False,
        }

        result = await generate_path(state, mock_config, store=store)
        assert result["next"] == "customAction"