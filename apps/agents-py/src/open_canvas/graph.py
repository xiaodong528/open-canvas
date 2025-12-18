"""
Open Canvas 主代理图

包含核心工作流：生成路径、工件管理、跟进消息等

从 TypeScript 迁移: apps/agents/src/open-canvas/index.ts
"""

from typing import Literal, cast
from langgraph.graph import END, START, StateGraph
from langgraph.store.base import BaseStore
from langgraph.types import RunnableConfig

from .state import OpenCanvasState, OpenCanvasGraphReturnType
from .nodes import (
    generate_followup,
    reply_to_general_input,
    reflect_node,
    generate_title_node,
    # 第二批
    update_artifact,
    update_highlighted_text,
    rewrite_artifact_theme,
    rewrite_code_artifact_theme,
    # 第三批
    generate_artifact,
    rewrite_artifact,
    custom_action,
    # 第四批
    generate_path,
)
from ..utils import DEFAULT_INPUTS
from ..constants import CHARACTER_MAX


# ============================================
# 辅助函数
# ============================================


def _calculate_message_chars(state: OpenCanvasState) -> int:
    """计算 _messages 中的总字符数"""
    total_chars = 0
    for msg in state.get("_messages", []):
        content = msg.content
        if isinstance(content, str):
            total_chars += len(content)
        elif isinstance(content, list):
            # 处理复杂内容结构
            for c in content:
                if isinstance(c, dict) and "text" in c:
                    total_chars += len(c.get("text", ""))
    return total_chars


# ============================================
# 路由函数
# ============================================


def route_after_generate_path(
    state: OpenCanvasState,
) -> Literal[
    "updateArtifact",
    "rewriteArtifactTheme",
    "rewriteCodeArtifactTheme",
    "replyToGeneralInput",
    "generateArtifact",
    "rewriteArtifact",
    "customAction",
    "updateHighlightedText",
    "webSearch",
]:
    """
    根据 generatePath 设置的 next 字段路由到下一个节点

    Returns:
        下一个节点名称
    """
    next_node = state.get("next")
    if not next_node:
        # 默认路由到一般回复
        return "replyToGeneralInput"
    return cast(str, next_node)


def route_after_clean_state(
    state: OpenCanvasState,
) -> Literal["generateTitle", "summarizer", "__end__"]:
    """
    清理状态后决定是否生成标题或摘要

    - 如果 messages <= 2，生成标题
    - 如果字符数超过阈值，启动摘要
    - 否则结束
    """
    messages = state.get("messages", [])

    # 首次对话时生成标题
    if len(messages) <= 2:
        return "generateTitle"

    # 检查是否需要摘要
    total_chars = _calculate_message_chars(state)
    if total_chars > CHARACTER_MAX:
        return "summarizer"

    return "__end__"


def route_post_web_search(
    state: OpenCanvasState,
) -> Literal["generateArtifact", "rewriteArtifact"]:
    """
    Web 搜索后路由

    - 如果已有工件，重写
    - 否则生成新工件
    """
    artifact = state.get("artifact")
    has_artifact = artifact and len(artifact.get("contents", [])) > 1
    return "rewriteArtifact" if has_artifact else "generateArtifact"


# ============================================
# 辅助节点 (子图占位)
# ============================================


async def web_search(
    state: OpenCanvasState,
    config: RunnableConfig,
    *,
    store: BaseStore,
) -> OpenCanvasGraphReturnType:
    """Web 搜索 - 使用子图"""
    # TODO: 集成 web_search 子图
    return {
        "webSearchResults": [],
    }


async def summarizer(
    state: OpenCanvasState,
    config: RunnableConfig,
    *,
    store: BaseStore,
) -> OpenCanvasGraphReturnType:
    """摘要节点 - 使用子图"""
    # TODO: 集成 summarizer 子图
    return {}


def clean_state(state: OpenCanvasState) -> OpenCanvasGraphReturnType:
    """
    清理状态节点 (同步)

    重置临时状态字段到默认值。
    """
    return DEFAULT_INPUTS.copy()


# ============================================
# 构建图
# ============================================


def build_graph() -> StateGraph:
    """构建 Open Canvas 主图"""
    builder = StateGraph(OpenCanvasState)

    # ===== 添加节点 =====

    # 路由节点
    builder.add_node("generatePath", generate_path)

    # 第一批: 已实现的真实节点
    builder.add_node("replyToGeneralInput", reply_to_general_input)
    builder.add_node("generateFollowup", generate_followup)
    builder.add_node("reflect", reflect_node)
    builder.add_node("generateTitle", generate_title_node)

    # 工件操作节点 (占位)
    builder.add_node("generateArtifact", generate_artifact)
    builder.add_node("rewriteArtifact", rewrite_artifact)
    builder.add_node("updateArtifact", update_artifact)
    builder.add_node("updateHighlightedText", update_highlighted_text)
    builder.add_node("rewriteArtifactTheme", rewrite_artifact_theme)
    builder.add_node("rewriteCodeArtifactTheme", rewrite_code_artifact_theme)
    builder.add_node("customAction", custom_action)

    # 辅助节点
    builder.add_node("webSearch", web_search)
    builder.add_node("summarizer", summarizer)
    builder.add_node("cleanState", clean_state)

    # ===== 添加边 =====

    # 入口
    builder.add_edge(START, "generatePath")

    # generatePath 路由到各处理节点
    builder.add_conditional_edges(
        "generatePath",
        route_after_generate_path,
        [
            "updateArtifact",
            "rewriteArtifactTheme",
            "rewriteCodeArtifactTheme",
            "replyToGeneralInput",
            "generateArtifact",
            "rewriteArtifact",
            "customAction",
            "updateHighlightedText",
            "webSearch",
        ],
    )

    # 工件操作后 → generateFollowup
    builder.add_edge("generateArtifact", "generateFollowup")
    builder.add_edge("rewriteArtifact", "generateFollowup")
    builder.add_edge("updateArtifact", "generateFollowup")
    builder.add_edge("updateHighlightedText", "generateFollowup")
    builder.add_edge("rewriteArtifactTheme", "generateFollowup")
    builder.add_edge("rewriteCodeArtifactTheme", "generateFollowup")
    builder.add_edge("customAction", "generateFollowup")

    # Web 搜索后路由
    builder.add_conditional_edges(
        "webSearch",
        route_post_web_search,
        ["generateArtifact", "rewriteArtifact"],
    )

    # 一般回复 → cleanState (不需要 followup)
    builder.add_edge("replyToGeneralInput", "cleanState")

    # 工件跟进后 → reflect → cleanState
    builder.add_edge("generateFollowup", "reflect")
    builder.add_edge("reflect", "cleanState")

    # cleanState 后条件路由
    builder.add_conditional_edges(
        "cleanState",
        route_after_clean_state,
        ["generateTitle", "summarizer", END],
    )

    # 终点
    builder.add_edge("generateTitle", END)
    builder.add_edge("summarizer", END)

    return builder


# 编译图
graph = build_graph().compile()
