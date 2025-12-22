"""
消息分类节点

判断用户消息是否需要进行网络搜索。

参考 TS: apps/agents/src/web-search/nodes/classify-message.ts
"""

from typing import Any

from langchain_anthropic import ChatAnthropic
from pydantic import BaseModel, Field

from ..state import WebSearchState


# ============================================
# 提示词
# ============================================


CLASSIFIER_PROMPT = """You're a helpful AI assistant tasked with classifying the user's latest message.
The user has enabled web search for their conversation, however not all messages should be searched.

Analyze their latest message in isolation and determine if it warrants a web search to include additional context.

<message>
{message}
</message>"""


# ============================================
# Pydantic Schema
# ============================================


class ClassifyMessage(BaseModel):
    """消息分类结果 schema"""

    shouldSearch: bool = Field(
        description="Whether or not to search the web based on the user's latest message."
    )


# ============================================
# 节点函数
# ============================================


async def classify_message(state: WebSearchState) -> dict[str, Any]:
    """
    消息分类节点

    分析用户最新消息，判断是否需要进行网络搜索。

    参考 TS: apps/agents/src/web-search/nodes/classify-message.ts
    """
    # 1. 创建模型并使用结构化输出
    model = ChatAnthropic(
        model="claude-3-5-sonnet-latest",
        temperature=0,
    )
    model_with_schema = model.with_structured_output(
        ClassifyMessage,
        method="function_calling",
    )

    # 2. 获取最新消息内容
    messages = state.get("messages", [])
    if not messages:
        return {"shouldSearch": False}

    latest_message = messages[-1]
    latest_message_content = (
        latest_message.content
        if isinstance(latest_message.content, str)
        else str(latest_message.content)
    )

    # 3. 格式化提示词
    formatted_prompt = CLASSIFIER_PROMPT.replace("{message}", latest_message_content)

    # 4. 调用模型
    response = await model_with_schema.ainvoke([("user", formatted_prompt)])

    return {
        "shouldSearch": response.shouldSearch,
    }
