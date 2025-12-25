"""
查询生成节点

将用户消息转换为搜索引擎友好的查询。

参考 TS: apps/agents/src/web-search/nodes/query-generator.ts
"""

from datetime import datetime
from typing import Any

from langgraph.types import RunnableConfig

from ...utils import format_messages, get_model_from_config
from ..state import WebSearchState


# ============================================
# 提示词
# ============================================


QUERY_GENERATOR_PROMPT = """You're a helpful AI assistant tasked with writing a query to search the web.
You're provided with a list of messages between a user and an AI assistant.
The most recent message from the user is the one you should update to be a more search engine friendly query.

Try to keep the new query as similar to the message as possible, while still being search engine friendly.

Here is the conversation between the user and the assistant, in order of oldest to newest:

<conversation>
{conversation}
</conversation>

<additional_context>
{additional_context}
</additional_context>

Respond ONLY with the search query, and nothing else."""


# ============================================
# 节点函数
# ============================================


async def query_generator(
    state: WebSearchState,
    config: RunnableConfig,
) -> dict[str, Any]:
    """
    查询生成节点

    将用户消息转换为搜索引擎友好的查询字符串。

    参考 TS: apps/agents/src/web-search/nodes/query-generator.ts
    """
    # 1. 创建模型 (使用用户配置的模型)
    model = get_model_from_config(config, temperature=0)

    # 2. 添加当前日期上下文
    # TS 使用 date-fns format(new Date(), "PPpp")
    # Python 等效格式: "Dec 22, 2024, 10:30 AM"
    additional_context = f"The current date is {datetime.now().strftime('%b %d, %Y, %I:%M %p')}"

    # 3. 格式化消息
    formatted_messages = format_messages(state.get("messages", []))

    # 4. 格式化提示词
    formatted_prompt = QUERY_GENERATOR_PROMPT.replace(
        "{conversation}", formatted_messages
    ).replace("{additional_context}", additional_context)

    # 5. 调用模型
    response = await model.ainvoke([("user", formatted_prompt)])

    # 6. 提取查询字符串
    query = response.content if isinstance(response.content, str) else str(response.content)

    return {
        "query": query.strip(),
    }
