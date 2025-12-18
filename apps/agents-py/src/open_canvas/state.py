"""
Open Canvas 主图状态定义

重要: 所有字段名必须保持 camelCase 与前端/TypeScript 完全一致
LangGraph Server 不会自动转换 snake_case ↔ camelCase
"""

from typing import Annotated, Any, Optional

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

from ..types import (
    ArtifactLengthOptions,
    ArtifactV3,
    CodeHighlight,
    LanguageOptions,
    ProgrammingLanguageOptions,
    ReadingLevelOptions,
    SearchResult,
    TextHighlight,
)
from ..utils import OC_SUMMARIZED_MESSAGE_KEY


# ============================================
# 自定义 Reducer - 处理摘要消息清空历史
# ============================================


def _is_summary_message(msg: Any) -> bool:
    """
    检查消息是否为摘要消息

    Args:
        msg: 要检查的消息

    Returns:
        True 如果是摘要消息
    """
    if not isinstance(msg, dict) and not hasattr(msg, "additional_kwargs"):
        return False

    # 检查 additional_kwargs
    additional_kwargs = getattr(msg, "additional_kwargs", None)
    if additional_kwargs is None and isinstance(msg, dict):
        additional_kwargs = msg.get("additional_kwargs", {})

    if additional_kwargs and additional_kwargs.get(OC_SUMMARIZED_MESSAGE_KEY) is True:
        return True

    # 检查 kwargs.additional_kwargs (某些序列化格式)
    kwargs = getattr(msg, "kwargs", None)
    if kwargs is None and isinstance(msg, dict):
        kwargs = msg.get("kwargs", {})

    if kwargs:
        nested_kwargs = kwargs.get("additional_kwargs", {})
        if nested_kwargs.get(OC_SUMMARIZED_MESSAGE_KEY) is True:
            return True

    return False


def _messages_reducer(
    left: list[AnyMessage],
    right: list[AnyMessage] | AnyMessage,
) -> list[AnyMessage]:
    """
    特殊 reducer: 遇到摘要消息时清空历史再追加

    这是保持与 TypeScript 版本行为一致的关键逻辑。
    当收到摘要消息时，清空现有消息列表，只保留摘要消息。
    这样可以防止上下文无限增长导致成本爆炸。

    Args:
        left: 现有消息列表
        right: 新消息（可以是单个消息或列表）

    Returns:
        更新后的消息列表
    """
    right_list = right if isinstance(right, list) else [right]

    if not right_list:
        return add_messages(left, right_list)

    # 检查最后一条消息是否为摘要消息
    latest_msg = right_list[-1]
    if _is_summary_message(latest_msg):
        # 摘要消息：清空历史，只保留新消息
        return add_messages([], right_list)

    # 正常情况：追加新消息
    return add_messages(left, right_list)


# ============================================
# 主图状态 - 字段名保持 camelCase
# ============================================


class OpenCanvasState(TypedDict, total=False):
    """
    Open Canvas 主图状态

    重要: 所有字段名必须与 TypeScript 版本完全一致 (camelCase)
    LangGraph Server 不会自动转换 snake_case ↔ camelCase

    Attributes:
        messages: 用户可见的完整消息列表
        _messages: 内部消息列表，包含摘要和隐藏消息
        highlightedCode: 用户高亮的代码区域
        highlightedText: 用户高亮的文本区域
        artifact: 当前工件（支持版本控制）
        next: 下一个路由目标节点
        language: 翻译目标语言
        artifactLength: 工件长度选项
        regenerateWithEmojis: 是否使用表情符号重新生成
        readingLevel: 阅读水平
        addComments: 是否添加代码注释
        addLogs: 是否添加日志语句
        portLanguage: 代码移植目标语言
        fixBugs: 是否修复 bug
        customQuickActionId: 自定义快捷操作 ID
        webSearchEnabled: 是否启用网络搜索
        webSearchResults: 网络搜索结果
    """

    # 消息列表 - 使用 add_messages reducer
    messages: Annotated[list[AnyMessage], add_messages]

    # 内部消息 - 使用自定义 reducer 处理摘要
    _messages: Annotated[list[AnyMessage], _messages_reducer]

    # 高亮代码/文本 - camelCase
    highlightedCode: Optional[CodeHighlight]
    highlightedText: Optional[TextHighlight]

    # 文档
    artifact: Optional[ArtifactV3]

    # 路由
    next: Optional[str]

    # 语言选项 - camelCase
    language: Optional[LanguageOptions]
    artifactLength: Optional[ArtifactLengthOptions]
    regenerateWithEmojis: Optional[bool]
    readingLevel: Optional[ReadingLevelOptions]

    # 代码选项 - camelCase
    addComments: Optional[bool]
    addLogs: Optional[bool]
    portLanguage: Optional[ProgrammingLanguageOptions]
    fixBugs: Optional[bool]

    # 自定义操作 - camelCase
    customQuickActionId: Optional[str]

    # 网络搜索 - camelCase
    webSearchEnabled: Optional[bool]
    webSearchResults: Optional[list[SearchResult]]


# 返回类型别名
OpenCanvasGraphReturnType = dict[str, Any]
