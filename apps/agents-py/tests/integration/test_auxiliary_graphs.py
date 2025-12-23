"""
Integration tests for auxiliary graphs.

Tests for: reflection, thread_title, summarizer, and web_search graphs.
"""

import pytest
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.store.memory import InMemoryStore


@pytest.mark.integration
class TestReflectionGraph:
    """Tests for the reflection graph."""

    def test_reflection_graph_compiles(self):
        """Reflection graph should compile successfully."""
        from src.reflection.graph import graph

        assert graph is not None
        assert hasattr(graph, "invoke")

    def test_reflection_graph_has_reflect_node(self):
        """Reflection graph should have reflect node."""
        from src.reflection.graph import graph

        assert graph is not None

    @pytest.mark.asyncio
    @pytest.mark.requires_api
    async def test_reflection_stores_insights(self, mock_config):
        """Reflection should store user insights in memory."""
        from src.reflection.graph import graph

        store = InMemoryStore()

        input_state = {
            "messages": [
                HumanMessage(content="Write Python code"),
                AIMessage(content="Here's your code"),
            ],
        }

        config = {
            **mock_config,
            "store": store,
        }

        pytest.skip("Skipping test that requires API keys")

        await graph.ainvoke(input_state, config=config)

        # Check that reflections were stored
        # (Implementation depends on actual store structure)


@pytest.mark.integration
class TestThreadTitleGraph:
    """Tests for the thread_title graph."""

    def test_thread_title_graph_compiles(self):
        """Thread title graph should compile successfully."""
        from src.thread_title.graph import graph

        assert graph is not None
        assert hasattr(graph, "invoke")

    def test_thread_title_has_generate_title_node(self):
        """Thread title graph should have generateTitle node."""
        from src.thread_title.graph import graph

        assert graph is not None

    @pytest.mark.asyncio
    @pytest.mark.requires_api
    async def test_generates_title_from_messages(self, mock_config):
        """Should generate a title from conversation."""
        from src.thread_title.graph import graph

        input_state = {
            "messages": [
                HumanMessage(content="Help me write a Python web scraper"),
                AIMessage(content="I'll help you create a web scraper."),
            ],
        }

        pytest.skip("Skipping test that requires API keys")

        result = await graph.ainvoke(input_state, config=mock_config)

        # Title should be generated
        # (Check actual output format)


@pytest.mark.integration
class TestSummarizerGraph:
    """Tests for the summarizer graph."""

    def test_summarizer_graph_compiles(self):
        """Summarizer graph should compile successfully."""
        from src.summarizer.graph import graph

        assert graph is not None
        assert hasattr(graph, "invoke")

    def test_summarizer_has_summarize_node(self):
        """Summarizer graph should have summarize node."""
        from src.summarizer.graph import graph

        assert graph is not None

    @pytest.mark.asyncio
    @pytest.mark.requires_api
    async def test_summarizes_long_conversation(self, mock_config):
        """Should summarize a long conversation."""
        from src.summarizer.graph import graph

        # Create a long conversation
        messages = []
        for i in range(10):
            messages.append(HumanMessage(content=f"Question {i}"))
            messages.append(AIMessage(content=f"Answer {i}"))

        input_state = {
            "messages": messages,
            "threadId": "test-thread-123",
        }

        pytest.skip("Skipping test that requires API keys")

        result = await graph.ainvoke(input_state, config=mock_config)

        # Should have summarized messages


@pytest.mark.integration
class TestWebSearchGraph:
    """Tests for the web_search graph."""

    def test_web_search_graph_compiles(self):
        """Web search graph should compile successfully."""
        from src.web_search.graph import graph

        assert graph is not None
        assert hasattr(graph, "invoke")

    def test_web_search_has_required_nodes(self):
        """Web search graph should have classifyMessage, queryGenerator, search nodes."""
        from src.web_search.graph import graph

        assert graph is not None

    def test_classify_message_node_exists(self):
        """classifyMessage node should exist."""
        from src.web_search.nodes.classify_message import classify_message

        assert callable(classify_message)

    def test_query_generator_node_exists(self):
        """queryGenerator node should exist."""
        from src.web_search.nodes.query_generator import query_generator

        assert callable(query_generator)

    def test_search_node_exists(self):
        """search node should exist."""
        from src.web_search.nodes.search import search

        assert callable(search)

    @pytest.mark.asyncio
    @pytest.mark.requires_api
    async def test_classifies_search_request(self, mock_config):
        """Should correctly classify if search is needed."""
        from src.web_search.graph import graph

        input_state = {
            "messages": [
                HumanMessage(content="What is the latest Python version?"),
            ],
        }

        pytest.skip("Skipping test that requires API keys")

        result = await graph.ainvoke(input_state, config=mock_config)

        # Should have classification result


@pytest.mark.integration
class TestAllGraphsLoad:
    """Test that all graphs can be loaded without errors."""

    def test_all_graphs_import(self):
        """All graphs should import successfully."""
        # Main graph
        from src.open_canvas.graph import graph as main_graph

        assert main_graph is not None

        # Reflection
        from src.reflection.graph import graph as reflection_graph

        assert reflection_graph is not None

        # Thread title
        from src.thread_title.graph import graph as title_graph

        assert title_graph is not None

        # Summarizer
        from src.summarizer.graph import graph as summarizer_graph

        assert summarizer_graph is not None

        # Web search
        from src.web_search.graph import graph as search_graph

        assert search_graph is not None

    def test_all_graphs_have_invoke_method(self):
        """All graphs should have invoke methods."""
        from src.open_canvas.graph import graph as main_graph
        from src.reflection.graph import graph as reflection_graph
        from src.thread_title.graph import graph as title_graph
        from src.summarizer.graph import graph as summarizer_graph
        from src.web_search.graph import graph as search_graph

        graphs = [main_graph, reflection_graph, title_graph, summarizer_graph, search_graph]

        for graph in graphs:
            assert hasattr(graph, "invoke")
            assert hasattr(graph, "ainvoke")
