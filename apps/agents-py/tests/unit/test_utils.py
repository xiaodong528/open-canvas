"""
Unit tests for the core utility functions in src/utils.py

Tests cover:
- Model configuration parsing for 7 LLM providers
- Reflection formatting
- Artifact content handling
- Thinking model utilities
- Message formatting
"""

import os
from unittest.mock import MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from src.constants import OC_SUMMARIZED_MESSAGE_KEY, OC_WEB_SEARCH_RESULTS_MESSAGE_KEY


# ============================================
# Tests for get_model_config()
# ============================================


@pytest.mark.unit
class TestGetModelConfig:
    """Tests for model configuration parsing across different providers."""

    def test_openai_model_config(self):
        """OpenAI model config should return correct provider and model name."""
        from src.utils import get_model_config

        config = {"configurable": {"customModelName": "gpt-4o"}}
        result = get_model_config(config)

        assert result["modelProvider"] == "openai"
        assert result["modelName"] == "gpt-4o"

    def test_openai_reasoning_model_config(self):
        """OpenAI reasoning models (o1, o3, o4) should be detected correctly."""
        from src.utils import get_model_config

        # Test o1 model
        config = {"configurable": {"customModelName": "o1-mini"}}
        result = get_model_config(config)
        assert result["modelProvider"] == "openai"
        assert result["modelName"] == "o1-mini"

        # Test o3 model
        config = {"configurable": {"customModelName": "o3-mini"}}
        result = get_model_config(config)
        assert result["modelProvider"] == "openai"
        assert result["modelName"] == "o3-mini"

        # Test o4 model
        config = {"configurable": {"customModelName": "o4-mini"}}
        result = get_model_config(config)
        assert result["modelProvider"] == "openai"
        assert result["modelName"] == "o4-mini"

    def test_openai_tool_calling_swaps_o1_to_gpt4o(self):
        """When is_tool_calling=True, o1 models should swap to gpt-4o."""
        from src.utils import get_model_config

        config = {"configurable": {"customModelName": "o1-mini"}}
        result = get_model_config(config, is_tool_calling=True)

        assert result["modelName"] == "gpt-4o"
        assert result["modelProvider"] == "openai"

    def test_anthropic_model_config(self):
        """Anthropic model config should return correct provider."""
        from src.utils import get_model_config

        config = {"configurable": {"customModelName": "claude-3-5-sonnet-20241022"}}
        result = get_model_config(config)

        assert result["modelProvider"] == "anthropic"
        assert result["modelName"] == "claude-3-5-sonnet-20241022"

    def test_anthropic_claude4_config(self):
        """Claude 4 series should be detected as Anthropic."""
        from src.utils import get_model_config

        config = {"configurable": {"customModelName": "claude-sonnet-4-20250514"}}
        result = get_model_config(config)

        assert result["modelProvider"] == "anthropic"
        assert result["modelName"] == "claude-sonnet-4-20250514"

    def test_gemini_model_config(self):
        """Gemini model config should return google-genai provider."""
        from src.utils import get_model_config

        config = {"configurable": {"customModelName": "gemini-2.0-flash-exp"}}
        result = get_model_config(config)

        assert result["modelProvider"] == "google-genai"
        assert result["modelName"] == "gemini-2.0-flash-exp"

    def test_gemini_thinking_model_tool_calling(self):
        """Gemini thinking models should swap to flash-exp for tool calling."""
        from src.utils import get_model_config

        config = {"configurable": {"customModelName": "gemini-2.0-flash-thinking-exp"}}
        result = get_model_config(config, is_tool_calling=True)

        assert result["modelName"] == "gemini-2.0-flash-exp"
        assert result["modelProvider"] == "google-genai"

    def test_fireworks_model_config(self):
        """Fireworks model config should detect 'fireworks/' in model name."""
        from src.utils import get_model_config

        config = {
            "configurable": {
                "customModelName": "accounts/fireworks/models/llama-v3p3-70b-instruct"
            }
        }
        result = get_model_config(config)

        assert result["modelProvider"] == "fireworks"
        assert result["modelName"] == "accounts/fireworks/models/llama-v3p3-70b-instruct"

    def test_fireworks_tool_calling_swaps_model(self):
        """Non-llama Fireworks models should swap to llama for tool calling."""
        from src.utils import get_model_config

        config = {
            "configurable": {"customModelName": "accounts/fireworks/models/some-other-model"}
        }
        result = get_model_config(config, is_tool_calling=True)

        assert result["modelName"] == "accounts/fireworks/models/llama-v3p3-70b-instruct"

    @patch.dict(
        os.environ,
        {
            "_AZURE_OPENAI_API_KEY": "test-key",
            "_AZURE_OPENAI_API_INSTANCE_NAME": "test-instance",
            "_AZURE_OPENAI_API_DEPLOYMENT_NAME": "test-deployment",
        },
    )
    def test_azure_openai_model_config(self):
        """Azure OpenAI model config should parse azure/ prefix correctly."""
        from src.utils import get_model_config

        config = {"configurable": {"customModelName": "azure/gpt-4"}}
        result = get_model_config(config)

        assert result["modelProvider"] == "azure_openai"
        assert result["modelName"] == "gpt-4"
        assert "azureConfig" in result
        assert result["azureConfig"]["azureOpenAIApiKey"] == "test-key"

    def test_groq_model_config(self):
        """Groq model config should parse groq/ prefix correctly."""
        from src.utils import get_model_config

        config = {"configurable": {"customModelName": "groq/llama-3.1-70b"}}
        result = get_model_config(config)

        assert result["modelProvider"] == "groq"
        assert result["modelName"] == "llama-3.1-70b"

    def test_ollama_model_config(self):
        """Ollama model config should parse ollama- prefix correctly."""
        from src.utils import get_model_config

        config = {"configurable": {"customModelName": "ollama-llama3"}}
        result = get_model_config(config)

        assert result["modelProvider"] == "ollama"
        assert result["modelName"] == "llama3"

    def test_missing_model_name_raises_error(self):
        """Missing model name should raise ValueError."""
        from src.utils import get_model_config

        config = {"configurable": {}}

        with pytest.raises(ValueError, match="Model name is missing"):
            get_model_config(config)

    def test_unknown_provider_raises_error(self):
        """Unknown model provider should raise ValueError."""
        from src.utils import get_model_config

        config = {"configurable": {"customModelName": "unknown-provider-model"}}

        with pytest.raises(ValueError, match="Unknown model provider"):
            get_model_config(config)


