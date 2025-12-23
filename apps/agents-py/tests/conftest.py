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
    """Create a mock for routing decisions."""

    def _create_mock(next_node: str):
        mock = MagicMock()
        mock.tool_calls = [{"args": {"next": next_node}}]
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


# Markers for test categorization


def pytest_configure(config):
    """Configure custom pytest markers."""
    config.addinivalue_line("markers", "unit: mark test as unit test")
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "slow: mark test as slow (requires API calls)")
    config.addinivalue_line("markers", "requires_api: mark test as requiring API keys")
