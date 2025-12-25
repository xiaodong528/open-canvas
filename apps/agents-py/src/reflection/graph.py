"""
反思图

用于生成和存储用户洞察/风格规则到记忆中

参考 TS: apps/agents/src/reflection/index.ts
"""

from typing import Any

from langchain_core.messages import AnyMessage
from langgraph.graph import END, START, StateGraph
from langgraph.store.base import BaseStore
from langgraph.types import RunnableConfig
from pydantic import BaseModel, Field

from ..types import ArtifactCodeV3, ArtifactMarkdownV3, ArtifactV3
from ..utils import format_reflections, get_model_from_config
from .prompts import REFLECT_SYSTEM_PROMPT, REFLECT_USER_PROMPT
from .state import ReflectionState


# ============================================
# Pydantic 工具 Schema
# ============================================


class GenerateReflections(BaseModel):
    """生成用户反思的工具 schema"""

    styleRules: list[str] = Field(
        description="The complete new list of style rules and guidelines."
    )
    content: list[str] = Field(
        description="The complete new list of memories/facts about the user."
    )


# ============================================
# 辅助函数
# ============================================


def get_artifact_content(artifact: ArtifactV3) -> ArtifactMarkdownV3 | ArtifactCodeV3 | None:
    """获取工件的当前内容"""
    contents = artifact.get("contents", [])
    if not contents:
        return None

    current_index = artifact.get("currentIndex", len(contents) - 1)
    if 0 <= current_index < len(contents):
        return contents[current_index]

    return contents[-1] if contents else None


def is_artifact_markdown_content(
    content: ArtifactMarkdownV3 | ArtifactCodeV3,
) -> bool:
    """判断工件内容是否为 Markdown 类型"""
    return content.get("type") == "text"


def format_conversation(messages: list[AnyMessage]) -> str:
    """格式化对话为 XML 格式"""
    formatted = []
    for msg in messages:
        msg_type = msg.type if hasattr(msg, "type") else "unknown"
        content = msg.content if isinstance(msg.content, str) else ""

        # 处理列表类型的 content
        if not isinstance(msg.content, str) and hasattr(msg.content, "__iter__"):
            content = "\n".join(
                c.get("text", "") for c in msg.content if isinstance(c, dict) and "text" in c
            )

        formatted.append(f"<{msg_type}>\n{content}\n</{msg_type}>")

    return "\n\n".join(formatted)


# ============================================
# 节点函数
# ============================================


async def reflect(
    state: ReflectionState,
    config: RunnableConfig,
    *,
    store: BaseStore,
) -> dict[str, Any]:
    """
    反思节点

    分析工件和对话，提取用户风格规则和信息，存储到 Store。

    参考 TS: apps/agents/src/reflection/index.ts
    """
    # 1. 获取 assistant_id
    configurable = config.get("configurable", {})
    assistant_id = configurable.get("open_canvas_assistant_id")
    if not assistant_id:
        raise ValueError("`open_canvas_assistant_id` not found in configurable")

    # 2. 从 Store 读取现有记忆
    memory_namespace = ("memories", assistant_id)
    memory_key = "reflection"
    memories = await store.aget(memory_namespace, memory_key)

    memories_as_string = (
        format_reflections(memories.value)
        if memories and memories.value
        else "No reflections found."
    )

    # 3. 格式化工件内容
    artifact_content = None
    if state.get("artifact"):
        artifact_content = get_artifact_content(state["artifact"])

    artifact_text = "No artifact found."
    if artifact_content:
        if is_artifact_markdown_content(artifact_content):
            artifact_text = artifact_content.get("fullMarkdown", "")
        else:
            artifact_text = artifact_content.get("code", "")

    # 4. 创建模型并绑定工具 (使用用户配置的模型)
    model = get_model_from_config(config, temperature=0, is_tool_calling=True)
    model_with_tool = model.bind_tools(
        [GenerateReflections],
        tool_choice="GenerateReflections",
    )

    # 5. 格式化提示词
    formatted_system_prompt = REFLECT_SYSTEM_PROMPT.replace(
        "{artifact}", artifact_text
    ).replace("{reflections}", memories_as_string)

    formatted_user_prompt = REFLECT_USER_PROMPT.replace(
        "{conversation}", format_conversation(state.get("messages", []))
    )

    # 6. 调用模型
    result = await model_with_tool.ainvoke([
        {"role": "system", "content": formatted_system_prompt},
        {"role": "user", "content": formatted_user_prompt},
    ])

    # 7. 提取工具调用结果
    tool_calls = result.tool_calls if hasattr(result, "tool_calls") else []
    if not tool_calls:
        print("FAILED TO GENERATE TOOL CALL", result)
        raise ValueError("Reflection tool call failed.")

    reflection_tool_call = tool_calls[0]
    new_memories = {
        "styleRules": reflection_tool_call.get("args", {}).get("styleRules", []),
        "content": reflection_tool_call.get("args", {}).get("content", []),
    }

    # 8. 存储新反思
    await store.aput(memory_namespace, memory_key, new_memories)

    return {}


# ============================================
# 图构建
# ============================================


def build_graph() -> StateGraph:
    """构建反思图"""
    builder = StateGraph(ReflectionState)

    builder.add_node("reflect", reflect)

    builder.add_edge(START, "reflect")
    builder.add_edge("reflect", END)

    return builder


graph = build_graph().compile()
