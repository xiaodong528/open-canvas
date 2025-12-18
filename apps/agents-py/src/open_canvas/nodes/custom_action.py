"""
Custom Action 节点

从 TypeScript 迁移: apps/agents/src/open-canvas/nodes/customAction.ts

功能: 执行用户自定义的快捷操作
"""

from langchain_core.messages import BaseMessage, HumanMessage
from langgraph.store.base import BaseStore
from langgraph.types import RunnableConfig

from ..state import OpenCanvasGraphReturnType, OpenCanvasState
from ...utils import (
    ensure_store_in_config,
    format_reflections,
    get_model_from_config,
)
from ...types import ArtifactCodeV3, ArtifactMarkdownV3, ArtifactV3, Reflections


# 快捷操作提示词
CUSTOM_QUICK_ACTION_ARTIFACT_CONTENT_PROMPT = """Here is the full artifact content the user has generated, and is requesting you rewrite according to their custom instructions:
<artifact>
{artifactContent}
</artifact>"""

CUSTOM_QUICK_ACTION_ARTIFACT_PROMPT_PREFIX = """You are an AI assistant tasked with rewriting a users generated artifact.
They have provided custom instructions on how you should manage rewriting the artifact. The custom instructions are wrapped inside the <custom-instructions> tags.

Use this context about the application the user is interacting with when generating your response:
<app-context>
The name of the application is "Open Canvas". Open Canvas is a web application where users have a chat window and a canvas to display an artifact.
Artifacts can be any sort of writing content, emails, code, or other creative writing work. Think of artifacts as content, or writing you might find on you might find on a blog, Google doc, or other writing platform.
Users only have a single artifact per conversation, however they have the ability to go back and fourth between artifact edits/revisions.
</app-context>"""

CUSTOM_QUICK_ACTION_CONVERSATION_CONTEXT = """Here is the last 5 (or less) messages in the chat history between you and the user:
<conversation>
{conversation}
</conversation>"""

REFLECTIONS_QUICK_ACTION_PROMPT = """The following are reflections on the user's style guidelines and general memories/facts about the user.
Use these reflections as context when generating your response.
<reflections>
{reflections}
</reflections>"""


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


def _format_messages(messages: list[BaseMessage]) -> str:
    """格式化消息列表为字符串"""
    formatted = []
    for msg in messages:
        msg_type = msg.type if hasattr(msg, "type") else "unknown"
        content = msg.content if isinstance(msg.content, str) else ""

        # 处理复杂内容结构
        if not isinstance(msg.content, str) and hasattr(msg.content, "__iter__"):
            content = "\n".join(
                c.get("text", "")
                for c in msg.content
                if isinstance(c, dict) and "text" in c
            )

        formatted.append(f"<{msg_type}>\n{content}\n</{msg_type}>")

    return "\n".join(formatted)


async def custom_action(
    state: OpenCanvasState,
    config: RunnableConfig,
    *,
    store: BaseStore,
) -> OpenCanvasGraphReturnType:
    """
    执行用户自定义的快捷操作

    从 Store 加载自定义操作定义，动态构建提示词，
    然后调用 LLM 重写工件。

    Args:
        state: 当前图状态
        config: LangGraph 运行配置
        store: 跨线程存储

    Returns:
        包含更新后 artifact 的状态更新
    """
    # 检查自定义操作 ID
    custom_quick_action_id = state.get("customQuickActionId")
    if not custom_quick_action_id:
        raise ValueError("No custom quick action ID found.")

    # 获取模型
    small_model = get_model_from_config(config, temperature=0.5)

    # 获取配置信息
    assistant_id = config.get("configurable", {}).get("assistant_id")
    user_id = config.get("configurable", {}).get("supabase_user_id")

    if not assistant_id:
        raise ValueError("`assistant_id` not found in configurable")
    if not user_id:
        raise ValueError("`user.id` not found in configurable")

    # 定义命名空间
    custom_actions_namespace = ("custom_actions", user_id)
    actions_key = "actions"
    memory_namespace = ("memories", assistant_id)
    memory_key = "reflection"

    # 并行获取自定义操作和记忆
    custom_actions_item = await store.aget(custom_actions_namespace, actions_key)
    memories = await store.aget(memory_namespace, memory_key)

    # 验证自定义操作存在
    if not custom_actions_item or not custom_actions_item.value:
        raise ValueError("No custom actions found.")

    custom_quick_action = custom_actions_item.value.get(custom_quick_action_id)
    if not custom_quick_action:
        raise ValueError(
            f"No custom quick action found from ID {custom_quick_action_id}"
        )

    # 获取当前工件内容
    current_artifact_content = _get_artifact_content(state.get("artifact"))

    # 构建提示词
    formatted_prompt = f"<custom-instructions>\n{custom_quick_action.get('prompt', '')}\n</custom-instructions>"

    # 可选: 添加反思/记忆
    if custom_quick_action.get("includeReflections") and memories and memories.value:
        memories_as_string = format_reflections(memories.value)
        reflections_prompt = REFLECTIONS_QUICK_ACTION_PROMPT.format(
            reflections=memories_as_string
        )
        formatted_prompt += f"\n\n{reflections_prompt}"

    # 可选: 添加前缀
    if custom_quick_action.get("includePrefix"):
        formatted_prompt = f"{CUSTOM_QUICK_ACTION_ARTIFACT_PROMPT_PREFIX}\n\n{formatted_prompt}"

    # 可选: 添加最近对话历史
    if custom_quick_action.get("includeRecentHistory"):
        internal_messages = state.get("_messages", [])
        recent_messages = internal_messages[-5:]  # 最后 5 条消息
        formatted_conversation = _format_messages(recent_messages)
        conversation_context = CUSTOM_QUICK_ACTION_CONVERSATION_CONTEXT.format(
            conversation=formatted_conversation
        )
        formatted_prompt += f"\n\n{conversation_context}"

    # 添加工件内容
    if current_artifact_content:
        if _is_markdown_artifact(current_artifact_content):
            artifact_content = current_artifact_content.get("fullMarkdown", "")
        else:
            artifact_content = current_artifact_content.get("code", "")
    else:
        artifact_content = "No artifacts generated yet."

    artifact_prompt = CUSTOM_QUICK_ACTION_ARTIFACT_CONTENT_PROMPT.format(
        artifactContent=artifact_content
    )
    formatted_prompt += f"\n\n{artifact_prompt}"

    # 调用模型
    new_artifact_values = await small_model.ainvoke([
        HumanMessage(content=formatted_prompt)
    ])

    # 如果没有当前工件，返回空
    if not current_artifact_content:
        return {}

    # 创建新工件内容
    artifact = state.get("artifact", {})
    contents = artifact.get("contents", [])
    new_index = len(contents) + 1

    if _is_markdown_artifact(current_artifact_content):
        new_artifact_content: ArtifactMarkdownV3 = {
            **current_artifact_content,
            "index": new_index,
            "fullMarkdown": str(new_artifact_values.content),
        }
    else:
        new_artifact_content: ArtifactCodeV3 = {
            **current_artifact_content,
            "index": new_index,
            "code": str(new_artifact_values.content),
        }

    new_artifact: ArtifactV3 = {
        **artifact,
        "currentIndex": new_index,
        "contents": [*contents, new_artifact_content],
    }

    return {
        "artifact": new_artifact,
    }
