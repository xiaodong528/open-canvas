"""
搜索节点

使用 Exa API 执行网络搜索。

参考 TS: apps/agents/src/web-search/nodes/search.ts
"""

import os
from typing import Any

from exa_py import Exa

from ...types import SearchResult
from ..state import WebSearchState


# ============================================
# 节点函数
# ============================================


async def search(state: WebSearchState) -> dict[str, Any]:
    """
    搜索节点

    使用 Exa API 执行网络搜索并返回结果。

    参考 TS: apps/agents/src/web-search/nodes/search.ts
    """
    # 1. 创建 Exa 客户端
    exa_api_key = os.environ.get("EXA_API_KEY", "")
    exa = Exa(api_key=exa_api_key)

    # 2. 获取查询 (使用 query_generator 生成的查询，或回退到最新消息)
    query = state.get("query")
    if not query:
        messages = state.get("messages", [])
        if messages:
            latest_message = messages[-1]
            query = (
                latest_message.content
                if isinstance(latest_message.content, str)
                else str(latest_message.content)
            )
        else:
            return {"webSearchResults": []}

    # 3. 执行搜索
    # 使用 search_and_contents 获取内容
    results = exa.search_and_contents(
        query,
        num_results=5,
        type="auto",
        text=True,  # 获取文本内容
    )

    # 4. 转换为 SearchResult 格式 (匹配 TypeScript ExaMetadata)
    web_search_results: list[SearchResult] = []
    for result in results.results:
        search_result: SearchResult = {
            "pageContent": result.text or "",
            "metadata": {
                "id": result.id,
                "url": result.url,
                "title": result.title or "",
                "author": getattr(result, "author", None),
                "publishedDate": getattr(result, "publishedDate", None),
                "image": getattr(result, "image", None),
                "favicon": getattr(result, "favicon", None),
            },
        }
        web_search_results.append(search_result)

    return {
        "webSearchResults": web_search_results,
    }
