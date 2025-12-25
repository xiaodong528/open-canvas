"""
Pytest configuration and shared fixtures for Open Canvas Python agent tests.
"""

import pytest
import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock

from langchain_core.messages import HumanMessage, AIMessage
from langgraph.store.memory import InMemoryStore


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_store() -> InMemoryStore:
    """Create an in-memory store for testing."""
    return InMemoryStore()


@pytest.fixture
def mock_config() -> dict[str, Any]:
    """Create a test configuration."""
    return {
        "configurable": {
            "customModelName": "gpt-4o-mini",
            "supabase_user_id": "test-user-id",
            "supabase_session": {"access_token": "test-token"},
            "thread_id": "test-thread-id",
            "assistant_id": "test-assistant-id",
        }
    }


@pytest.fixture
def sample_human_message() -> HumanMessage:
    """Create a sample human message."""
    return HumanMessage(content="Write a Python function to calculate fibonacci")


@pytest.fixture
def sample_messages(sample_human_message) -> list:
    """Create sample message history."""
    return [sample_human_message]


@pytest.fixture
def sample_artifact() -> dict[str, Any]:
    """Create a sample artifact for testing."""
    return {
        "currentIndex": 1,
        "contents": [
            {
                "index": 1,
                "type": "code",
                "title": "Fibonacci Calculator",
                "language": "python",
                "code": "def fibonacci(n):\n    if n <= 1:\n        return n\n    return fibonacci(n-1) + fibonacci(n-2)",
            }
        ],
    }


@pytest.fixture
def sample_code_artifact() -> dict[str, Any]:
    """Create a sample code artifact."""
    return {
        "currentIndex": 1,
        "contents": [
            {
                "index": 1,
                "type": "code",
                "title": "Sample Code",
                "language": "python",
                "code": "def hello():\n    return 'Hello, World!'",
            }
        ],
    }


@pytest.fixture
def sample_text_artifact() -> dict[str, Any]:
    """Create a sample text/markdown artifact."""
    return {
        "currentIndex": 1,
        "contents": [
            {
                "index": 1,
                "type": "text",
                "title": "Sample Document",
                "fullMarkdown": "# Hello World\n\nThis is a sample document.",
            }
        ],
    }


@pytest.fixture
def sample_state(sample_messages, sample_artifact) -> dict[str, Any]:
    """Create a complete sample state for testing."""
    return {
        "messages": sample_messages,
        "_messages": sample_messages,
        "artifact": sample_artifact,
        "next": None,
        "highlightedCode": None,
        "highlightedText": None,
        "language": None,
        "artifactLength": None,
        "regenerateWithEmojis": None,
        "readingLevel": None,
        "addComments": None,
        "addLogs": None,
        "fixBugs": None,
        "portLanguage": None,
        "customQuickActionId": None,
        "webSearchEnabled": False,
        "webSearchResults": [],
    }


@pytest.fixture
def empty_state() -> dict[str, Any]:
    """Create an empty state for testing new artifact generation."""
    return {
        "messages": [HumanMessage(content="Write a hello world function")],
        "_messages": [HumanMessage(content="Write a hello world function")],
        "artifact": None,
        "next": None,
    }


# Mock fixtures for LLM responses


@pytest.fixture
def mock_route_response():
    """Create a mock for routing decisions.

    Note: The RouteQuerySchema in generate_path.py uses 'route' field,
    not 'next'. This matches the actual LLM tool response format.
    """

    def _create_mock(route: str):
        mock = MagicMock()
        mock.tool_calls = [{"args": {"route": route}}]
        return mock

    return _create_mock


@pytest.fixture
def mock_artifact_response():
    """Create a mock for artifact generation."""

    def _create_mock(code: str, title: str, language: str = "python"):
        mock = MagicMock()
        mock.tool_calls = [
            {
                "args": {
                    "artifact": code,
                    "title": title,
                    "type": "code",
                    "language": language,
                }
            }
        ]
        return mock

    return _create_mock


@pytest.fixture
def mock_llm():
    """Create a mock LLM that can be configured."""
    mock = AsyncMock()
    mock.bind_tools = MagicMock(return_value=mock)
    mock.with_structured_output = MagicMock(return_value=mock)
    return mock


# ============================================
# Enhanced mock fixtures for functional testing
# ============================================


@pytest.fixture
def mock_model_response():
    """Factory for creating mock LLM responses with tool calls.

    Usage:
        response = mock_model_response(
            tool_calls=[{"args": {"next": "generateArtifact"}}],
            content="I'll create an artifact for you."
        )
    """

    def _create_response(
        tool_calls: list[dict] = None,
        content: str = "",
        additional_kwargs: dict = None,
    ):
        mock = MagicMock()
        mock.tool_calls = tool_calls or []
        mock.content = content
        mock.additional_kwargs = additional_kwargs or {}
        return mock

    return _create_response


@pytest.fixture
def mock_streaming_response():
    """Factory for creating mock streaming LLM responses.

    Simulates async iterator for streaming responses.

    Usage:
        async for chunk in mock_streaming_response(["Hello", " ", "World"]):
            print(chunk.content)
    """

    def _create_streaming(chunks: list[str]):
        async def async_generator():
            for chunk in chunks:
                mock_chunk = MagicMock()
                mock_chunk.content = chunk
                yield mock_chunk

        return async_generator()

    return _create_streaming


