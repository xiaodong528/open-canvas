"""
网络搜索图

基于 Exa 的网络搜索集成

TODO Phase 3: 实现完整逻辑
"""

from langgraph.graph import END, START, StateGraph

from .state import WebSearchState


def classify_message(state: WebSearchState) -> dict:
    """
    消息分类节点 (同步占位)

    决定是否需要进行网络搜索。

    TODO Phase 3:
    - 分析用户消息判断是否需要搜索
    - 返回 shouldSearch 布尔值
    """
    return {"shouldSearch": False}


def query_generator(state: WebSearchState) -> dict:
    """
    查询生成节点 (同步占位)

    生成网络搜索查询。

    TODO Phase 3:
    - 基于用户消息生成搜索查询
    - 返回 searchQueries 列表
    """
    return {"searchQueries": []}


def search(state: WebSearchState) -> dict:
    """
    搜索执行节点 (同步占位)

    执行 Exa 网络搜索。

    TODO Phase 3:
    - 使用 Exa API 执行搜索
    - 返回 webSearchResults
    """
    return {"webSearchResults": []}


def route_search(state: WebSearchState) -> str:
    """路由：是否需要搜索"""
    if state.get("shouldSearch"):
        return "queryGenerator"
    return END


def build_graph() -> StateGraph:
    """构建网络搜索图"""
    builder = StateGraph(WebSearchState)

    builder.add_node("classifyMessage", classify_message)
    builder.add_node("queryGenerator", query_generator)
    builder.add_node("search", search)

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
