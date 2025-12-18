"""
Generate Artifact 节点

从 TypeScript 迁移: apps/agents/src/open-canvas/nodes/generate-artifact/index.ts

功能: 根据用户请求生成新工件 (代码或文本)
"""

from typing import Literal, Optional
from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.store.base import BaseStore
from langgraph.types import RunnableConfig

from ..state import OpenCanvasGraphReturnType, OpenCanvasState
from ..prompts import NEW_ARTIFACT_PROMPT
from ...utils import (
    create_context_document_messages,
    get_formatted_reflections,
    get_model_config,
    get_model_from_config,
    is_using_o1_mini_model,
    optionally_get_system_prompt_from_config,
)
from ...types import ArtifactCodeV3, ArtifactMarkdownV3, ArtifactV3
from ...constants import PROGRAMMING_LANGUAGES


# 工件生成工具 Schema
class GenerateArtifactTool(BaseModel):
    """生成工件的工具参数"""

    type: Literal["code", "text"] = Field(
        description="The content type of the artifact generated."
    )
    language: Optional[str] = Field(
        default=None,
        description=(
            "The language/programming language of the artifact generated.\n"
            "If generating code, it should be one of the options, or 'other'.\n"
            "If not generating code, the language should ALWAYS be 'other'."
        ),
    )
    isValidReact: Optional[bool] = Field(
        default=None,
        description=(
            "Whether or not the generated code is valid React code. "
            "Only populate this field if generating code."
        ),
    )
    artifact: str = Field(description="The content of the artifact to generate.")
    title: str = Field(
        description="A short title to give to the artifact. Should be less than 5 words."
    )


def _format_new_artifact_prompt(memories_as_string: str, model_name: str) -> str:
    """格式化新工件生成提示词"""
    # Claude 模型需要禁用 CoT
    disable_cot = ""
    if "claude" in model_name.lower():
        disable_cot = (
            "\n\nIMPORTANT: Do NOT preform chain of thought beforehand. "
            "Instead, go STRAIGHT to generating the tool response. This is VERY important."
        )

    return NEW_ARTIFACT_PROMPT.format(
        reflections=memories_as_string,
        disableChainOfThought=disable_cot,
    )


def _create_artifact_content(tool_call: dict) -> ArtifactCodeV3 | ArtifactMarkdownV3:
    """根据工具调用结果创建工件内容"""
    artifact_type = tool_call.get("type")

    if artifact_type == "code":
        return {
            "index": 1,
            "type": "code",
            "title": tool_call.get("title", ""),
            "code": tool_call.get("artifact", ""),
            "language": tool_call.get("language", "other"),
            "isValidReact": tool_call.get("isValidReact", False),
        }

    return {
        "index": 1,
        "type": "text",
        "title": tool_call.get("title", ""),
        "fullMarkdown": tool_call.get("artifact", ""),
    }


async def generate_artifact(
    state: OpenCanvasState,
    config: RunnableConfig,
    *,
    store: BaseStore,
) -> OpenCanvasGraphReturnType:
    """
    根据用户请求生成新工件

    使用工具调用来生成结构化的工件内容。支持代码和文本两种类型。

    Args:
        state: 当前图状态
        config: LangGraph 运行配置
        store: 跨线程存储

    Returns:
        包含新 artifact 的状态更新
    """
    # 获取模型配置
    _, model_name = get_model_config(config, is_tool_calling=True)

    # 获取模型 (使用工具调用模式)
    small_model = get_model_from_config(
        config, temperature=0.5, is_tool_calling=True
    )

    # 绑定工件生成工具
    model_with_artifact_tool = small_model.bind_tools(
        [GenerateArtifactTool],
        tool_choice="GenerateArtifactTool",
    )

    # 获取反思/记忆
    memories_as_string = await get_formatted_reflections(config, store)

    # 格式化提示词
    formatted_prompt = _format_new_artifact_prompt(memories_as_string, model_name)

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
    internal_messages = state.get("_messages", [])

    if is_o1_model:
        messages = [
            HumanMessage(content=full_system_prompt),
            *context_document_messages,
            *internal_messages,
        ]
    else:
        messages = [
            SystemMessage(content=full_system_prompt),
            *context_document_messages,
            *internal_messages,
        ]

    # 调用模型
    response = await model_with_artifact_tool.ainvoke(messages)

    # 提取工具调用结果
    if not response.tool_calls:
        raise ValueError("No tool calls found in response")

    args = response.tool_calls[0].get("args", {})
    if not args:
        raise ValueError("No args found in response")

    # 创建工件内容
    new_artifact_content = _create_artifact_content(args)

    # 创建新工件
    new_artifact: ArtifactV3 = {
        "currentIndex": 1,
        "contents": [new_artifact_content],
    }

    return {
        "artifact": new_artifact,
    }
