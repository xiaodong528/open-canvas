"""
标题生成图

自动生成对话标题

TODO Phase 3: 实现完整逻辑
"""

from langgraph.graph import END, START, StateGraph

from .state import ThreadTitleState


def generate_title(state: ThreadTitleState) -> dict:
    """
    标题生成节点 (同步占位)

    基于对话内容生成简洁的标题。

    TODO Phase 3:
    - 使用 GPT-4o-mini 生成标题
    - 更新 LangGraph 线程元数据
    """
    return {}


def build_graph() -> StateGraph:
    """构建标题生成图"""
    builder = StateGraph(ThreadTitleState)

    builder.add_node("generateTitle", generate_title)

    builder.add_edge(START, "generateTitle")
    builder.add_edge("generateTitle", END)

    return builder


graph = build_graph().compile()
