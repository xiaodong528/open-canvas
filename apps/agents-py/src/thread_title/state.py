"""
标题生成图状态定义
"""

from typing import Annotated, Optional

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

from ..types import ArtifactV3


class ThreadTitleState(TypedDict, total=False):
    """
    标题生成图状态

    用于自动生成对话标题。
    """

    # 消息列表
    messages: Annotated[list[AnyMessage], add_messages]

    # 当前工件
    artifact: Optional[ArtifactV3]
