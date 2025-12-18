"""
摘要图

压缩长对话历史

TODO Phase 3: 实现完整逻辑
"""

from langgraph.graph import END, START, StateGraph

from .state import SummarizerState


def summarize(state: SummarizerState) -> dict:
    """
    摘要节点 (同步占位)

    压缩长对话历史为摘要消息。

    TODO Phase 3:
    - 使用 Claude 3.5 Sonnet 生成摘要
    - 创建带 OC_SUMMARIZED_MESSAGE_KEY 标记的摘要消息
    - 更新原线程状态
    """
    return {}


def build_graph() -> StateGraph:
    """构建摘要图"""
    builder = StateGraph(SummarizerState)

    builder.add_node("summarize", summarize)

    builder.add_edge(START, "summarize")
    builder.add_edge("summarize", END)

    return builder


graph = build_graph().compile()
