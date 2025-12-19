"""
Rewrite Artifact 节点

从 TypeScript 迁移: apps/agents/src/open-canvas/nodes/rewrite-artifact/index.ts

功能: 重写现有工件，支持类型转换
"""

import uuid
from typing import Literal, Optional
from pydantic import BaseModel, Field
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.store.base import BaseStore
from langgraph.types import RunnableConfig

from ..state import OpenCanvasGraphReturnType, OpenCanvasState
from ..prompts import UPDATE_ENTIRE_ARTIFACT_PROMPT, OPTIONALLY_UPDATE_META_PROMPT, GET_TITLE_TYPE_REWRITE_ARTIFACT
from ...utils import (
    create_context_document_messages,
    extract_thinking_and_response,
    format_artifact_content,
    get_formatted_reflections,
    get_model_config,
    get_model_from_config,
    is_thinking_model,
    is_using_o1_mini_model,
    optionally_get_system_prompt_from_config,
)
from ...types import ArtifactCodeV3, ArtifactMarkdownV3, ArtifactV3


# 元数据更新工具 Schema
class UpdateArtifactMetaTool(BaseModel):
    """可选更新工件元数据的工具参数"""

    type: Literal["code", "text"] = Field(
        description="The type of the artifact to generate."
    )
    title: Optional[str] = Field(
        default=None,
        description="The new title to give the artifact."
    )
    language: Optional[str] = Field(
        default=None,
        description="The language of the code artifact (if applicable)."
    )
    isValidReact: Optional[bool] = Field(
        default=None,
        description="Whether the code is valid React (if applicable)."
    )


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


def _is_code_artifact(content: dict | None) -> bool:
    """检查是否为代码工件"""
    return content is not None and content.get("type") == "code"


async def _optionally_update_artifact_meta(
    state: OpenCanvasState,
    config: RunnableConfig,
    store: BaseStore,  # pylint: disable=unused-argument
) -> dict:
    """
    使用 LLM 决定是否需要更新工件类型和标题

    使用 GET_TITLE_TYPE_REWRITE_ARTIFACT 模板分析用户意图

    Returns:
        包含 type, title, language, isValidReact 的字典
    """
    current_artifact_content = _get_artifact_content(state.get("artifact"))
    if not current_artifact_content:
        return {"type": "text", "title": None, "language": None, "isValidReact": None}

    # 获取模型
    small_model = get_model_from_config(config, is_tool_calling=True)

    # 绑定工具
    model_with_tool = small_model.bind_tools(
        [UpdateArtifactMetaTool],
        tool_choice="UpdateArtifactMetaTool",
    )

    # 获取最近的用户消息
    internal_messages = state.get("_messages", [])
    recent_human_message = None
    for msg in reversed(internal_messages):
        if hasattr(msg, "type") and msg.type == "human":
            recent_human_message = msg
            break

    if not recent_human_message:
        # 返回当前类型
        return {
            "type": current_artifact_content.get("type", "text"),
            "title": current_artifact_content.get("title"),
            "language": current_artifact_content.get("language"),
            "isValidReact": current_artifact_content.get("isValidReact"),
        }

    # 使用正确的模板构建提示词 (只有 {artifact} 占位符)
    prompt = GET_TITLE_TYPE_REWRITE_ARTIFACT.format(
        artifact=format_artifact_content(current_artifact_content, shorten_content=True),
    )

    # 检查是否使用 O1 模型
    is_o1_model = is_using_o1_mini_model(config)

    # 调用模型
    response = await model_with_tool.ainvoke([
        {"role": "user" if is_o1_model else "system", "content": prompt},
        recent_human_message,
    ])

    # 提取工具调用结果
    artifact_type = current_artifact_content.get("type", "text")
    if response.tool_calls:
        args = response.tool_calls[0].get("args", {})
        return {
            "type": args.get("type", artifact_type),
            "title": args.get("title") or current_artifact_content.get("title"),
            "language": args.get("language") or current_artifact_content.get("language"),
            "isValidReact": args.get("isValidReact") or current_artifact_content.get("isValidReact"),
        }

    return {
        "type": artifact_type,
        "title": current_artifact_content.get("title"),
        "language": current_artifact_content.get("language"),
        "isValidReact": current_artifact_content.get("isValidReact"),
    }


def _build_prompt(
    artifact_content: str,
    memories_as_string: str,
    is_new_type: bool,
    artifact_meta: dict,
) -> str:
    """构建重写提示词"""
    # 构建元数据提示词
    meta_prompt = ""
    if is_new_type:
        title_section = ""
        if artifact_meta.get("title") and artifact_meta.get("type") != "code":
            title_section = f"And its title is (do NOT include this in your response):\n{artifact_meta['title']}"

        meta_prompt = OPTIONALLY_UPDATE_META_PROMPT.format(
            artifactType=artifact_meta.get("type", "text"),
            artifactTitle=title_section,
        )

    return UPDATE_ENTIRE_ARTIFACT_PROMPT.format(
        artifactContent=artifact_content,
        reflections=memories_as_string,
        updateMetaPrompt=meta_prompt,
    )