# ============================================
# Tests for format_reflections()
# ============================================


@pytest.mark.unit
class TestFormatReflections:
    """Tests for reflection formatting."""

    def test_format_empty_reflections(self):
        """Empty reflections should return default messages."""
        from src.utils import format_reflections

        reflections = {}
        result = format_reflections(reflections)

        assert "No style guidelines found" in result
        assert "No memories/facts found" in result

    def test_format_with_style_rules(self):
        """Reflections with style rules should format correctly."""
        from src.utils import format_reflections

        reflections = {"styleRules": ["Use concise language", "Prefer bullet points"]}
        result = format_reflections(reflections)

        assert "Use concise language" in result
        assert "Prefer bullet points" in result
        assert "<style-guidelines>" in result

    def test_format_with_user_facts(self):
        """Reflections with user facts should format correctly."""
        from src.utils import format_reflections

        reflections = {
            "content": ["User prefers Python", "User works in data science"]
        }
        result = format_reflections(reflections)

        assert "User prefers Python" in result
        assert "User works in data science" in result
        assert "<user-facts>" in result

    def test_format_only_style(self):
        """only_style=True should return only style guidelines."""
        from src.utils import format_reflections

        reflections = {
            "styleRules": ["Be concise"],
            "content": ["User fact"],
        }
        result = format_reflections(reflections, only_style=True)

        assert "Be concise" in result
        assert "User fact" not in result

    def test_format_only_content(self):
        """only_content=True should return only user facts."""
        from src.utils import format_reflections

        reflections = {
            "styleRules": ["Be concise"],
            "content": ["User fact"],
        }
        result = format_reflections(reflections, only_content=True)

        assert "Be concise" not in result
        assert "User fact" in result

    def test_format_both_flags_raises_error(self):
        """Setting both only_style and only_content should raise error."""
        from src.utils import format_reflections

        reflections = {}

        with pytest.raises(ValueError, match="Cannot specify both"):
            format_reflections(reflections, only_style=True, only_content=True)

    def test_format_json_string_style_rules(self):
        """Style rules as JSON string should be parsed correctly."""
        from src.utils import format_reflections

        reflections = {"styleRules": '["Rule 1", "Rule 2"]'}
        result = format_reflections(reflections)

        assert "Rule 1" in result
        assert "Rule 2" in result

    def test_format_invalid_json_string(self):
        """Invalid JSON string should be handled gracefully."""
        from src.utils import format_reflections

        reflections = {"styleRules": "not valid json"}
        result = format_reflections(reflections)

        assert "No style guidelines found" in result


# ============================================
# Tests for artifact helpers
# ============================================


