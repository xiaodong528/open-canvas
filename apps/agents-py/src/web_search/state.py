"""
网络搜索图状态定义
"""

from typing import Annotated, Optional

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

from ..types import SearchResult


class WebSearchState(TypedDict, total=False):
    """
    网络搜索图状态

    用于 Exa 网络搜索集成。
    """

    # 消息列表
    messages: Annotated[list[AnyMessage], add_messages]

    # 是否需要搜索
    shouldSearch: Optional[bool]

    # 搜索查询 (单个查询字符串)
    query: Optional[str]

    # 搜索结果
    webSearchResults: Optional[list[SearchResult]]
