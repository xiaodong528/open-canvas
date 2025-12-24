"""
Generate Path 节点

从 TypeScript 迁移: apps/agents/src/open-canvas/nodes/generate-path/index.ts

功能: 路由决策 - 分析用户输入和当前状态，决定下一个处理节点

关键功能:
- 上下文文档处理 (PDF/文本文件)
- 跨模型提供商文档格式修复
- URL 内容自动提取 (FireCrawl)
- 消息状态正确返回 (messages/_messages)
"""

import re
import uuid
from typing import Literal

from langchain_core.messages import BaseMessage, HumanMessage, RemoveMessage
from langgraph.store.base import BaseStore
from langgraph.types import RunnableConfig
from pydantic import BaseModel, Field

from ...constants import OC_HIDE_FROM_UI_KEY
from ...types import ArtifactV3, ContextDocument
from ...utils import (
    clean_base64,
    convert_pdf_to_text,
    create_context_document_messages,
    format_artifact_content,
    get_model_config,
    get_model_from_config,
    get_string_from_content,
)
from ..prompts import (
    CURRENT_ARTIFACT_PROMPT,
    NO_ARTIFACT_PROMPT,
    ROUTE_QUERY_OPTIONS_HAS_ARTIFACTS,
    ROUTE_QUERY_OPTIONS_NO_ARTIFACTS,
    ROUTE_QUERY_PROMPT,
)
from ..state import OpenCanvasGraphReturnType, OpenCanvasState


# ============================================
# URL 提取
# ============================================

# URL 正则表达式 - 匹配 TypeScript extractUrls 行为
MARKDOWN_LINK_PATTERN = re.compile(r'\[([^\]]+)\]\((https?://[^\s)]+)\)')
PLAIN_URL_PATTERN = re.compile(
    r'https?://[^\s<\]"\'{}|\\^`]+(?:[^<.,:;"\')\]\s]|(?=\s|$))',
    re.IGNORECASE
)


def extract_urls(text: str) -> list[str]:
    """
    从文本中提取 URLs，支持 markdown 链接格式

    匹配 TypeScript: packages/shared/src/utils/urls.ts

    Args:
        text: 输入文本

    Returns:
        URL 列表 (去重)
    """
    urls = set()

    # 先提取 markdown 链接中的 URL
    def replace_markdown(match):
        urls.add(match.group(2))
        return " " * len(match.group(0))

    processed_text = MARKDOWN_LINK_PATTERN.sub(replace_markdown, text)

    # 再提取纯文本中的 URL
    for url in PLAIN_URL_PATTERN.findall(processed_text):
        urls.add(url)

    return list(urls)


# ============================================
# 上下文文档处理
# ============================================


async def convert_context_document_to_human_message(
    messages: list[BaseMessage],
    config: RunnableConfig,
) -> HumanMessage | None:
    """
    将消息中的上下文文档转换为 HumanMessage

    检查最后一条消息的 additional_kwargs.documents，
    如果存在则转换为正确格式的 HumanMessage。

    匹配 TypeScript: generate-path/documents.ts convertContextDocumentToHumanMessage

    Args:
        messages: 消息列表
        config: LangGraph 配置

    Returns:
        包含文档内容的 HumanMessage，或 None
    """
    if not messages:
        return None

    last_message = messages[-1]
    documents = last_message.additional_kwargs.get("documents", [])

    if not documents:
        return None

    # 使用 create_context_document_messages 获取正确格式的文档消息
    context_messages = await create_context_document_messages(config, documents)
    if not context_messages:
        return None

    # 从 context_messages 中提取 content 项
    content_items = []
    for msg in context_messages:
        if isinstance(msg.get("content"), list):
            content_items.extend(msg["content"])

    return HumanMessage(
        id=str(uuid.uuid4()),
        content=content_items,
        additional_kwargs={OC_HIDE_FROM_UI_KEY: True},
    )


