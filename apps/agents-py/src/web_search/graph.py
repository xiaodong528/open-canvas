"""
网络搜索图

基于 Exa 的网络搜索集成

参考 TS: apps/agents/src/web-search/index.ts
"""

from langgraph.graph import END, START, StateGraph

from .nodes import classify_message, query_generator, search
from .state import WebSearchState


# ============================================
# 路由函数
# ============================================


def route_search(state: WebSearchState) -> str:
    """
    路由：是否需要搜索

    根据 classifyMessage 节点的结果决定是否执行搜索。
    """
    if state.get("shouldSearch"):
        return "queryGenerator"
    return END


# ============================================
# 图构建
# ============================================


def build_graph() -> StateGraph:
    """构建网络搜索图"""
    builder = StateGraph(WebSearchState)

    # 添加节点
    builder.add_node("classifyMessage", classify_message)
    builder.add_node("queryGenerator", query_generator)
    builder.add_node("search", search)

    # 添加边
    builder.add_edge(START, "classifyMessage")
    builder.add_conditional_edges(
        "classifyMessage",
        route_search,
        ["queryGenerator", END],
    )
    builder.add_edge("queryGenerator", "search")
    builder.add_edge("search", END)

    return builder


graph = build_graph().compile()
graph.name = "Web Search Graph"
