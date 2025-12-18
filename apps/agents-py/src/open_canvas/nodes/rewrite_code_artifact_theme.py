"""
Rewrite Code Artifact Theme 节点

从 TypeScript 迁移: apps/agents/src/open-canvas/nodes/rewriteCodeArtifactTheme.ts

功能: 重写代码工件的主题 (添加注释、日志、修复 bug、移植语言)
"""

import uuid
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.store.base import BaseStore
from langgraph.types import RunnableConfig

from ..state import OpenCanvasGraphReturnType, OpenCanvasState
from ..prompts import (
    ADD_COMMENTS_TO_CODE_ARTIFACT_PROMPT,
    ADD_LOGS_TO_CODE_ARTIFACT_PROMPT,
    FIX_BUGS_CODE_ARTIFACT_PROMPT,
    PORT_LANGUAGE_CODE_ARTIFACT_PROMPT,
)
from ...utils import (
    extract_thinking_and_response,
    get_model_config,
    get_model_from_config,
    is_thinking_model,
)
from ...types import ArtifactCodeV3, ArtifactV3


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


# 语言名称映射
LANGUAGE_MAP = {
    "typescript": "TypeScript",
    "javascript": "JavaScript",
    "cpp": "C++",
    "java": "Java",
    "php": "PHP",
    "python": "Python",
    "html": "HTML",
    "sql": "SQL",
}


async def rewrite_code_artifact_theme(
    state: OpenCanvasState,
    config: RunnableConfig,
    *,
    store: BaseStore,
) -> OpenCanvasGraphReturnType:
    """
    重写代码工件的主题

    支持以下操作:
    - 添加注释 (addComments)
    - 添加日志 (addLogs)
    - 修复 bug (fixBugs)
    - 移植语言 (portLanguage)

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

    # 获取当前工件内容
    current_artifact_content = _get_artifact_content(state.get("artifact"))
    if not current_artifact_content:
        raise ValueError("No artifact found")

    if not _is_code_artifact(current_artifact_content):
        raise ValueError("Current artifact content is not code")

    code = current_artifact_content.get("code", "")

    # 根据状态选择提示词
    formatted_prompt = ""

    if state.get("addComments"):
        # 添加注释
        formatted_prompt = ADD_COMMENTS_TO_CODE_ARTIFACT_PROMPT
    elif state.get("portLanguage"):
        # 移植语言
        port_language = state.get("portLanguage")
        new_language = LANGUAGE_MAP.get(port_language, port_language)
        formatted_prompt = PORT_LANGUAGE_CODE_ARTIFACT_PROMPT.format(
            newLanguage=new_language
        )
    elif state.get("addLogs"):
        # 添加日志
        formatted_prompt = ADD_LOGS_TO_CODE_ARTIFACT_PROMPT
    elif state.get("fixBugs"):
        # 修复 bug
        formatted_prompt = FIX_BUGS_CODE_ARTIFACT_PROMPT
    else:
        raise ValueError("No theme selected")

    # 插入代码内容
    formatted_prompt = formatted_prompt.format(artifactContent=code)

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

    # 确定新的语言
    new_language = state.get("portLanguage") or current_artifact_content.get("language")

    new_artifact_content: ArtifactCodeV3 = {
        "index": new_index,
        "type": "code",
        "title": current_artifact_content.get("title", ""),
        "language": new_language,
        "code": artifact_content_text,
        "isValidReact": current_artifact_content.get("isValidReact", False),
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