async def fix_mis_formatted_context_doc_message(
    message: HumanMessage,
    config: RunnableConfig,
) -> list[BaseMessage] | None:
    """
    修复跨模型提供商的文档格式

    当用户切换模型提供商时，之前的文档消息格式可能不兼容。
    此函数检测并转换为当前提供商的正确格式。

    匹配 TypeScript: generate-path/documents.ts fixMisFormattedContextDocMessage

    Args:
        message: 需要检查的 HumanMessage
        config: LangGraph 配置

    Returns:
        [RemoveMessage, 新 HumanMessage] 列表，或 None (无需修复)
    """
    if isinstance(message.content, str):
        return None

    model_cfg = get_model_config(config)
    model_provider = model_cfg.get("modelProvider", "")
    new_msg_id = str(uuid.uuid4())
    changes_made = False

    if model_provider == "openai" or model_provider == "azure_openai":
        # 将 Anthropic/Gemini 格式转换为 OpenAI (纯文本)
        new_content = []
        for item in message.content:
            if isinstance(item, dict):
                if item.get("type") == "document" and item.get("source", {}).get("type") == "base64":
                    # Anthropic 格式 -> OpenAI 文本
                    changes_made = True
                    text = await convert_pdf_to_text(item["source"]["data"])
                    new_content.append({"type": "text", "text": text})
                elif item.get("type") == "application/pdf":
                    # Gemini 格式 -> OpenAI 文本
                    changes_made = True
                    text = await convert_pdf_to_text(item["data"])
                    new_content.append({"type": "text", "text": text})
                else:
                    new_content.append(item)
            else:
                new_content.append(item)

        if changes_made:
            return [
                RemoveMessage(id=message.id or ""),
                HumanMessage(
                    id=new_msg_id,
                    content=new_content,
                    additional_kwargs=message.additional_kwargs
                ),
            ]

    elif model_provider == "anthropic":
        # 将 Gemini 格式转换为 Anthropic
        new_content = []
        for item in message.content:
            if isinstance(item, dict) and item.get("type") == "application/pdf":
                # Gemini 格式 -> Anthropic 格式
                changes_made = True
                new_content.append({
                    "type": "document",
                    "source": {
                        "type": "base64",
                        "media_type": item["type"],
                        "data": item["data"],
                    },
                })
            else:
                new_content.append(item)

        if changes_made:
            return [
                RemoveMessage(id=message.id or ""),
                HumanMessage(
                    id=new_msg_id,
                    content=new_content,
                    additional_kwargs=message.additional_kwargs
                ),
            ]

    elif model_provider == "google-genai":
        # 将 Anthropic 格式转换为 Gemini
        new_content = []
        for item in message.content:
            if isinstance(item, dict) and item.get("type") == "document":
                # Anthropic 格式 -> Gemini 格式
                changes_made = True
                new_content.append({
                    "type": "application/pdf",
                    "data": item["source"]["data"],
                })
            else:
                new_content.append(item)

        if changes_made:
            return [
                RemoveMessage(id=message.id or ""),
                HumanMessage(
                    id=new_msg_id,
                    content=new_content,
                    additional_kwargs=message.additional_kwargs
                ),
            ]

    return None


# ============================================
# URL 内容提取 (FireCrawl)
# ============================================

INCLUDE_URL_PROMPT = """You're an advanced AI assistant.
You have been tasked with analyzing the user's message and determining if the user wants the contents of the URL included in their message included in their prompt.
You should ONLY answer 'true' if it is explicitly clear the user included the URL in their message so that its contents would be included in the prompt, otherwise, answer 'false'

Here is the user's message:
<message>
{message}
</message>

Now, given their message, determine whether or not they want the contents of that webpage to be included in the prompt."""


class ShouldIncludeUrlContents(BaseModel):
    """是否应该包含 URL 内容"""
    shouldIncludeUrlContents: bool = Field(
        description="Whether or not to include the contents of the URL in the prompt."
    )


async def fetch_url_contents(url: str) -> dict:
    """
    使用 FireCrawl 抓取 URL 内容

    Args:
        url: 要抓取的 URL

    Returns:
        {"url": url, "pageContent": content}
    """
    try:
        from firecrawl import FirecrawlApp

        app = FirecrawlApp()
        result = app.scrape_url(url, params={"formats": ["markdown"]})
        return {
            "url": url,
            "pageContent": result.get("markdown", "") if result else "",
        }
    except ImportError:
        print("Warning: firecrawl-py not installed, skipping URL content fetch")
        return {"url": url, "pageContent": ""}
    except Exception as e:
        print(f"Failed to fetch URL contents: {e}")
        return {"url": url, "pageContent": ""}


async def include_url_contents(
    message: HumanMessage,
    urls: list[str],
) -> HumanMessage | None:
    """
    使用 LLM 判断是否需要包含 URL 内容，如果需要则抓取

    匹配 TypeScript: generate-path/include-url-contents.ts

    Args:
        message: 用户消息
        urls: 消息中的 URL 列表

    Returns:
        包含 URL 内容的更新后消息，或 None
    """
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI

        prompt_text = message.content if isinstance(message.content, str) else get_string_from_content(message.content)

        # 使用 Gemini 2.0 Flash 判断
        model = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            temperature=0,
        )

        model_with_tool = model.bind_tools(
            [ShouldIncludeUrlContents],
            tool_choice="ShouldIncludeUrlContents",
        )

        formatted_prompt = INCLUDE_URL_PROMPT.replace("{message}", prompt_text)
        result = await model_with_tool.ainvoke([["user", formatted_prompt]])

        if not result.tool_calls:
            return None

        args = result.tool_calls[0].get("args", {})
        if not args.get("shouldIncludeUrlContents"):
            return None

        # 抓取 URL 内容
        url_contents = []
        for url in urls:
            content = await fetch_url_contents(url)
            url_contents.append(content)

        # 将 URL 替换为抓取的内容
        transformed_prompt = prompt_text
        for item in url_contents:
            url = item["url"]
            page_content = item["pageContent"]
            if page_content:  # 只有成功抓取时才替换
                transformed_prompt = transformed_prompt.replace(
                    url,
                    f'<page-contents url="{url}">\n  {page_content}\n  </page-contents>'
                )

        return HumanMessage(
            id=message.id,
            content=transformed_prompt,
            additional_kwargs=message.additional_kwargs,
        )

    except ImportError:
        print("Warning: langchain-google-genai not installed, skipping URL content inclusion")
        return None
    except Exception as e:
        print(f"Failed to handle included URLs: {e}")
        return None


