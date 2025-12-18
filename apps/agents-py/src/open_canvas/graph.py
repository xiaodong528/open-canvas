"""
Open Canvas 主代理图

包含核心工作流：生成路径、工件管理、跟进消息等

TODO Phase 2: 实现完整节点逻辑
"""

from langgraph.graph import END, START, StateGraph

from .state import OpenCanvasState


# ============================================
# 占位节点函数 - Phase 2 将实现完整逻辑
# ============================================


def generate_path(state: OpenCanvasState) -> dict:
    """
    路由决策节点 (同步占位)

    分析用户输入和当前状态，决定下一个处理节点。

    TODO Phase 2:
    - 检查 highlightedCode → updateArtifact
    - 检查 highlightedText → updateHighlightedText
    - 检查 language/artifactLength → rewriteArtifactTheme
    - 检查 addComments/addLogs → rewriteCodeArtifactTheme
    - 检查 customQuickActionId → customAction
    - 检查 webSearchEnabled → webSearch
    - 默认 → dynamicDeterminePath (LLM 决策)
    """
    # 占位实现：直接返回到 replyToGeneralInput
    return {"next": "replyToGeneralInput"}


def reply_to_general_input(state: OpenCanvasState) -> dict:
    """
    普通输入回复节点 (同步占位)

    处理不需要工件操作的一般对话。

    TODO Phase 2: 实现 LLM 调用和响应生成
    """
    from langchain_core.messages import AIMessage

    return {
        "messages": [
            AIMessage(
                content="Hello! I'm the Open Canvas assistant. How can I help you today?",
                id="placeholder-response",
            )
        ]
    }


def clean_state(state: OpenCanvasState) -> dict:
    """
    清理状态节点 (同步)

    重置临时状态字段到默认值。
    """
    from ..utils import DEFAULT_INPUTS

    return DEFAULT_INPUTS.copy()


# ============================================
# 构建图
# ============================================


def build_graph() -> StateGraph:
    """构建 Open Canvas 主图"""
    builder = StateGraph(OpenCanvasState)

    # 添加节点
    builder.add_node("generatePath", generate_path)
    builder.add_node("replyToGeneralInput", reply_to_general_input)
    builder.add_node("cleanState", clean_state)

    # 添加边
    builder.add_edge(START, "generatePath")
    builder.add_edge("generatePath", "replyToGeneralInput")
    builder.add_edge("replyToGeneralInput", "cleanState")
    builder.add_edge("cleanState", END)

    return builder


# 编译图
graph = build_graph().compile()
