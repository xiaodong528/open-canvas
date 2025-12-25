"""
Reflect 节点

从 TypeScript 迁移: apps/agents/src/open-canvas/nodes/reflect.ts

功能: 触发反思图进行后台记忆更新
       使用 5 分钟延迟去抖动，避免频繁调用
"""

import os
import logging

from langgraph_sdk import get_client
from langgraph.store.base import BaseStore
from langgraph.types import RunnableConfig

from ..state import OpenCanvasGraphReturnType, OpenCanvasState


logger = logging.getLogger(__name__)


async def reflect_node(
    state: OpenCanvasState,
    config: RunnableConfig,
    *,
    store: BaseStore,
) -> OpenCanvasGraphReturnType:
    """
    触发反思图进行后台记忆更新

    这是一个后台任务节点，使用 LangGraph SDK 异步启动 reflection 图。
    使用 5 分钟延迟实现去抖动，节省成本并避免重复记忆。

    Args:
        state: 当前图状态
        config: LangGraph 运行配置
        store: 跨线程存储 (未使用，但保持签名一致)

    Returns:
        空字典 (后台任务无返回值)
    """
    try:
        # 创建 LangGraph SDK 客户端
        port = os.environ.get("PORT", "54367")
        langgraph_client = get_client(url=f"http://localhost:{port}")

        # 准备反思图的输入
        reflection_input = {
            "messages": state.get("_messages", []),
            "artifact": state.get("artifact"),
        }

        # 准备配置，传递 assistant_id 和模型配置
        configurable = config.get("configurable", {})
        reflection_config = {
            "configurable": {
                "open_canvas_assistant_id": configurable.get("assistant_id"),
                "customModelName": configurable.get("customModelName"),
                "modelConfig": configurable.get("modelConfig"),
            },
        }

        # 创建新线程
        new_thread = await langgraph_client.threads.create()

        # 创建反思运行 (后台运行，不等待完成)
        # 使用 afterSeconds=300 (5分钟) 实现去抖动:
        # - 如果 5 分钟内有新请求，旧任务将被取消，新任务将重新排队
        # - 这样可以在用户活跃对话时避免频繁调用，节省成本
        await langgraph_client.runs.create(
            thread_id=new_thread["thread_id"],
            assistant_id="reflection",
            input=reflection_input,
            config=reflection_config,
            multitask_strategy="enqueue",
            after_seconds=5 * 60,  # 5 分钟延迟
        )

    except Exception as e:
        logger.error(f"Failed to start reflection: {e}")

    return {}
