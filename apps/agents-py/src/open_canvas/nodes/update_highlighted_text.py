"""
Update Highlighted Text 节点

从 TypeScript 迁移: apps/agents/src/open-canvas/nodes/updateHighlightedText.ts

功能: 更新 Markdown 工件中的高亮文本块
"""

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.store.base import BaseStore
from langgraph.types import RunnableConfig

from ..state import OpenCanvasGraphReturnType, OpenCanvasState
from ...utils import (
    create_context_document_messages,
    get_model_config,
    get_model_from_config,
    is_using_o1_mini_model,
)
from ...types import ArtifactMarkdownV3, ArtifactV3


# 更新高亮文本的提示词
UPDATE_HIGHLIGHTED_TEXT_PROMPT = """You are an expert AI writing assistant, tasked with rewriting some text a user has selected. The selected text is nested inside a larger 'block'. You should always respond with ONLY the updated text block in accordance with the user's request.
You should always respond with the full markdown text block, as it will simply replace the existing block in the artifact.
The blocks will be joined later on, so you do not need to worry about the formatting of the blocks, only make sure you keep the formatting and structure of the block you are updating.

# Selected text
{highlightedText}

# Text block
{textBlocks}

Your task is to rewrite the sourounding content to fulfill the users request. The selected text content you are provided above has had the markdown styling removed, so you can focus on the text itself.
However, ensure you ALWAYS respond with the full markdown text block, including any markdown syntax.
NEVER wrap your response in any additional markdown syntax, as this will be handled by the system. Do NOT include a triple backtick wrapping the text block, unless it was present in the original text block.
You should NOT change anything EXCEPT the selected text. The ONLY instance where you may update the sourounding text is if it is necessary to make the selected text make sense.
You should ALWAYS respond with the full, updated text block, including any formatting, e.g newlines, indents, markdown syntax, etc. NEVER add extra syntax or formatting unless the user has specifically requested it.
If you observe partial markdown, this is OKAY because you are only updating a partial piece of the text.

Ensure you reply with the FULL text block, including the updated selected text. NEVER include only the updated selected text, or additional prefixes or suffixes."""


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


def _is_markdown_artifact(content: dict | None) -> bool:
    """检查是否为 Markdown 工件"""
    return content is not None and content.get("type") == "text"


async def update_highlighted_text(
    state: OpenCanvasState,
    config: RunnableConfig,
    *,
    store: BaseStore,
) -> OpenCanvasGraphReturnType:
    """
    更新 Markdown 工件中的高亮文本块

    根据用户请求更新文档中选中的文本块。返回完整的更新后块，
    然后在原文档中替换。

    Args:
        state: 当前图状态
        config: LangGraph 运行配置
        store: 跨线程存储

    Returns:
        包含更新后 artifact 的状态更新
    """
    # 获取模型配置
    model_provider, model_name = get_model_config(config)

    # 选择模型 - 智能模型使用用户配置，否则使用 gpt-4o
    if "openai" in model_provider or "3-5-sonnet" in model_name:
        model = get_model_from_config(config, temperature=0)
    else:
        # 使用更智能的模型
        override_config = {
            **config,
            "configurable": {
                **config.get("configurable", {}),
                "customModelName": "gpt-4o",
            },
        }
        model = get_model_from_config(override_config, temperature=0)

    # 获取当前工件内容
    current_artifact_content = _get_artifact_content(state.get("artifact"))
    if not current_artifact_content:
        raise ValueError("No artifact found")

    if not _is_markdown_artifact(current_artifact_content):
        raise ValueError("Artifact is not markdown content")

    # 检查高亮文本
    highlighted_text = state.get("highlightedText")
    if not highlighted_text:
        raise ValueError("Can not partially regenerate an artifact without a highlight")

    markdown_block = highlighted_text.get("markdownBlock", "")
    selected_text = highlighted_text.get("selectedText", "")
    full_markdown = highlighted_text.get("fullMarkdown", "")

    # 格式化提示词
    formatted_prompt = UPDATE_HIGHLIGHTED_TEXT_PROMPT.format(
        highlightedText=selected_text,
        textBlocks=markdown_block,
    )

    # 获取上下文文档消息
    context_document_messages = await create_context_document_messages(config)

    # 获取最近的用户消息
    internal_messages = state.get("_messages", [])
    if not internal_messages:
        raise ValueError("No messages found")

    recent_user_message = internal_messages[-1]
    if hasattr(recent_user_message, "type") and recent_user_message.type != "human":
        raise ValueError("Expected a human message")

    # 检查是否使用 O1 模型
    is_o1_model = is_using_o1_mini_model(config)

    # 构建消息列表
    if is_o1_model:
        messages = [
            HumanMessage(content=formatted_prompt),
            *context_document_messages,
            recent_user_message,
        ]
    else:
        messages = [
            SystemMessage(content=formatted_prompt),
            *context_document_messages,
            recent_user_message,
        ]

    # 调用模型
    response = await model.ainvoke(messages)
    response_content = str(response.content)

    # 获取工件信息
    artifact = state.get("artifact", {})
    contents = artifact.get("contents", [])
    new_curr_index = len(contents) + 1

    # 查找前一个版本内容
    prev_content = None
    for content in contents:
        if content.get("index") == artifact.get("currentIndex") and content.get("type") == "text":
            prev_content = content
            break

    if not prev_content:
        raise ValueError("Previous content not found")

    # 验证并替换
    if markdown_block not in full_markdown:
        raise ValueError("Selected text not found in current content")

    new_full_markdown = full_markdown.replace(markdown_block, response_content)

    # 创建更新后的工件内容
    updated_artifact_content: ArtifactMarkdownV3 = {
        **prev_content,
        "index": new_curr_index,
        "fullMarkdown": new_full_markdown,
    }

    new_artifact: ArtifactV3 = {
        **artifact,
        "currentIndex": new_curr_index,
        "contents": [*contents, updated_artifact_content],
    }

    return {
        "artifact": new_artifact,
    }
