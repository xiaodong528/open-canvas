"""
Open Canvas 主代理图

包含核心工作流：生成路径、工件管理、跟进消息等

从 TypeScript 迁移: apps/agents/src/open-canvas/index.ts
"""

from typing import Literal, Union
from langgraph.graph import END, START, StateGraph
from langgraph.store.base import BaseStore
from langgraph.types import RunnableConfig, Send, Command

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
from ..constants import CHARACTER_MAX, DEFAULT_INPUTS
from ..utils import create_ai_message_from_web_results


# ============================================
# 辅助函数
# ============================================


def _calculate_message_chars(state: OpenCanvasState) -> int:
    """计算 _messages 中的总字符数

    参考 TS: apps/agents/src/open-canvas/index.ts:39-57 simpleTokenCalculator
    """
    total_chars = 0
    for msg in state.get("_messages", []):
        content = msg.content
        if isinstance(content, str):
            total_chars += len(content)
        else:
            # 处理非字符串内容 (对应 TS 的 flatMap + "text" in c)
            if isinstance(content, list):
                for c in content:
                    # 支持 dict 和对象两种形式
                    if isinstance(c, dict) and "text" in c:
                        total_chars += len(c.get("text", ""))
                    elif hasattr(c, "text"):
                        total_chars += len(getattr(c, "text", ""))
    return total_chars


def simple_token_calculator(
    state: OpenCanvasState,
) -> Literal["summarizer", "__end__"]:
    """
    基于字符数决定是否触发摘要

    参考 TS: apps/agents/src/open-canvas/index.ts:39-57
    ~ 4 chars per token, max tokens of 75000. 75000 * 4 = 300000
    """
    total_chars = _calculate_message_chars(state)
    if total_chars > CHARACTER_MAX:
        return "summarizer"
    return END


# ============================================
# 路由函数
# ============================================


def route_node(state: OpenCanvasState) -> Send:
    """
    根据 generatePath 设置的 next 字段路由到下一个节点
    
    参考 TS: apps/agents/src/open-canvas/index.ts:20-28
    使用 Send 进行动态路由，传递完整状态到目标节点
    
    Returns:
        Send 对象，指向下一个节点并携带状态
        
    Raises:
        ValueError: 如果 next 字段未设置
    """
    next_node = state.get("next")
    if not next_node:
        raise ValueError("'next' state field not set.")
    
    return Send(next_node, dict(state))


def conditionally_generate_title(
    state: OpenCanvasState,
) -> Literal["generateTitle", "summarizer", "__end__"]:
    """
    清理状态后决定是否生成标题或摘要
    
    参考 TS: apps/agents/src/open-canvas/index.ts:64-72
    
    逻辑:
    - 如果 messages <= 2，生成标题 (首次对话)
    - 否则调用 simpleTokenCalculator 检查是否需要摘要
    """
    messages = state.get("messages", [])
    
    # 首次对话时生成标题
    if len(messages) <= 2:
        return "generateTitle"
    
    # 检查是否需要摘要
    return simple_token_calculator(state)


# ============================================
# 节点函数
# ============================================


def clean_state(state: OpenCanvasState) -> OpenCanvasGraphReturnType:
    """
    清理状态节点 (同步)
    
    参考 TS: apps/agents/src/open-canvas/index.ts:30-34
    重置临时状态字段到默认值，防止污染下一轮路由。
    """
    return DEFAULT_INPUTS.copy()


def route_post_web_search(
    state: OpenCanvasState,
) -> Union[Send, Command]:
    """
    Web 搜索后路由节点
    
    参考 TS: apps/agents/src/open-canvas/index.ts:78-106
    
    逻辑:
    - 如果无搜索结果 → Send 到 generateArtifact/rewriteArtifact
    - 如果有搜索结果 → Command 更新 messages/_messages 并路由
    
    Returns:
        Send: 无搜索结果时直接路由
        Command: 有搜索结果时更新状态并路由
    """
    # 判断是否已有工件
    artifact = state.get("artifact")
    includes_artifacts = (
        artifact is not None 
        and artifact.get("contents") is not None 
        and len(artifact.get("contents", [])) > 1
    )
    target = "rewriteArtifact" if includes_artifacts else "generateArtifact"
    
    # 如果没有搜索结果，直接路由
    web_search_results = state.get("webSearchResults")
    if not web_search_results or len(web_search_results) == 0:
        return Send(target, {
            **state,
            "webSearchEnabled": False,
        })
    
    # 有搜索结果，创建消息并更新状态
    web_results_msg = create_ai_message_from_web_results(web_search_results)
    
    return Command(
        goto=target,
        update={
            "webSearchEnabled": False,
            "messages": [web_results_msg],
            "_messages": [web_results_msg],
        },
    )


