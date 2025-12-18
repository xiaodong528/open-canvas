"""
反思图

用于生成和存储用户洞察/风格规则到记忆中

TODO Phase 3: 实现完整逻辑
"""

from langgraph.graph import END, START, StateGraph

from .state import ReflectionState


def reflect(state: ReflectionState) -> dict:
    """
    反思节点 (同步占位)

    分析工件和对话，提取用户风格规则和信息。

    TODO Phase 3:
    - 使用 Claude 分析工件和对话
    - 提取 styleRules 和 content
    - 存储到 Supabase store
    """
    return {}


def build_graph() -> StateGraph:
    """构建反思图"""
    builder = StateGraph(ReflectionState)

    builder.add_node("reflect", reflect)

    builder.add_edge(START, "reflect")
    builder.add_edge("reflect", END)

    return builder


graph = build_graph().compile()