@pytest.mark.unit
class TestArtifactHelpers:
    """Tests for artifact content handling functions."""

    def test_is_artifact_code_content_true(self):
        """Code artifacts should be identified correctly."""
        from src.utils import is_artifact_code_content

        content = {"type": "code", "code": "print('hello')"}
        assert is_artifact_code_content(content) is True

    def test_is_artifact_code_content_false(self):
        """Text/markdown artifacts should return False."""
        from src.utils import is_artifact_code_content

        content = {"type": "text", "fullMarkdown": "# Hello"}
        assert is_artifact_code_content(content) is False

    def test_format_artifact_content_code(self):
        """Code artifact formatting should include code content."""
        from src.utils import format_artifact_content

        content = {
            "type": "code",
            "title": "Hello World",
            "code": "print('hello world')",
        }
        result = format_artifact_content(content)

        assert "Title: Hello World" in result
        assert "Artifact type: code" in result
        assert "print('hello world')" in result

    def test_format_artifact_content_text(self):
        """Text artifact formatting should include markdown content."""
        from src.utils import format_artifact_content

        content = {
            "type": "text",
            "title": "My Document",
            "fullMarkdown": "# Hello\n\nWorld",
        }
        result = format_artifact_content(content)

        assert "Title: My Document" in result
        assert "Artifact type: text" in result
        assert "# Hello" in result

    def test_format_artifact_content_shortened(self):
        """Shortened content should be truncated to 500 chars."""
        from src.utils import format_artifact_content

        content = {
            "type": "code",
            "title": "Long Code",
            "code": "x" * 1000,
        }
        result = format_artifact_content(content, shorten_content=True)

        # Should be truncated - check that full content is not present
        assert "x" * 1000 not in result
        assert "x" * 500 in result

    def test_format_artifact_content_with_template(self):
        """Template formatting should replace {artifact} placeholder."""
        from src.utils import format_artifact_content_with_template

        template = "Here is the artifact:\n{artifact}\n\nPlease review."
        content = {"type": "code", "title": "Test", "code": "pass"}

        result = format_artifact_content_with_template(template, content)

        assert "Here is the artifact:" in result
        assert "Please review." in result
        assert "Title: Test" in result


# ============================================
# Tests for thinking model utilities
# ============================================


@pytest.mark.unit
class TestThinkingModels:
    """Tests for thinking model detection and response parsing."""

    def test_is_thinking_model_true(self):
        """Known thinking models should be detected."""
        from src.utils import is_thinking_model

        assert is_thinking_model("accounts/fireworks/models/deepseek-r1") is True
        assert is_thinking_model("groq/deepseek-r1-distill-llama-70b") is True

    def test_is_thinking_model_false(self):
        """Regular models should not be detected as thinking models."""
        from src.utils import is_thinking_model

        assert is_thinking_model("gpt-4o") is False
        assert is_thinking_model("claude-3-5-sonnet-20241022") is False

    def test_extract_thinking_and_response_with_tags(self):
        """Should extract thinking content from <think> tags."""
        from src.utils import extract_thinking_and_response

        text = "Hello <think>processing...</think>world"
        thinking, response = extract_thinking_and_response(text)

        assert thinking == "processing..."
        assert response == "Hello world"

    def test_extract_thinking_and_response_no_end_tag(self):
        """Should handle streaming case without closing tag."""
        from src.utils import extract_thinking_and_response

        text = "Hello <think>still thinking..."
        thinking, response = extract_thinking_and_response(text)

        assert thinking == "still thinking..."
        assert response == "Hello"

    def test_extract_thinking_and_response_no_tags(self):
        """Should return empty thinking for text without tags."""
        from src.utils import extract_thinking_and_response

        text = "Just a regular response"
        thinking, response = extract_thinking_and_response(text)

        assert thinking == ""
        assert response == "Just a regular response"


# ============================================
# Tests for message formatting
# ============================================


@pytest.mark.unit
class TestMessageFormatting:
    """Tests for message formatting utilities."""

    def test_format_messages(self):
        """Messages should be formatted as XML."""
        from src.utils import format_messages

        messages = [
            HumanMessage(content="Hello"),
            AIMessage(content="Hi there!"),
        ]
        result = format_messages(messages)

        assert '<human index="0">' in result
        assert "Hello" in result
        assert '<ai index="1">' in result
        assert "Hi there!" in result

    def test_get_string_from_content_string(self):
        """String content should be returned as-is."""
        from src.utils import get_string_from_content

        result = get_string_from_content("Hello world")
        assert result == "Hello world"

    def test_get_string_from_content_list(self):
        """List content should extract text from dicts."""
        from src.utils import get_string_from_content

        content = [{"type": "text", "text": "Hello"}, {"type": "text", "text": "World"}]
        result = get_string_from_content(content)

        assert "Hello" in result
        assert "World" in result


