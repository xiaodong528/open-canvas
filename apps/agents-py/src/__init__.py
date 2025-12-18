"""
Open Canvas LangGraph Agents (Python)

这是 Open Canvas 代理的 Python 实现，提供与 TypeScript 版本相同的功能。
"""

__version__ = "0.1.0"

# 导出共享模块
from .constants import (
    CHARACTER_MAX,
    CONTEXT_DOCUMENTS_NAMESPACE,
    DEFAULT_INPUTS,
    LANGCHAIN_USER_ONLY_MODELS,
    OC_HIDE_FROM_UI_KEY,
    OC_SUMMARIZED_MESSAGE_KEY,
    OC_WEB_SEARCH_RESULTS_MESSAGE_KEY,
    PROGRAMMING_LANGUAGES,
    TEMPERATURE_EXCLUDED_MODELS,
)
from .types import (
    ArtifactCodeV3,
    ArtifactLengthOptions,
    ArtifactMarkdownV3,
    ArtifactType,
    ArtifactV3,
    CodeHighlight,
    ContextDocument,
    CustomModelConfig,
    CustomQuickAction,
    ExaMetadata,
    GraphInput,
    LanguageOptions,
    ProgrammingLanguageOptions,
    ReadingLevelOptions,
    Reflections,
    SearchResult,
    TextHighlight,
)
from .utils import (
    create_ai_message_from_web_results,
    ensure_store_in_config,
    format_artifact_content,
    format_artifact_content_with_template,
    format_messages,
    format_reflections,
    get_formatted_reflections,
    get_model_config,
    get_model_from_config,
    get_string_from_content,
    is_artifact_code_content,
    is_using_o1_mini_model,
    optionally_get_system_prompt_from_config,
)

__all__ = [
    # Constants
    "CHARACTER_MAX",
    "CONTEXT_DOCUMENTS_NAMESPACE",
    "DEFAULT_INPUTS",
    "LANGCHAIN_USER_ONLY_MODELS",
    "OC_HIDE_FROM_UI_KEY",
    "OC_SUMMARIZED_MESSAGE_KEY",
    "OC_WEB_SEARCH_RESULTS_MESSAGE_KEY",
    "PROGRAMMING_LANGUAGES",
    "TEMPERATURE_EXCLUDED_MODELS",
    # Types
    "ArtifactCodeV3",
    "ArtifactLengthOptions",
    "ArtifactMarkdownV3",
    "ArtifactType",
    "ArtifactV3",
    "CodeHighlight",
    "ContextDocument",
    "CustomModelConfig",
    "CustomQuickAction",
    "ExaMetadata",
    "GraphInput",
    "LanguageOptions",
    "ProgrammingLanguageOptions",
    "ReadingLevelOptions",
    "Reflections",
    "SearchResult",
    "TextHighlight",
    # Utils
    "create_ai_message_from_web_results",
    "ensure_store_in_config",
    "format_artifact_content",
    "format_artifact_content_with_template",
    "format_messages",
    "format_reflections",
    "get_formatted_reflections",
    "get_model_config",
    "get_model_from_config",
    "get_string_from_content",
    "is_artifact_code_content",
    "is_using_o1_mini_model",
    "optionally_get_system_prompt_from_config",
]
