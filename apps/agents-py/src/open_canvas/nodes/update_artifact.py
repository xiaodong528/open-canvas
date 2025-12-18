"""
Update Artifact 节点

从 TypeScript 迁移: apps/agents/src/open-canvas/nodes/updateArtifact.ts

功能: 更新代码工件中的高亮部分
"""

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.store.base import BaseStore
from langgraph.types import RunnableConfig

from ..state import OpenCanvasGraphReturnType, OpenCanvasState
from ..prompts import UPDATE_HIGHLIGHTED_ARTIFACT_PROMPT
from ...utils import (
    create_context_document_messages,
    ensure_store_in_config,
    format_reflections,
    get_model_config,
    get_model_from_config,
    is_using_o1_mini_model,
)
from ...types import ArtifactCodeV3, ArtifactV3, Reflections


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


def _is_code_artifact(content: dict | None) -> bool:
    """检查是否为代码工件"""
    return content is not None and content.get("type") == "code"


async def update_artifact(
    state: OpenCanvasState,
    config: RunnableConfig,
    *,
    store: BaseStore,
) -> OpenCanvasGraphReturnType:
    """
    更新代码工件中的高亮部分

    根据用户请求更新代码中选中的部分。使用上下文窗口
    (高亮前后各 500 字符) 来帮助模型理解代码结构。

    Args:
        state: 当前图状态
        config: LangGraph 运行配置
        store: 跨线程存储

    Returns:
        包含更新后 artifact 的状态更新
    """
    # 获取模型配置
    model_provider, model_name = get_model_config(config)

    # 选择模型 - 智能模型使用用户配置，否则使用 gpt-4o
    if "openai" in model_provider or "3-5-sonnet" in model_name:
        small_model = get_model_from_config(config, temperature=0)
    else:
        # 使用更智能的模型
        override_config = {
            **config,
            "configurable": {
                **config.get("configurable", {}),
                "customModelName": "gpt-4o",
            },
        }
        small_model = get_model_from_config(override_config, temperature=0)

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

    if not _is_code_artifact(current_artifact_content):
        raise ValueError("Current artifact content is not code")

    # 检查高亮代码
    highlighted_code = state.get("highlightedCode")
    if not highlighted_code:
        raise ValueError("Can not partially regenerate an artifact without a highlight")

    code = current_artifact_content.get("code", "")
    start_char_index = highlighted_code.get("startCharIndex", 0)
    end_char_index = highlighted_code.get("endCharIndex", len(code))

    # 提取上下文窗口 (前后各 500 字符)
    start = max(0, start_char_index - 500)
    end = min(len(code), end_char_index + 500)

    before_highlight = code[start:start_char_index]
    highlighted_text = code[start_char_index:end_char_index]
    after_highlight = code[end_char_index:end]

    # 格式化提示词
    formatted_prompt = UPDATE_HIGHLIGHTED_ARTIFACT_PROMPT.format(
        highlightedText=highlighted_text,
        beforeHighlight=before_highlight,
        afterHighlight=after_highlight,
        reflections=memories_as_string,
    )

    # 获取上下文文档消息
    context_document_messages = await create_context_document_messages(config)

    # 获取最近的用户消息
    internal_messages = state.get("_messages", [])
    recent_human_message = None
    for msg in reversed(internal_messages):
        if hasattr(msg, "type") and msg.type == "human":
            recent_human_message = msg
            break

    if not recent_human_message:
        raise ValueError("No recent human message found")

    # 检查是否使用 O1 模型
    is_o1_model = is_using_o1_mini_model(config)

    # 构建消息列表
    if is_o1_model:
        messages = [
            HumanMessage(content=formatted_prompt),
            *context_document_messages,
            recent_human_message,
        ]
    else:
        messages = [
            SystemMessage(content=formatted_prompt),
            *context_document_messages,
            recent_human_message,
        ]

    # 调用模型
    updated_artifact = await small_model.ainvoke(messages)

    # 拼接完整内容
    entire_text_before = code[:start_char_index]
    entire_text_after = code[end_char_index:]
    entire_updated_content = f"{entire_text_before}{updated_artifact.content}{entire_text_after}"

    # 创建新版本
    artifact = state.get("artifact", {})
    contents = artifact.get("contents", [])
    new_index = len(contents) + 1

    new_artifact_content: ArtifactCodeV3 = {
        **current_artifact_content,
        "index": new_index,
        "code": entire_updated_content,
    }

    new_artifact: ArtifactV3 = {
        **artifact,
        "currentIndex": new_index,
        "contents": [*contents, new_artifact_content],
    }

    return {
        "artifact": new_artifact,
    }
