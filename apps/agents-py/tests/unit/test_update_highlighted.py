"""
Unit tests for the update_artifact and update_highlighted_text nodes.

These nodes handle updating specific portions of artifacts based on
user-highlighted selections.
"""

import pytest
from langchain_core.messages import HumanMessage, AIMessage


@pytest.mark.unit
class TestUpdateArtifact:
    """Tests for the update_artifact node (code highlighting)."""

    def test_update_artifact_function_exists(self):
        """update_artifact function should exist and be callable."""
        from src.open_canvas.nodes.update_artifact import update_artifact

        assert callable(update_artifact)

    def test_get_model_from_config_function_exists(self):
        """get_model_from_config function should be imported."""
        from src.open_canvas.nodes.update_artifact import get_model_from_config

        assert callable(get_model_from_config)

    def test_get_artifact_content_exists(self):
        """_get_artifact_content helper should exist."""
        from src.open_canvas.nodes.update_artifact import _get_artifact_content

        assert callable(_get_artifact_content)

    def test_is_code_artifact_exists(self):
        """_is_code_artifact helper should exist."""
        from src.open_canvas.nodes.update_artifact import _is_code_artifact

        assert callable(_is_code_artifact)


@pytest.mark.unit
class TestUpdateHighlightedText:
    """Tests for the update_highlighted_text node (markdown highlighting)."""

    def test_update_highlighted_text_function_exists(self):
        """update_highlighted_text function should exist and be callable."""
        from src.open_canvas.nodes.update_highlighted_text import update_highlighted_text

        assert callable(update_highlighted_text)

    def test_get_model_from_config_function_exists(self):
        """get_model_from_config function should be imported."""
        from src.open_canvas.nodes.update_highlighted_text import get_model_from_config

        assert callable(get_model_from_config)

    def test_get_artifact_content_exists(self):
        """_get_artifact_content helper should exist."""
        from src.open_canvas.nodes.update_highlighted_text import _get_artifact_content

        assert callable(_get_artifact_content)

    def test_is_markdown_artifact_exists(self):
        """_is_markdown_artifact helper should exist."""
        from src.open_canvas.nodes.update_highlighted_text import _is_markdown_artifact

        assert callable(_is_markdown_artifact)


@pytest.mark.unit
class TestHighlightTypes:
    """Tests for highlight-related types."""

    def test_code_highlight_type_is_defined(self):
        """CodeHighlight type should be importable."""
        from src.types import CodeHighlight

        assert CodeHighlight is not None

    def test_text_highlight_type_is_defined(self):
        """TextHighlight type should be importable."""
        from src.types import TextHighlight

        assert TextHighlight is not None
