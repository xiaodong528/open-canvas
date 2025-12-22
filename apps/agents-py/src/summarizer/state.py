"""
摘要图状态定义
"""

from typing import Annotated, Optional

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


class SummarizerState(TypedDict, total=False):
    """
    摘要图状态

    用于压缩长对话历史。
    """

    # 消息列表
    messages: Annotated[list[AnyMessage], add_messages]

    # 内部消息列表
    _messages: Annotated[list[AnyMessage], add_messages]

    # 线程 ID (用于更新线程状态)
    threadId: Optional[str]
