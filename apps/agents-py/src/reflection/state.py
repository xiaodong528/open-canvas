"""
反思图状态定义
"""

from typing import Annotated, Any, Optional

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

from ..types import ArtifactV3


class ReflectionState(TypedDict, total=False):
    """
    反思图状态

    用于生成和存储用户洞察/风格规则到记忆中。
    """

    # 消息列表
    messages: Annotated[list[AnyMessage], add_messages]

    # 当前工件
    artifact: Optional[ArtifactV3]
