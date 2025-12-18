"""
Generate Followup 节点

从 TypeScript 迁移: apps/agents/src/open-canvas/nodes/generateFollowup.ts

功能: 在生成或更新工件后，生成一条简短的跟进消息
"""

from langchain_core.messages import HumanMessage
from langgraph.store.base import BaseStore
from langgraph.types import RunnableConfig

from ..state import OpenCanvasGraphReturnType, OpenCanvasState
from ..prompts import FOLLOWUP_ARTIFACT_PROMPT
from ...utils import (
    ensure_store_in_config,
    format_reflections,
    get_model_from_config,
)
from ...types import Reflections


def _get_artifact_content(artifact: dict) -> str:
    """获取工件内容字符串"""
    if not artifact:
        return "No artifacts generated yet."

    contents = artifact.get("contents", [])
    current_index = artifact.get("currentIndex", 1)

    # 查找当前版本的内容
    current_content = None
    for content in contents:
        if content.get("index") == current_index:
            current_content = content
            break

    if not current_content:
        # 如果没找到，使用最后一个
        current_content = contents[-1] if contents else None

    if not current_content:
        return "No artifacts generated yet."

    # 根据类型返回内容
    if current_content.get("type") == "code":
        return current_content.get("code", "")
    else:
        return current_content.get("fullMarkdown", "")


def _format_messages_for_conversation(messages: list) -> str:
    """格式化消息列表为对话字符串"""
    formatted = []
    for msg in messages:
        msg_type = msg.type if hasattr(msg, "type") else "unknown"
        content = msg.content if isinstance(msg.content, str) else ""

        # 处理复杂内容结构
        if not isinstance(msg.content, str) and hasattr(msg.content, "__iter__"):
            content = "\n".join(
                c.get("text", "")
                for c in msg.content
                if isinstance(c, dict) and "text" in c
            )

        formatted.append(f"<{msg_type}>\n{content}\n</{msg_type}>")

    return "\n\n".join(formatted)


async def generate_followup(
    state: OpenCanvasState,
    config: RunnableConfig,
    *,
    store: BaseStore,
) -> OpenCanvasGraphReturnType:
    """
    在生成或更新工件后，生成跟进消息

    Args:
        state: 当前图状态
        config: LangGraph 运行配置
        store: 跨线程存储

    Returns:
        包含 messages 和 _messages 的状态更新
    """
    # 使用小模型 (maxTokens=250, isToolCalling=True 会选择较小的模型)
    small_model = get_model_from_config(config, is_tool_calling=True, max_tokens=250)

    # 获取 assistant_id
    assistant_id = config.get("configurable", {}).get("assistant_id")
    if not assistant_id:
        raise ValueError("`assistant_id` not found in configurable")

    # 从 store 获取反思/记忆
    memory_namespace = ("memories", assistant_id)
    memory_key = "reflection"
    memories = await store.aget(memory_namespace, memory_key)

    if memories and memories.value:
        memories_as_string = format_reflections(
            memories.value, only_content=True
        )
    else:
        memories_as_string = "No reflections found."

    # 获取当前工件内容
    artifact_content = _get_artifact_content(state.get("artifact"))

    # 格式化对话历史
    internal_messages = state.get("_messages", [])
    conversation = _format_messages_for_conversation(internal_messages)

    # 格式化 prompt
    formatted_prompt = FOLLOWUP_ARTIFACT_PROMPT.format(
        artifactContent=artifact_content,
        reflections=memories_as_string,
        conversation=conversation,
    )

    # 调用模型
    response = await small_model.ainvoke([
        HumanMessage(content=formatted_prompt)
    ])

    return {
        "messages": [response],
        "_messages": [response],
    }