# ============================================
# 辅助函数
# ============================================


def _get_artifact_content(artifact: dict | None) -> dict | None:
    """获取当前工件内容"""
    if not artifact:
        return None

    contents = artifact.get("contents", [])
    current_index = artifact.get("currentIndex", 1)

    for content in contents:
        if content.get("index") == current_index:
            return content

    return contents[-1] if contents else None


def _get_message_content(message: BaseMessage) -> str:
    """获取消息内容字符串"""
    content = message.content
    if isinstance(content, str):
        return content
    elif isinstance(content, list):
        text_parts = []
        for c in content:
            if isinstance(c, dict) and "text" in c:
                text_parts.append(c.get("text", ""))
            elif isinstance(c, str):
                text_parts.append(c)
        return "\n".join(text_parts)
    return ""


def _format_recent_messages(messages: list[BaseMessage], count: int = 3) -> str:
    """格式化最近的消息"""
    recent = messages[-count:] if len(messages) >= count else messages
    formatted = []
    for msg in recent:
        msg_type = msg.type if hasattr(msg, "type") else "unknown"
        content = _get_message_content(msg)
        formatted.append(f"{msg_type}: {content}")
    return "\n\n".join(formatted)


def _format_artifact_for_prompt(content: dict | None) -> str:
    """格式化工件内容用于提示词"""
    if not content:
        return ""

    artifact_type = content.get("type")
    if artifact_type == "text":
        return content.get("fullMarkdown", "")
    elif artifact_type == "code":
        language = content.get("language", "")
        code = content.get("code", "")
        return f"```{language}\n{code}\n```"
    return ""


def _find_existing_doc_message(messages: list[BaseMessage]) -> HumanMessage | None:
    """查找消息中已存在的文档消息"""
    for msg in messages:
        if not isinstance(msg, HumanMessage):
            continue
        if isinstance(msg.content, list):
            for content in msg.content:
                if isinstance(content, dict) and content.get("type") in ("document", "application/pdf"):
                    return msg
    return None


# ============================================
# LLM 动态路由
# ============================================


async def _dynamic_determine_path(
    state: OpenCanvasState,
    config: RunnableConfig,
) -> str:
    """
    使用 LLM 动态决定路由

    Returns:
        路由目标: "replyToGeneralInput", "generateArtifact", 或 "rewriteArtifact"
    """
    internal_messages = state.get("_messages", [])
    artifact = state.get("artifact")
    current_artifact_content = _get_artifact_content(artifact)

    # 确定可用的路由选项
    if current_artifact_content:
        artifact_options = ROUTE_QUERY_OPTIONS_HAS_ARTIFACTS
        artifact_route = "rewriteArtifact"
    else:
        artifact_options = ROUTE_QUERY_OPTIONS_NO_ARTIFACTS
        artifact_route = "generateArtifact"

    # 格式化最近消息
    recent_messages = _format_recent_messages(internal_messages, 3)

    # 格式化当前工件提示词
    if current_artifact_content:
        artifact_text = _format_artifact_for_prompt(current_artifact_content)
        current_artifact_prompt = CURRENT_ARTIFACT_PROMPT.format(
            artifact=artifact_text
        )
    else:
        current_artifact_prompt = NO_ARTIFACT_PROMPT

    # 构建完整提示词
    formatted_prompt = ROUTE_QUERY_PROMPT.replace(
        "{artifactOptions}", artifact_options
    ).replace(
        "{recentMessages}", recent_messages
    ).replace(
        "{currentArtifactPrompt}", current_artifact_prompt
    )

    # 获取模型
    model = get_model_from_config(config, temperature=0, is_tool_calling=True)

    # 创建动态 schema
    route_options = ["replyToGeneralInput", artifact_route]

    class DynamicRouteSchema(BaseModel):
        route: Literal[tuple(route_options)] = Field(  # type: ignore
            description="The route to take based on the user's query."
        )

    # 绑定工具
    model_with_tool = model.bind_tools(
        [DynamicRouteSchema],
        tool_choice="DynamicRouteSchema",
    )

    # 获取上下文文档消息 - 与 TS 版本保持一致
    # 参考: apps/agents/src/open-canvas/nodes/generate-path/dynamic-determine-path.ts:90
    context_document_messages = await create_context_document_messages(config)

    # 调用模型 - 注入上下文文档以提供完整信息给路由决策
    result = await model_with_tool.ainvoke([
        *context_document_messages,
        HumanMessage(content=formatted_prompt),
    ])

    # 提取路由结果
    if result.tool_calls:
        args = result.tool_calls[0].get("args", {})
        route = args.get("route")
        if route in route_options:
            return route

    # 默认路由
    return "replyToGeneralInput"