# ============================================
# Tests for web search result processing
# ============================================


@pytest.mark.unit
class TestWebSearchResults:
    """Tests for web search result message creation."""

    def test_create_ai_message_from_web_results(self):
        """Should create AIMessage with web search results."""
        from src.utils import create_ai_message_from_web_results

        web_results = [
            {
                "pageContent": "Python is a programming language",
                "metadata": {
                    "id": "1",
                    "url": "https://python.org",
                    "title": "Python Official",
                    "author": "Python Foundation",
                    "publishedDate": "2024-01-01",
                },
            }
        ]
        result = create_ai_message_from_web_results(web_results)

        assert isinstance(result, AIMessage)
        assert "Python is a programming language" in result.content
        assert "https://python.org" in result.content
        assert result.additional_kwargs.get(OC_WEB_SEARCH_RESULTS_MESSAGE_KEY) is True

    def test_create_ai_message_with_multiple_results(self):
        """Should handle multiple search results."""
        from src.utils import create_ai_message_from_web_results

        web_results = [
            {
                "pageContent": "Result 1",
                "metadata": {"id": "1", "url": "https://a.com", "title": "A"},
            },
            {
                "pageContent": "Result 2",
                "metadata": {"id": "2", "url": "https://b.com", "title": "B"},
            },
        ]
        result = create_ai_message_from_web_results(web_results)

        assert "Result 1" in result.content
        assert "Result 2" in result.content
        assert 'index="0"' in result.content
        assert 'index="1"' in result.content


# ============================================
# Tests for base64 and PDF utilities
# ============================================


@pytest.mark.unit
class TestBase64Utilities:
    """Tests for base64 and PDF processing utilities."""

    def test_clean_base64_with_prefix(self):
        """Should remove data URL prefix."""
        from src.utils import clean_base64

        data = "data:application/pdf;base64,SGVsbG8gV29ybGQ="
        result = clean_base64(data)

        assert result == "SGVsbG8gV29ybGQ="

    def test_clean_base64_without_prefix(self):
        """Should return raw base64 unchanged."""
        from src.utils import clean_base64

        data = "SGVsbG8gV29ybGQ="
        result = clean_base64(data)

        assert result == "SGVsbG8gV29ybGQ="


# ============================================
# Tests for ensure_store_in_config
# ============================================


@pytest.mark.unit
class TestEnsureStoreInConfig:
    """Tests for store configuration validation."""

    def test_ensure_store_present(self):
        """Should return store when present in config."""
        from src.utils import ensure_store_in_config

        mock_store = MagicMock()
        config = {"store": mock_store}

        result = ensure_store_in_config(config)
        assert result is mock_store

    def test_ensure_store_missing_raises_error(self):
        """Should raise error when store is missing."""
        from src.utils import ensure_store_in_config

        config = {}

        with pytest.raises(ValueError, match="store.*not found"):
            ensure_store_in_config(config)


# ============================================
# Tests for optionally_get_system_prompt_from_config
# ============================================


@pytest.mark.unit
class TestSystemPrompt:
    """Tests for system prompt retrieval."""

    def test_get_system_prompt_present(self):
        """Should return system prompt when present."""
        from src.utils import optionally_get_system_prompt_from_config

        config = {"configurable": {"systemPrompt": "You are a helpful assistant."}}
        result = optionally_get_system_prompt_from_config(config)

        assert result == "You are a helpful assistant."

    def test_get_system_prompt_missing(self):
        """Should return None when system prompt is missing."""
        from src.utils import optionally_get_system_prompt_from_config

        config = {"configurable": {}}
        result = optionally_get_system_prompt_from_config(config)

        assert result is None


# ============================================
# Tests for is_using_o1_mini_model
# ============================================


@pytest.mark.unit
class TestIsUsingO1Mini:
    """Tests for o1-mini model detection."""

    def test_is_using_o1_mini_true(self):
        """Should detect o1-mini model."""
        from src.utils import is_using_o1_mini_model

        config = {"configurable": {"customModelName": "o1-mini"}}
        result = is_using_o1_mini_model(config)

        assert result is True

    def test_is_using_o1_mini_false(self):
        """Should return False for other models."""
        from src.utils import is_using_o1_mini_model

        config = {"configurable": {"customModelName": "gpt-4o"}}
        result = is_using_o1_mini_model(config)

        assert result is False
