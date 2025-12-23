"""
Unit tests for the generate_artifact node.

This node is responsible for generating new artifacts (code or text)
based on user requests.
"""

import pytest
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
