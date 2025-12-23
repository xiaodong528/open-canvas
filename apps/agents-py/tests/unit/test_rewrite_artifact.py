"""
Unit tests for the rewrite_artifact node.

This node is responsible for rewriting existing artifacts based on user requests.
"""

import pytest
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
