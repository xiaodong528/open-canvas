"""
Generate Title 节点

从 TypeScript 迁移: apps/agents/src/open-canvas/nodes/generateTitle.ts

功能: 在对话初期触发标题生成图
       仅在 messages.length <= 2 时运行
"""

import os
import logging

from langgraph_sdk import get_client
from langgraph.store.base import BaseStore
from langgraph.types import RunnableConfig

from ..state import OpenCanvasGraphReturnType, OpenCanvasState


logger = logging.getLogger(__name__)


async def generate_title_node(
    state: OpenCanvasState,
    config: RunnableConfig,
    *,
    store: BaseStore,
) -> OpenCanvasGraphReturnType:
    """
    触发标题生成图

    仅在对话初期 (messages.length <= 2) 运行。
    使用 LangGraph SDK 异步启动 thread_title 图，立即执行无延迟。

    Args:
        state: 当前图状态
        config: LangGraph 运行配置
        store: 跨线程存储 (未使用，但保持签名一致)

    Returns:
        空字典 (后台任务无返回值)
    """
    # 检查消息数量，仅在对话初期运行
    messages = state.get("messages", [])
    if len(messages) > 2:
        # 跳过非首次对话 (由 conditional edge 保护，实际上不应到达这里)
        return {}

    try:
        # 创建 LangGraph SDK 客户端
        port = os.environ.get("PORT", "54367")
        langgraph_client = get_client(url=f"http://localhost:{port}")

        # 准备标题生成图的输入
        title_input = {
            "messages": messages,
            "artifact": state.get("artifact"),
        }

        # 准备配置，传递 thread_id 和模型配置
        configurable = config.get("configurable", {})
        title_config = {
            "configurable": {
                "open_canvas_thread_id": configurable.get("thread_id"),
                "customModelName": configurable.get("customModelName"),
                "modelConfig": configurable.get("modelConfig"),
            },
        }

        # 创建新线程
        new_thread = await langgraph_client.threads.create()

        # 创建标题生成运行 (后台运行，不等待完成)
        # afterSeconds=0: 立即执行，不延迟
        await langgraph_client.runs.create(
            thread_id=new_thread["thread_id"],
            assistant_id="thread_title",
            input=title_input,
            config=title_config,
            multitask_strategy="enqueue",
            after_seconds=0,  # 立即执行
        )

    except Exception as e:
        logger.error(f"Failed to call generate title graph: {e}")

    return {}
