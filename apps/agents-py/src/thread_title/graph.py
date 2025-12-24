"""
标题生成图

自动生成对话标题并更新线程元数据

参考 TS: apps/agents/src/thread-title/index.ts
"""

import os
from typing import Any

from langchain_core.messages import AnyMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from langgraph.types import RunnableConfig
from pydantic import BaseModel, Field

from ..types import ArtifactCodeV3, ArtifactMarkdownV3, ArtifactV3
from .prompts import TITLE_SYSTEM_PROMPT, TITLE_USER_PROMPT
from .state import ThreadTitleState


# ============================================
# Pydantic 工具 Schema
# ============================================


class GenerateTitle(BaseModel):
    """生成对话标题的工具 schema"""

    title: str = Field(description="The generated title for the conversation.")


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


async def generate_title(
    state: ThreadTitleState,
    config: RunnableConfig,
) -> dict[str, Any]:
    """
    标题生成节点

    基于对话内容生成简洁的标题，并更新线程元数据。

    参考 TS: apps/agents/src/thread-title/index.ts
    """
    # 1. 获取 thread_id
    configurable = config.get("configurable", {})
    thread_id = configurable.get("open_canvas_thread_id")

    if not thread_id:
        raise ValueError("open_canvas_thread_id not found in configurable")

    # 2. 创建模型并绑定工具
    model = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0,
    )
    model_with_tool = model.bind_tools(
        [GenerateTitle],
        tool_choice="GenerateTitle",
    )

    # 3. 格式化工件上下文
    artifact_context = "No artifact was generated during this conversation."
    if state.get("artifact"):
        artifact_content = get_artifact_content(state["artifact"])
        if artifact_content:
            if is_artifact_markdown_content(artifact_content):
                content_text = artifact_content.get("fullMarkdown", "")
            else:
                content_text = artifact_content.get("code", "")
            artifact_context = (
                f"An artifact was generated during this conversation:\n\n{content_text}"
            )

    # 4. 格式化提示词
    formatted_user_prompt = TITLE_USER_PROMPT.replace(
        "{conversation}", format_conversation(state.get("messages", []))
    ).replace("{artifact_context}", artifact_context)

    # 5. 调用模型
    result = await model_with_tool.ainvoke([
        {"role": "system", "content": TITLE_SYSTEM_PROMPT},
        {"role": "user", "content": formatted_user_prompt},
    ])

    # 6. 提取工具调用结果
    tool_calls = result.tool_calls if hasattr(result, "tool_calls") else []
    if not tool_calls:
        print("FAILED TO GENERATE TOOL CALL", result)
        raise ValueError("Title generation tool call failed.")

    title_tool_call = tool_calls[0]
    title = title_tool_call.get("args", {}).get("title", "Untitled")

    # 7. 使用 LangGraph SDK Client 更新线程元数据
    from langgraph_sdk import get_client

    port = os.environ.get("PORT", "54367")
    client = get_client(url=f"http://localhost:{port}")

    await client.threads.update(
        thread_id,
        metadata={"thread_title": title},
    )

    return {}


# ============================================
# 图构建
# ============================================


def build_graph() -> StateGraph:
    """构建标题生成图"""
    builder = StateGraph(ThreadTitleState)

    builder.add_node("generateTitle", generate_title)

    builder.add_edge(START, "generateTitle")
    builder.add_edge("generateTitle", END)

    return builder


graph = build_graph().compile()
