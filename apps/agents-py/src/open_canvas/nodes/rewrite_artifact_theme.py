"""
Rewrite Artifact Theme 节点

从 TypeScript 迁移: apps/agents/src/open-canvas/nodes/rewriteArtifactTheme.ts

功能: 重写文本工件的主题 (语言、阅读级别、长度、表情符号等)
"""

import uuid
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.store.base import BaseStore
from langgraph.types import RunnableConfig

from ..state import OpenCanvasGraphReturnType, OpenCanvasState
from ..prompts import (
    ADD_EMOJIS_TO_ARTIFACT_PROMPT,
    CHANGE_ARTIFACT_LANGUAGE_PROMPT,
    CHANGE_ARTIFACT_LENGTH_PROMPT,
    CHANGE_ARTIFACT_READING_LEVEL_PROMPT,
    CHANGE_ARTIFACT_TO_PIRATE_PROMPT,
)
from ...utils import (
    ensure_store_in_config,
    extract_thinking_and_response,
    format_reflections,
    get_model_config,
    get_model_from_config,
    is_thinking_model,
)
from ...types import ArtifactMarkdownV3, ArtifactV3, Reflections


def _get_artifact_content(artifact: dict | None) -> dict | None:
    """获取当前工件内容"""
    if not artifact:
        return None

    contents = artifact.get("contents", [])
    current_index = artifact.get("currentIndex", 1)

    for content in contents:
        if content.get("index") == current_index:
            return content

    return contents[-1] if contents else None


def _is_markdown_artifact(content: dict | None) -> bool:
    """检查是否为 Markdown 工件"""
    return content is not None and content.get("type") == "text"


# 阅读级别映射
READING_LEVEL_MAP = {
    "child": "elementary school student",
    "teenager": "high school student",
    "college": "college student",
    "phd": "PhD student",
}

# 长度描述映射
LENGTH_MAP = {
    "shortest": "much shorter than it currently is",
    "short": "slightly shorter than it currently is",
    "long": "slightly longer than it currently is",
    "longest": "much longer than it currently is",
}


async def rewrite_artifact_theme(
    state: OpenCanvasState,
    config: RunnableConfig,
    *,
    store: BaseStore,
) -> OpenCanvasGraphReturnType:
    """
    重写文本工件的主题

    支持以下操作:
    - 更改语言 (language)
    - 更改阅读级别 (readingLevel)
    - 更改长度 (artifactLength)
    - 添加表情符号 (regenerateWithEmojis)

    Args:
        state: 当前图状态
        config: LangGraph 运行配置
        store: 跨线程存储

    Returns:
        包含更新后 artifact 的状态更新，可能包含思考消息
    """
    # 获取模型
    _, model_name = get_model_config(config)
    small_model = get_model_from_config(config)

    # 获取 assistant_id
    assistant_id = config.get("configurable", {}).get("assistant_id")
    if not assistant_id:
        raise ValueError("`assistant_id` not found in configurable")

    # 从 store 获取反思/记忆
    memory_namespace = ("memories", assistant_id)
    memory_key = "reflection"
    memories = await store.aget(memory_namespace, memory_key)

    if memories and memories.value:
        memories_as_string = format_reflections(memories.value)
    else:
        memories_as_string = "No reflections found."

    # 获取当前工件内容
    current_artifact_content = _get_artifact_content(state.get("artifact"))
    if not current_artifact_content:
        raise ValueError("No artifact found")

    if not _is_markdown_artifact(current_artifact_content):
        raise ValueError("Current artifact content is not markdown")

    full_markdown = current_artifact_content.get("fullMarkdown", "")

    # 根据状态选择提示词
    formatted_prompt = ""

    if state.get("language"):
        # 更改语言
        formatted_prompt = CHANGE_ARTIFACT_LANGUAGE_PROMPT.format(
            newLanguage=state.get("language"),
            artifactContent=full_markdown,
        )
    elif state.get("readingLevel") and state.get("readingLevel") != "pirate":
        # 更改阅读级别
        reading_level = state.get("readingLevel")
        new_reading_level = READING_LEVEL_MAP.get(reading_level, reading_level)
        formatted_prompt = CHANGE_ARTIFACT_READING_LEVEL_PROMPT.format(
            newReadingLevel=new_reading_level,
            artifactContent=full_markdown,
        )
    elif state.get("readingLevel") == "pirate":
        # 海盗模式
        formatted_prompt = CHANGE_ARTIFACT_TO_PIRATE_PROMPT.format(
            artifactContent=full_markdown,
        )
    elif state.get("artifactLength"):
        # 更改长度
        artifact_length = state.get("artifactLength")
        new_length = LENGTH_MAP.get(artifact_length, artifact_length)
        formatted_prompt = CHANGE_ARTIFACT_LENGTH_PROMPT.format(
            newLength=new_length,
            artifactContent=full_markdown,
        )
    elif state.get("regenerateWithEmojis"):
        # 添加表情符号
        formatted_prompt = ADD_EMOJIS_TO_ARTIFACT_PROMPT.format(
            artifactContent=full_markdown,
        )
    else:
        raise ValueError("No theme selected")

    # 添加反思信息
    formatted_prompt = formatted_prompt.replace("{reflections}", memories_as_string)

    # 调用模型
    new_artifact_values = await small_model.ainvoke([
        HumanMessage(content=formatted_prompt)
    ])

    # 处理思考模型输出
    thinking_message = None
    artifact_content_text = str(new_artifact_values.content)

    if is_thinking_model(model_name):
        thinking, response = extract_thinking_and_response(artifact_content_text)
        if thinking:
            thinking_message = AIMessage(
                id=f"thinking-{uuid.uuid4()}",
                content=thinking,
            )
        artifact_content_text = response

    # 创建新版本
    artifact = state.get("artifact", {})
    contents = artifact.get("contents", [])
    new_index = len(contents) + 1

    new_artifact_content: ArtifactMarkdownV3 = {
        **current_artifact_content,
        "index": new_index,
        "fullMarkdown": artifact_content_text,
    }

    new_artifact: ArtifactV3 = {
        **artifact,
        "currentIndex": new_index,
        "contents": [*contents, new_artifact_content],
    }

    result: OpenCanvasGraphReturnType = {
        "artifact": new_artifact,
    }

    # 添加思考消息
    if thinking_message:
        result["messages"] = [thinking_message]
        result["_messages"] = [thinking_message]

    return result