def _create_new_artifact_content(
    artifact_type: str,
    state: OpenCanvasState,
    current_artifact_content: dict,
    artifact_meta: dict,
    new_content: str,
) -> ArtifactCodeV3 | ArtifactMarkdownV3:
    """创建新的工件内容"""
    artifact = state.get("artifact", {})
    contents = artifact.get("contents", [])
    new_index = len(contents) + 1

    base_content = {
        "index": new_index,
        "title": artifact_meta.get("title") or current_artifact_content.get("title", ""),
    }

    if artifact_type == "code":
        # 确定语言
        language = artifact_meta.get("language")
        if not language and _is_code_artifact(current_artifact_content):
            language = current_artifact_content.get("language", "other")
        if not language:
            language = "other"

        return {
            **base_content,
            "type": "code",
            "language": language,
            "code": new_content,
            "isValidReact": artifact_meta.get("isValidReact", False),
        }

    return {
        **base_content,
        "type": "text",
        "fullMarkdown": new_content,
    }


async def rewrite_artifact(
    state: OpenCanvasState,
    config: RunnableConfig,
    *,
    store: BaseStore,
) -> OpenCanvasGraphReturnType:
    """
    重写现有工件

    支持类型转换 (代码 ↔ 文本) 和元数据更新。

    Args:
        state: 当前图状态
        config: LangGraph 运行配置
        store: 跨线程存储

    Returns:
        包含更新后 artifact 的状态更新，可能包含思考消息
    """
    # 获取模型
    model_cfg = get_model_config(config)
    model_name = model_cfg.get("modelName", "")
    small_model = get_model_from_config(config)

    # 获取反思/记忆
    memories_as_string = await get_formatted_reflections(config)

    # 验证状态
    current_artifact_content = _get_artifact_content(state.get("artifact"))
    if not current_artifact_content:
        raise ValueError("No artifact found")

    # 获取最近的用户消息
    internal_messages = state.get("_messages", [])
    recent_human_message = None
    for msg in reversed(internal_messages):
        if hasattr(msg, "type") and msg.type == "human":
            recent_human_message = msg
            break

    if not recent_human_message:
        raise ValueError("No recent human message found")

    # 可选更新元数据
    artifact_meta = await _optionally_update_artifact_meta(state, config, store)
    artifact_type = artifact_meta.get("type", "text")
    is_new_type = artifact_type != current_artifact_content.get("type")

    # 获取当前工件内容
    if _is_markdown_artifact(current_artifact_content):
        artifact_content = current_artifact_content.get("fullMarkdown", "")
    else:
        artifact_content = current_artifact_content.get("code", "")

    # 构建提示词
    formatted_prompt = _build_prompt(
        artifact_content,
        memories_as_string,
        is_new_type,
        artifact_meta,
    )

    # 获取用户自定义系统提示词
    user_system_prompt = optionally_get_system_prompt_from_config(config)
    full_system_prompt = (
        f"{user_system_prompt}\n{formatted_prompt}"
        if user_system_prompt
        else formatted_prompt
    )

    # 获取上下文文档消息
    context_document_messages = await create_context_document_messages(config)

    # 检查是否使用 O1 模型
    is_o1_model = is_using_o1_mini_model(config)

    # 构建消息列表
    if is_o1_model:
        messages = [
            HumanMessage(content=full_system_prompt),
            *context_document_messages,
            recent_human_message,
        ]
    else:
        messages = [
            SystemMessage(content=full_system_prompt),
            *context_document_messages,
            recent_human_message,
        ]

    # 调用模型
    new_artifact_response = await small_model.ainvoke(messages)

    # 处理思考模型输出
    thinking_message = None
    artifact_content_text = str(new_artifact_response.content)

    if is_thinking_model(model_name):
        thinking, response = extract_thinking_and_response(artifact_content_text)
        if thinking:
            thinking_message = AIMessage(
                id=f"thinking-{uuid.uuid4()}",
                content=thinking,
            )
        artifact_content_text = response

    # 创建新工件内容
    new_artifact_content = _create_new_artifact_content(
        artifact_type,
        state,
        current_artifact_content,
        artifact_meta,
        artifact_content_text,
    )

    # 创建新工件
    artifact = state.get("artifact", {})
    contents = artifact.get("contents", [])

    new_artifact: ArtifactV3 = {
        **artifact,
        "currentIndex": len(contents) + 1,
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