@pytest.fixture
def mock_reflection_store(mock_store):
    """Pre-populated store with reflections for testing.

    Returns:
        InMemoryStore with sample reflection data
    """
    import asyncio

    async def setup_store():
        await mock_store.aput(
            ("memories", "test-assistant-id"),
            "reflection",
            {
                "styleRules": ["Use concise language", "Prefer bullet points"],
                "content": ["User prefers Python", "User works in data science"],
            },
        )
        return mock_store

    # Run setup synchronously for fixture
    loop = asyncio.get_event_loop_policy().new_event_loop()
    try:
        loop.run_until_complete(setup_store())
    finally:
        loop.close()

    return mock_store


@pytest.fixture
def mock_llm_with_tool_response(mock_route_response):
    """Create a mock LLM that returns a specific routing decision.

    Usage:
        llm = mock_llm_with_tool_response("generateArtifact")
        result = await llm.ainvoke(messages)
        assert result.tool_calls[0]["args"]["next"] == "generateArtifact"
    """

    def _create_llm(next_node: str):
        mock = AsyncMock()
        mock.ainvoke = AsyncMock(return_value=mock_route_response(next_node))
        mock.bind_tools = MagicMock(return_value=mock)
        mock.with_structured_output = MagicMock(return_value=mock)
        return mock

    return _create_llm


@pytest.fixture
def mock_artifact_generation_response():
    """Factory for creating mock artifact generation responses.

    Usage:
        response = mock_artifact_generation_response(
            code="print('hello')",
            title="Hello World",
            artifact_type="code",
            language="python"
        )
    """

    def _create_response(
        code: str = "",
        full_markdown: str = "",
        title: str = "Untitled",
        artifact_type: str = "code",
        language: str = "python",
    ):
        mock = MagicMock()

        if artifact_type == "code":
            mock.tool_calls = [
                {
                    "args": {
                        "artifact": code,
                        "title": title,
                        "type": artifact_type,
                        "language": language,
                    }
                }
            ]
        else:
            mock.tool_calls = [
                {
                    "args": {
                        "artifact": full_markdown,
                        "title": title,
                        "type": artifact_type,
                    }
                }
            ]

        mock.content = f"Created {artifact_type} artifact: {title}"
        return mock

    return _create_response


@pytest.fixture
def sample_web_search_results() -> list[dict[str, Any]]:
    """Sample web search results matching SearchResult structure."""
    return [
        {
            "pageContent": "Python is a high-level programming language.",
            "metadata": {
                "id": "result-1",
                "url": "https://python.org",
                "title": "Python Official Website",
                "author": "Python Foundation",
                "publishedDate": "2024-01-01",
                "image": None,
                "favicon": "https://python.org/favicon.ico",
            },
        },
        {
            "pageContent": "Learn Python programming with tutorials.",
            "metadata": {
                "id": "result-2",
                "url": "https://realpython.com",
                "title": "Real Python Tutorials",
                "author": "Real Python Team",
                "publishedDate": "2024-06-15",
                "image": None,
                "favicon": "https://realpython.com/favicon.ico",
            },
        },
    ]


@pytest.fixture
def sample_code_highlight() -> dict[str, Any]:
    """Sample code highlight for testing update_artifact."""
    return {
        "startCharIndex": 0,
        "endCharIndex": 20,
        "selectedText": "def fibonacci(n):",
    }


@pytest.fixture
def sample_text_highlight() -> dict[str, Any]:
    """Sample text highlight for testing update_highlighted_text."""
    return {
        "fullMarkdown": "# Hello World\n\nThis is a sample document.",
        "markdownBlock": "This is a sample document.",
        "selectedText": "sample",
    }


@pytest.fixture
def state_with_code_highlight(sample_state, sample_code_highlight) -> dict[str, Any]:
    """State with code highlight for testing update_artifact."""
    return {
        **sample_state,
        "highlightedCode": sample_code_highlight,
    }


@pytest.fixture
def state_with_text_highlight(sample_text_artifact, sample_text_highlight) -> dict[str, Any]:
    """State with text highlight for testing update_highlighted_text."""
    return {
        "messages": [HumanMessage(content="Update the highlighted text")],
        "_messages": [HumanMessage(content="Update the highlighted text")],
        "artifact": sample_text_artifact,
        "highlightedText": sample_text_highlight,
        "highlightedCode": None,
        "next": None,
    }


# ============================================
# Config variants for different model providers
# ============================================


@pytest.fixture
def openai_config() -> dict[str, Any]:
    """Config for OpenAI models."""
    return {
        "configurable": {
            "customModelName": "gpt-4o",
            "assistant_id": "test-assistant-id",
            "thread_id": "test-thread-id",
        }
    }


@pytest.fixture
def anthropic_config() -> dict[str, Any]:
    """Config for Anthropic models."""
    return {
        "configurable": {
            "customModelName": "claude-3-5-sonnet-20241022",
            "assistant_id": "test-assistant-id",
            "thread_id": "test-thread-id",
        }
    }


@pytest.fixture
def gemini_config() -> dict[str, Any]:
    """Config for Gemini models."""
    return {
        "configurable": {
            "customModelName": "gemini-2.0-flash-exp",
            "assistant_id": "test-assistant-id",
            "thread_id": "test-thread-id",
        }
    }


# Markers for test categorization


def pytest_configure(config):
    """Configure custom pytest markers."""
    config.addinivalue_line("markers", "unit: mark test as unit test")
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "slow: mark test as slow (requires API calls)")
    config.addinivalue_line("markers", "requires_api: mark test as requiring API keys")