# ============================================
# 主函数
# ============================================


async def generate_path(
    state: OpenCanvasState,
    config: RunnableConfig,
    *,
    store: BaseStore,
) -> OpenCanvasGraphReturnType:
    """
    路由决策节点

    分析用户输入和当前状态，决定下一个处理节点。

    关键改进 (相对于旧版本):
    - 处理上下文文档 (PDF/文本)
    - 跨模型提供商文档格式修复
    - URL 内容自动提取
    - 每个路由都正确返回 messages/_messages

    Args:
        state: 当前图状态
        config: LangGraph 运行配置
        store: 跨线程存储

    Returns:
        包含 next 和 messages/_messages 的状态更新
    """
    internal_messages = state.get("_messages", [])
    new_messages: list[BaseMessage] = []

    # ===== 上下文文档处理 =====

    # 1. 检查是否有新的上下文文档需要转换
    doc_message = await convert_context_document_to_human_message(
        internal_messages, config
    )

    # 2. 查找已存在的文档消息
    existing_doc_message = _find_existing_doc_message(internal_messages)

    if doc_message:
        new_messages.append(doc_message)
    elif existing_doc_message:
        # 如果存在旧格式文档，尝试修复
        fixed_messages = await fix_mis_formatted_context_doc_message(
            existing_doc_message, config
        )
        if fixed_messages:
            new_messages.extend(fixed_messages)

    # 构建消息返回辅助函数
    def build_messages_return() -> dict:
        if new_messages:
            return {
                "messages": new_messages,
                "_messages": new_messages,
            }
        return {}

    # ===== 硬编码路由优先 =====

    # 检查高亮代码 → updateArtifact
    if state.get("highlightedCode"):
        return {"next": "updateArtifact", **build_messages_return()}

    # 检查高亮文本 → updateHighlightedText
    if state.get("highlightedText"):
        return {"next": "updateHighlightedText", **build_messages_return()}

    # 检查文本主题标志 → rewriteArtifactTheme
    if any([
        state.get("language"),
        state.get("artifactLength"),
        state.get("readingLevel"),
        state.get("regenerateWithEmojis"),
    ]):
        return {"next": "rewriteArtifactTheme", **build_messages_return()}

    # 检查代码主题标志 → rewriteCodeArtifactTheme
    if any([
        state.get("addComments"),
        state.get("addLogs"),
        state.get("portLanguage"),
        state.get("fixBugs"),
    ]):
        return {"next": "rewriteCodeArtifactTheme", **build_messages_return()}

    # 检查自定义操作 → customAction
    if state.get("customQuickActionId"):
        return {"next": "customAction", **build_messages_return()}

    # 检查 Web 搜索 → webSearch
    if state.get("webSearchEnabled"):
        return {"next": "webSearch", **build_messages_return()}

    # ===== URL 内容处理 =====

    new_internal_messages = list(internal_messages)

    if internal_messages:
        last_msg = internal_messages[-1]
        if isinstance(last_msg, HumanMessage):
            last_msg_content = _get_message_content(last_msg)
            message_urls = extract_urls(last_msg_content)

            if message_urls:
                updated_message = await include_url_contents(last_msg, message_urls)
                if updated_message:
                    # 替换最后一条消息
                    new_internal_messages = [
                        updated_message if (hasattr(m, 'id') and m.id == updated_message.id) else m
                        for m in internal_messages
                    ]

    # ===== LLM 动态路由 =====

    route = await _dynamic_determine_path(
        {**state, "_messages": new_internal_messages},
        config,
    )

    # 验证路由结果 - 与 TS 版本保持一致
    # 参考: apps/agents/src/open-canvas/nodes/generate-path/index.ts:150-152
    if not route:
        raise ValueError("Route not found from dynamic path determination")

    # 构建最终返回
    if new_messages:
        return {
            "next": route,
            "messages": new_messages,
            "_messages": [*new_internal_messages, *new_messages],
        }
    elif new_internal_messages != internal_messages:
        # URL 内容被更新了
        return {
            "next": route,
            "_messages": new_internal_messages,
        }
    else:
        return {"next": route}
