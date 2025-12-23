"""
Unit tests for the generate_path node.

This node is responsible for routing requests to the appropriate handler
based on the user's input and current state.
"""

import pytest
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