# ============================================
# 辅助节点 (子图占位)
# ============================================


async def web_search(
    state: OpenCanvasState,
    config: RunnableConfig,
    *,
    store: BaseStore,
) -> OpenCanvasGraphReturnType:
    """Web 搜索节点 - Phase 6 实现

    NOTE: 当前为占位实现，始终返回空结果。
    真正的 web_search 子图将在 Phase 6 实现，届时此函数将被替换为子图调用。

    参考 TS: apps/agents/src/open-canvas/index.ts 使用 webSearchGraph 子图
    """
    # TODO(Phase 6): 替换为 web_search 子图调用
    return {
        "webSearchResults": [],
    }


async def summarizer(
    state: OpenCanvasState,
    config: RunnableConfig,
    *,
    store: BaseStore,
) -> OpenCanvasGraphReturnType:
    """摘要节点 - 使用子图
    
    TODO Phase 6: 集成 summarizer 子图
    """
    return {}


# ============================================
# 构建图
# ============================================


def build_graph() -> StateGraph:
    """
    构建 Open Canvas 主图
    
    参考 TS: apps/agents/src/open-canvas/index.ts:108-162
    
    节点清单 (15 个):
    - generatePath: 路由决策
    - replyToGeneralInput: 纯对话回复
    - generateArtifact: 创建新工件
    - rewriteArtifact: 重写工件
    - updateArtifact: 代码高亮编辑
    - updateHighlightedText: Markdown 高亮编辑
    - rewriteArtifactTheme: 文本主题变换
    - rewriteCodeArtifactTheme: 代码主题变换
    - customAction: 自定义操作
    - generateFollowup: 跟进消息
    - reflect: 反思/记忆更新
    - cleanState: 状态清理
    - generateTitle: 标题生成
    - summarizer: 对话摘要
    - webSearch: Web 搜索
    - routePostWebSearch: 搜索后路由
    """
    builder = StateGraph(OpenCanvasState)

    # ===== 添加节点 =====

    # 路由节点
    builder.add_node("generatePath", generate_path)

    # 对话节点
    builder.add_node("replyToGeneralInput", reply_to_general_input)
    builder.add_node("generateFollowup", generate_followup)
    builder.add_node("reflect", reflect_node)
    builder.add_node("generateTitle", generate_title_node)

    # 工件操作节点
    builder.add_node("generateArtifact", generate_artifact)
    builder.add_node("rewriteArtifact", rewrite_artifact)
    builder.add_node("updateArtifact", update_artifact)
    builder.add_node("updateHighlightedText", update_highlighted_text)
    builder.add_node("rewriteArtifactTheme", rewrite_artifact_theme)
    builder.add_node("rewriteCodeArtifactTheme", rewrite_code_artifact_theme)
    builder.add_node("customAction", custom_action)

    # 辅助节点
    builder.add_node("webSearch", web_search)
    builder.add_node("routePostWebSearch", route_post_web_search)  # 新增: 搜索后路由节点
    builder.add_node("summarizer", summarizer)
    builder.add_node("cleanState", clean_state)

    # ===== 添加边 =====

    # 入口
    builder.add_edge(START, "generatePath")

    # generatePath 条件路由到各处理节点 (使用 Send 动态路由)
    builder.add_conditional_edges(
        "generatePath",
        route_node,
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

    # Web 搜索 → 路由节点 → 工件处理
    builder.add_edge("webSearch", "routePostWebSearch")
    # routePostWebSearch 节点返回 Send/Command，自动路由到目标节点

    # 一般回复 → cleanState (不需要 followup)
    builder.add_edge("replyToGeneralInput", "cleanState")

    # 工件跟进后 → reflect → cleanState
    builder.add_edge("generateFollowup", "reflect")
    builder.add_edge("reflect", "cleanState")

    # cleanState 后条件路由
    builder.add_conditional_edges(
        "cleanState",
        conditionally_generate_title,
        ["generateTitle", "summarizer", END],
    )

    # 终点
    builder.add_edge("generateTitle", END)
    builder.add_edge("summarizer", END)

    return builder


# 编译图
graph = build_graph().compile()