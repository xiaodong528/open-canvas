"""
Reply To General Input 节点

从 TypeScript 迁移: apps/agents/src/open-canvas/nodes/replyToGeneralInput.ts

功能: 生成对一般问题的响应，不涉及工件生成或修改
"""

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.store.base import BaseStore
from langgraph.types import RunnableConfig

from ..state import OpenCanvasGraphReturnType, OpenCanvasState
from ..prompts import CURRENT_ARTIFACT_PROMPT, NO_ARTIFACT_PROMPT
from ...utils import (
    create_context_document_messages,
    ensure_store_in_config,
    format_artifact_content,
    format_reflections,
    get_model_from_config,
    is_using_o1_mini_model,
)
from ...types import Reflections


# 基础提示词
REPLY_PROMPT = """You are an AI assistant tasked with responding to the users question.

The user has generated artifacts in the past. Use the following artifacts as context when responding to the users question.

You also have the following reflections on style guidelines and general memories/facts about the user to use when generating your response.
<reflections>
{reflections}
</reflections>

{currentArtifactPrompt}"""


def _get_current_artifact_content(artifact: dict) -> dict | None:
    """获取当前工件内容"""
    if not artifact:
        return None

    contents = artifact.get("contents", [])
    current_index = artifact.get("currentIndex", 1)

    # 查找当前版本的内容
    for content in contents:
        if content.get("index") == current_index:
            return content

    # 如果没找到，返回最后一个
    return contents[-1] if contents else None


async def reply_to_general_input(
    state: OpenCanvasState,
    config: RunnableConfig,
    *,
    store: BaseStore,
) -> OpenCanvasGraphReturnType:
    """
    回复一般输入，不涉及工件操作

    Args:
        state: 当前图状态
        config: LangGraph 运行配置
        store: 跨线程存储

    Returns:
        包含 messages 和 _messages 的状态更新
    """
    # 获取模型
    model = get_model_from_config(config)

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
    current_artifact_content = _get_current_artifact_content(state.get("artifact"))

    # 构建工件相关的提示词
    if current_artifact_content:
        artifact_formatted = format_artifact_content(current_artifact_content)
        current_artifact_prompt = CURRENT_ARTIFACT_PROMPT.format(
            artifact=artifact_formatted
        )
    else:
        current_artifact_prompt = NO_ARTIFACT_PROMPT

    # 格式化完整提示词
    formatted_prompt = REPLY_PROMPT.format(
        reflections=memories_as_string,
        currentArtifactPrompt=current_artifact_prompt,
    )

    # 获取上下文文档消息
    context_document_messages = await create_context_document_messages(config)

    # 检查是否使用 O1 模型 (O1 不支持系统提示词)
    is_o1_model = is_using_o1_mini_model(config)

    # 构建消息列表
    if is_o1_model:
        # O1 模型: 系统提示词作为用户消息
        messages = [
            HumanMessage(content=formatted_prompt),
            *context_document_messages,
            *state.get("_messages", []),
        ]
    else:
        # 普通模型: 使用系统提示词
        messages = [
            SystemMessage(content=formatted_prompt),
            *context_document_messages,
            *state.get("_messages", []),
        ]

    # 调用模型
    response = await model.ainvoke(messages)

    return {
        "messages": [response],
        "_messages": [response],
    }
