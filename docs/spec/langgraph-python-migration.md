# LangGraph TypeScript → Python SDK 重构方案

> **创建日期**: 2025-12-16
> **状态**: 进行中 (Phase 1 已完成)
> **优先级**: 紧急

## 目录

- [1. 项目背景](#1-项目背景)
- [2. 架构设计](#2-架构设计)
- [3. Python 项目结构](#3-python-项目结构)
- [4. 类型映射](#4-类型映射)
- [5. 依赖配置](#5-依赖配置)
- [6. 部署与切换](#6-部署与切换)
- [7. 迁移计划](#7-迁移计划)
- [8. 验证清单](#8-验证清单)

---

## 1. 项目背景

### 1.1 需求概述

| 维度               | 决策                                                         |
| ------------------ | ------------------------------------------------------------ |
| **动机**     | 需要与现有 Python 服务集成                                   |
| **策略**     | **完全替换** - Python 替代 TS 成为唯一后端             |
| **代码保留** | `apps/agents/` (TS) 保留作为参考，新建 `apps/agents-py/` |
| **通信方式** | LangGraph SDK 保持不变                                       |
| **部署环境** | 自托管 Docker/K8s                                            |
| **优先级**   | 紧急 - 尽快完成核心功能                                      |
| **关键要求** | 前端无缝连接 Python 后端                                     |

### 1.2 当前实现规模

| 组件                         | 文件数   | 描述                                 |
| ---------------------------- | -------- | ------------------------------------ |
| **open-canvas** (主图) | 18 文件  | 核心代理，包含路由、生成、重写等节点 |
| **reflection**         | 3 文件   | 用户洞察/风格规则记忆                |
| **thread-title**       | 3 文件   | 对话标题生成                         |
| **summarizer**         | 2 文件   | 对话压缩                             |
| **web-search**         | 5 文件   | Exa 网络搜索                         |
| **共享工具**           | 1 文件   | utils.ts                             |
| **总计**               | ~32 文件 | 5 个 LangGraph 图                    |

### 1.3 技术可行性评估

| 方面       | TS → Python 难度 | 备注                            |
| ---------- | ----------------- | ------------------------------- |
| State 定义 | 🟢 低             | TypedDict → Pydantic/TypedDict |
| 节点函数   | 🟢 低             | 函数逻辑直接翻译                |
| LLM 调用   | 🟢 低             | langchain-* 包接口一致          |
| Graph 定义 | 🟢 低             | StateGraph API 几乎相同         |
| 流式传输   | 🟡 中             | 需要调整 streaming 机制         |
| 前端集成   | 🟡 中             | LangGraph SDK 需验证兼容性      |

---

## 2. 架构设计

### 2.1 目标架构（Python 单后端）

```
┌─────────────────────────────────────────────────────────┐
│                    Next.js Frontend                      │
│                   (apps/web - port 3000)                 │
│                                                         │
│   NEXT_PUBLIC_API_URL = http://localhost:54367          │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│                  LangGraph Server (Python)               │
│                      Port: 54367                         │
│                                                         │
│  apps/agents-py/                                        │
│  └── src/                                               │
│      ├── open_canvas/    # 主代理图                      │
│      ├── reflection/     # 反思图                        │
│      ├── thread_title/   # 标题生成图                    │
│      ├── summarizer/     # 摘要图                        │
│      └── web_search/     # 网络搜索图                    │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│  apps/agents/ (TypeScript) - 保留作为参考，不再运行       │
│  └── src/                                               │
│      ├── open-canvas/                                   │
│      ├── reflection/                                    │
│      ├── thread-title/                                  │
│      ├── summarizer/                                    │
│      └── web-search/                                    │
└─────────────────────────────────────────────────────────┘
```

> **注意**: Python 后端使用与原 TS 后端相同的端口 (54367)，确保前端无需修改任何配置。

### 2.2 前端通信机制

前端通过 `@langchain/langgraph-sdk` 的 `Client` 与后端通信：

```typescript
// apps/web/src/hooks/utils.ts
import { Client } from "@langchain/langgraph-sdk";

export const createClient = () => {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:3000/api";
  return new Client({ apiUrl });
};
```

**关键 API 调用**:

- `client.runs.stream(threadId, assistantId, {...})` - 流式执行
- `client.threads.updateState(threadId, {...})` - 更新状态
- `streamMode: "events"` - 事件流模式

---

## 3. Python 项目结构

```
apps/agents-py/
├── pyproject.toml              # 依赖管理
├── langgraph.json              # LangGraph 配置
├── .env                        # 环境变量
├── Dockerfile                  # Docker 构建
└── src/
    ├── __init__.py
    ├── utils.py                # 共享工具函数
    ├── types.py                # 共享类型定义
    │
    ├── open_canvas/            # 主代理图
    │   ├── __init__.py
    │   ├── state.py            # State 定义
    │   ├── prompts.py          # Prompt 模板
    │   ├── graph.py            # StateGraph 定义
    │   └── nodes/
    │       ├── __init__.py
    │       ├── generate_path.py
    │       ├── generate_artifact.py
    │       ├── rewrite_artifact.py
    │       ├── update_artifact.py
    │       ├── update_highlighted_text.py
    │       ├── generate_followup.py
    │       ├── reply_to_general_input.py
    │       ├── custom_action.py
    │       ├── reflect.py
    │       ├── rewrite_artifact_theme.py
    │       ├── rewrite_code_artifact_theme.py
    │       ├── generate_title.py
    │       └── summarizer.py
    │
    ├── reflection/             # 反思图
    │   ├── __init__.py
    │   ├── state.py
    │   ├── prompts.py
    │   └── graph.py
    │
    ├── thread_title/           # 标题生成图
    │   ├── __init__.py
    │   ├── state.py
    │   ├── prompts.py
    │   └── graph.py
    │
    ├── summarizer/             # 摘要图
    │   ├── __init__.py
    │   ├── state.py
    │   └── graph.py
    │
    └── web_search/             # 网络搜索图
        ├── __init__.py
        ├── state.py
        └── graph.py
```

---

## 4. 类型映射

### 4.1 State 定义映射

| TypeScript                  | Python                                        |
| --------------------------- | --------------------------------------------- |
| `Annotation.Root({...})`  | `TypedDict` + `Annotated`                 |
| `MessagesAnnotation.spec` | `Annotated[list[AnyMessage], add_messages]` |
| `Annotation<T>`           | `T` 或 `Annotated[T, reducer]`            |

#### TypeScript 原始代码 (state.ts)

```typescript
import { Annotation, MessagesAnnotation, messagesStateReducer } from "@langchain/langgraph";
import { BaseMessage } from "@langchain/core/messages";
import { ArtifactV3, CodeHighlight, TextHighlight, ... } from "@opencanvas/shared/types";

export const OpenCanvasGraphAnnotation = Annotation.Root({
  ...MessagesAnnotation.spec,
  _messages: Annotation<BaseMessage[], Messages>({
    reducer: (state, update) => messagesStateReducer(state, update),
    default: () => [],
  }),
  highlightedCode: Annotation<CodeHighlight | undefined>,
  highlightedText: Annotation<TextHighlight | undefined>,
  artifact: Annotation<ArtifactV3>,
  next: Annotation<string | undefined>,
  language: Annotation<LanguageOptions | undefined>,
  artifactLength: Annotation<ArtifactLengthOptions | undefined>,
  regenerateWithEmojis: Annotation<boolean | undefined>,
  readingLevel: Annotation<ReadingLevelOptions | undefined>,
  addComments: Annotation<boolean | undefined>,
  addLogs: Annotation<boolean | undefined>,
  portLanguage: Annotation<ProgrammingLanguageOptions | undefined>,
  fixBugs: Annotation<boolean | undefined>,
  customQuickActionId: Annotation<string | undefined>,
  webSearchEnabled: Annotation<boolean | undefined>,
  webSearchResults: Annotation<SearchResult[] | undefined>,
});
```

#### Python 等效代码 (state.py)

> ⚠️ **关键**: State 字段名必须保持 camelCase 与前端/TypeScript 完全一致，否则会破坏前端兼容性。

```python
from typing import Annotated, Optional, Literal, Callable
from typing_extensions import TypedDict
from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages

# ============================================
# 共享常量 - 必须与 TS 侧保持一致
# ============================================
OC_SUMMARIZED_MESSAGE_KEY = "__oc_summarized_message"
OC_HIDE_FROM_UI_KEY = "__oc_hide_from_ui"
OC_WEB_SEARCH_RESULTS_KEY = "__oc_web_search_results_message"

# ============================================
# 类型定义 - 字段名保持 camelCase
# ============================================
LanguageOptions = Literal["english", "mandarin", "spanish", "french", "hindi"]
ArtifactLengthOptions = Literal["shortest", "short", "long", "longest"]
ReadingLevelOptions = Literal["pirate", "child", "teenager", "college", "phd"]
ProgrammingLanguageOptions = Literal[
    "typescript", "javascript", "cpp", "java", "php", "python",
    "html", "sql", "json", "rust", "xml", "clojure", "csharp", "other"
]

class CodeHighlight(TypedDict):
    """代码高亮 - 保持 camelCase"""
    startCharIndex: int
    endCharIndex: int

class TextHighlight(TypedDict):
    """文本高亮 - 保持 camelCase"""
    fullMarkdown: str
    markdownBlock: str
    selectedText: str

class ArtifactMarkdownV3(TypedDict):
    """Markdown 文档 - 保持 camelCase"""
    index: int
    type: Literal["text"]
    title: str
    fullMarkdown: str

class ArtifactCodeV3(TypedDict):
    """代码文档 - 保持 camelCase"""
    index: int
    type: Literal["code"]
    title: str
    language: ProgrammingLanguageOptions
    code: str
    isValidReact: Optional[bool]

class ArtifactV3(TypedDict):
    """文档 V3 - 保持 camelCase"""
    currentIndex: int
    contents: list[ArtifactMarkdownV3 | ArtifactCodeV3]

class SearchResult(TypedDict):
    """Exa 搜索结果 - 保持 camelCase"""
    id: str
    url: str
    title: str
    author: str
    publishedDate: str
    pageContent: str

# ============================================
# 自定义 Reducer - 处理摘要消息清空历史
# ============================================
def _messages_reducer(
    left: list[AnyMessage],
    right: list[AnyMessage] | AnyMessage
) -> list[AnyMessage]:
    """
    特殊 reducer: 遇到摘要消息时清空历史再追加
    这是保持与 TS 版本行为一致的关键逻辑
    """
    right_list = right if isinstance(right, list) else [right]
    if not right_list:
        return add_messages(left, right_list)

    latest = right_list[-1]
    additional_kwargs = getattr(latest, "additional_kwargs", {})

    # 如果是摘要消息，清空历史
    if additional_kwargs.get(OC_SUMMARIZED_MESSAGE_KEY) is True:
        return add_messages([], right_list)

    return add_messages(left, right_list)

# ============================================
# 主图状态 - 字段名保持 camelCase
# ============================================
class OpenCanvasState(TypedDict):
    """
    Open Canvas 主图状态

    ⚠️ 重要: 所有字段名必须与 TypeScript 版本完全一致 (camelCase)
    LangGraph Server 不会自动转换 snake_case ↔ camelCase
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
```

### 4.2 Graph 定义映射

| TypeScript                      | Python                            |
| ------------------------------- | --------------------------------- |
| `new StateGraph(Annotation)`  | `StateGraph(TypedDict)`         |
| `.addNode("name", fn)`        | `.add_node("name", fn)`         |
| `.addEdge(START, "name")`     | `.add_edge(START, "name")`      |
| `.addConditionalEdges()`      | `.add_conditional_edges()`      |
| `new Send(node, state)`       | `Send(node, state)`             |
| `new Command({goto, update})` | `Command(goto=..., update=...)` |

#### TypeScript 原始代码 (index.ts)

```typescript
import { Command, END, Send, START, StateGraph } from "@langchain/langgraph";
import { OpenCanvasGraphAnnotation } from "./state.js";
import { generatePath } from "./nodes/generate-path/index.js";
// ... other imports

const routeNode = (state: typeof OpenCanvasGraphAnnotation.State) => {
  if (!state.next) {
    throw new Error("'next' state field not set.");
  }
  return new Send(state.next, { ...state });
};

const builder = new StateGraph(OpenCanvasGraphAnnotation)
  .addNode("generatePath", generatePath)
  .addEdge(START, "generatePath")
  .addNode("replyToGeneralInput", replyToGeneralInput)
  .addNode("rewriteArtifact", rewriteArtifact)
  .addNode("generateArtifact", generateArtifact)
  .addNode("generateFollowup", generateFollowup)
  // ... more nodes
  .addConditionalEdges("generatePath", routeNode, [
    "updateArtifact", "rewriteArtifact", "generateArtifact", ...
  ])
  .addEdge("generateArtifact", "generateFollowup")
  // ... more edges

export const graph = builder.compile().withConfig({ runName: "open_canvas" });
```

#### Python 等效代码 (graph.py)

```python
from langgraph.graph import StateGraph, START, END, Send, Command
from .state import OpenCanvasState
from .nodes import (
    generate_path,
    generate_artifact,
    rewrite_artifact,
    update_artifact,
    update_highlighted_text,
    generate_followup,
    reply_to_general_input,
    custom_action,
    reflect_node,
    rewrite_artifact_theme,
    rewrite_code_artifact_theme,
    generate_title_node,
    summarizer,
)
from ..web_search.graph import graph as web_search_graph
from ..utils import create_ai_message_from_web_results

DEFAULT_INPUTS = {
    "highlighted_code": None,
    "highlighted_text": None,
    "language": None,
    "artifact_length": None,
    "regenerate_with_emojis": None,
    "reading_level": None,
    "add_comments": None,
    "add_logs": None,
    "port_language": None,
    "fix_bugs": None,
    "custom_quick_action_id": None,
    "web_search_enabled": None,
    "web_search_results": None,
}

def route_node(state: OpenCanvasState) -> Send:
    """根据 state.next 路由到对应节点"""
    if not state.get("next"):
        raise ValueError("'next' state field not set.")
    return Send(state["next"], dict(state))

def clean_state(state: OpenCanvasState) -> dict:
    """清理状态，重置为默认值"""
    return DEFAULT_INPUTS.copy()

CHARACTER_MAX = 300000  # ~75000 tokens

def simple_token_calculator(state: OpenCanvasState) -> str:
    """简单的 token 计算器，决定是否需要压缩"""
    total_chars = sum(
        len(msg.content) if isinstance(msg.content, str) else 0
        for msg in state.get("_messages", [])
    )
    return "summarizer" if total_chars > CHARACTER_MAX else END

def conditionally_generate_title(state: OpenCanvasState) -> str:
    """条件性生成标题"""
    if len(state.get("messages", [])) > 2:
        return simple_token_calculator(state)
    return "generateTitle"

def route_post_web_search(state: OpenCanvasState) -> Send | Command:
    """网络搜索后的路由"""
    includes_artifacts = len(state.get("artifact", {}).get("contents", [])) > 1

    if not state.get("web_search_results"):
        target = "rewriteArtifact" if includes_artifacts else "generateArtifact"
        return Send(target, {**state, "web_search_enabled": False})

    web_search_results_message = create_ai_message_from_web_results(
        state["web_search_results"]
    )

    return Command(
        goto="rewriteArtifact" if includes_artifacts else "generateArtifact",
        update={
            "web_search_enabled": False,
            "messages": [web_search_results_message],
            "_messages": [web_search_results_message],
        }
    )

# 构建图
builder = StateGraph(OpenCanvasState)

# 添加节点
builder.add_node("generatePath", generate_path)
builder.add_node("replyToGeneralInput", reply_to_general_input)
builder.add_node("rewriteArtifact", rewrite_artifact)
builder.add_node("rewriteArtifactTheme", rewrite_artifact_theme)
builder.add_node("rewriteCodeArtifactTheme", rewrite_code_artifact_theme)
builder.add_node("updateArtifact", update_artifact)
builder.add_node("updateHighlightedText", update_highlighted_text)
builder.add_node("generateArtifact", generate_artifact)
builder.add_node("customAction", custom_action)
builder.add_node("generateFollowup", generate_followup)
builder.add_node("cleanState", clean_state)
builder.add_node("reflect", reflect_node)
builder.add_node("generateTitle", generate_title_node)
builder.add_node("summarizer", summarizer)
builder.add_node("webSearch", web_search_graph)
builder.add_node("routePostWebSearch", route_post_web_search)

# 起始边
builder.add_edge(START, "generatePath")

# 条件路由
builder.add_conditional_edges("generatePath", route_node, [
    "updateArtifact",
    "rewriteArtifactTheme",
    "rewriteCodeArtifactTheme",
    "replyToGeneralInput",
    "generateArtifact",
    "rewriteArtifact",
    "customAction",
    "updateHighlightedText",
    "webSearch",
])

# 常规边
builder.add_edge("generateArtifact", "generateFollowup")
builder.add_edge("updateArtifact", "generateFollowup")
builder.add_edge("updateHighlightedText", "generateFollowup")
builder.add_edge("rewriteArtifact", "generateFollowup")
builder.add_edge("rewriteArtifactTheme", "generateFollowup")
builder.add_edge("rewriteCodeArtifactTheme", "generateFollowup")
builder.add_edge("customAction", "generateFollowup")
builder.add_edge("webSearch", "routePostWebSearch")
builder.add_edge("replyToGeneralInput", "cleanState")
builder.add_edge("generateFollowup", "reflect")
builder.add_edge("reflect", "cleanState")

# 条件结束边
builder.add_conditional_edges("cleanState", conditionally_generate_title, [
    END,
    "generateTitle",
    "summarizer",
])
builder.add_edge("generateTitle", END)
builder.add_edge("summarizer", END)

# 编译图
graph = builder.compile()
```

### 4.3 节点函数映射示例

#### TypeScript 节点 (generateFollowup.ts)

```typescript
import { ChatOpenAI } from "@langchain/openai";
import { OpenCanvasGraphAnnotation, OpenCanvasGraphReturnType } from "../state.js";

export async function generateFollowup(
  state: typeof OpenCanvasGraphAnnotation.State,
  config: LangGraphRunnableConfig
): Promise<OpenCanvasGraphReturnType> {
  const model = new ChatOpenAI({
    model: config.configurable?.customModelName || "gpt-4o",
    temperature: 0.7,
  });

  const response = await model.invoke(state.messages);

  return {
    messages: [response],
  };
}
```

#### Python 节点 (generate_followup.py)

```python
from langchain_openai import ChatOpenAI
from langgraph.types import RunnableConfig
from ..state import OpenCanvasState

async def generate_followup(
    state: OpenCanvasState,
    config: RunnableConfig
) -> dict:
    """生成跟进消息"""
    configurable = config.get("configurable", {})
    model_name = configurable.get("customModelName", "gpt-4o")

    model = ChatOpenAI(
        model=model_name,
        temperature=0.7,
    )

    response = await model.ainvoke(state["messages"])

    return {
        "messages": [response],
    }
```

---

## 5. 依赖配置

### 5.1 pyproject.toml

> ⚠️ **重要**: 迁移期间建议 Pin 版本，避免 API 变化导致的兼容性问题。

```toml
[project]
name = "open-canvas-agents"
version = "0.1.0"
description = "Open Canvas LangGraph Agents (Python)"
requires-python = ">=3.12"
dependencies = [
    # LangGraph 核心 - Pin 版本以确保稳定性
    "langgraph==1.0.5",
    "langgraph-sdk==0.3.0",
    "langgraph-cli[inmem]==0.3.7",

    # LangChain 核心
    "langchain-core==0.3.25",

    # LLM 提供商
    "langchain-openai==0.3.0",
    "langchain-anthropic==0.3.0",
    "langchain-google-genai==2.0.8",
    "langchain-fireworks==0.2.8",
    "langchain-ollama==0.3.0",

    # 网络搜索
    "exa-py>=1.0.0",

    # 工具库
    "pydantic>=2.0.0",
    "python-dotenv>=1.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "pytest-asyncio>=0.21.0",
    "black>=23.0.0",
    "ruff>=0.1.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.black]
line-length = 100
target-version = ["py312"]
```

### 5.2 langgraph.json

> ⚠️ **CORS 配置**: 如果浏览器直连后端（不经过 Next.js API 代理），必须配置 CORS。

```json
{
  "python_version": "3.12",
  "dependencies": ["."],
  "graphs": {
    "agent": "src.open_canvas.graph:graph",
    "reflection": "src.reflection.graph:graph",
    "thread_title": "src.thread_title.graph:graph",
    "summarizer": "src.summarizer.graph:graph",
    "web_search": "src.web_search.graph:graph"
  },
  "env": "../.env",
  "http": {
    "cors": {
      "allow_origins": ["http://localhost:3000", "https://your-domain.com"],
      "allow_methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
      "allow_headers": ["*"],
      "allow_credentials": true
    }
  }
}
```

> **注意**:
>
> - graphs 使用模块路径格式 `module.path:variable`，不是文件路径 `./path/to/file.py:variable`
> - env 指向根目录的 `.env` 文件 (`../env`)，而不是 `apps/agents-py/.env`

> **CORS 说明**:
>
> - `allow_origins`: 允许的前端域名列表
> - 本地开发: `http://localhost:3000`
> - 生产环境: 替换为实际域名
> - 如果使用 Next.js API 代理模式，则不需要 CORS 配置

### 5.3 部署方式

> ⚠️ **重要**: `langgraph up` 是在宿主机启动 Docker 容器的命令，不能作为容器的 entrypoint。
>
> 部署方式选择:
>
> - **本地开发**: 使用 `langgraph dev`
> - **生产部署**: 使用 `langgraph build` 构建镜像，或使用 `langgraph dockerfile` 生成 Dockerfile

#### 方式 A: 使用 langgraph build（推荐）

```bash
# 在 apps/agents-py 目录下
cd apps/agents-py

# 构建 LangGraph Server 镜像
langgraph build -t open-canvas-agents:latest

# 运行容器（容器内端口 8000，映射到宿主 54367）
docker run -d \
  --name open-canvas-agents \
  -p 54367:8000 \
  --env-file .env \
  open-canvas-agents:latest
```

#### 方式 B: 自定义 Dockerfile（用于特殊需求）

```dockerfile
# 使用官方 LangGraph 基础镜像
FROM langchain/langgraph-api:latest

WORKDIR /app

# 复制项目文件（不包含 .env，运行时注入）
COPY pyproject.toml langgraph.json ./
COPY src/ ./src/

# 安装依赖
RUN pip install --no-cache-dir -e .

# 容器内端口 8000（LangGraph Server 默认端口）
EXPOSE 8000

# 注意: 不需要显式 CMD，基础镜像已配置
```

> ⚠️ **安全提示**: 不要将 `.env` 文件 COPY 到镜像中，应使用运行时环境变量注入。

---

## 6. 部署与切换

### 6.1 本地开发

#### 启动 Python 后端

```bash
cd apps/agents-py

# 安装依赖
pip install -e ".[dev]"

# 启动 LangGraph 开发服务器 (端口 54367，与原 TS 后端相同)
langgraph dev --port 54367
```

#### 启动前端

```bash
cd apps/web

# 前端无需修改，使用默认配置连接 54367 端口
yarn dev
```

### 6.2 Docker Compose 配置

```yaml
# docker-compose.yml
version: '3.8'

services:
  # Python 后端（替代原 TypeScript 后端）
  agents:
    # 使用 langgraph build 构建的镜像
    image: open-canvas-agents:latest
    # 或者直接构建:
    # build:
    #   context: ./apps/agents-py
    #   dockerfile: Dockerfile
    ports:
      # 容器内 8000 → 宿主 54367（前端访问端口）
      - "54367:8000"
    env_file:
      - .env
    healthcheck:
      # 容器内使用 8000 端口
      test: ["CMD", "wget", "-qO-", "http://localhost:8000/health", "||", "exit", "1"]
      interval: 30s
      timeout: 10s
      retries: 3
    # 注意: 不需要 command，镜像已配置入口点

  # 前端
  web:
    build:
      context: ./apps/web
    ports:
      - "3000:3000"
    environment:
      # 容器间通信使用 8000，外部访问使用 54367
      - NEXT_PUBLIC_API_URL=http://agents:8000
    depends_on:
      agents:
        condition: service_healthy
```

> **端口映射说明**:
>
> - **容器内端口**: 8000（LangGraph Server 默认）
> - **宿主映射端口**: 54367（与原 TS 后端相同，前端零配置）
> - **容器间通信**: 使用 8000（web → agents）

### 6.3 前端配置（无需修改）

由于 Python 后端使用与原 TS 后端相同的端口 (54367)，前端代码无需任何修改：

```typescript
// apps/web/src/hooks/utils.ts (保持不变)
import { Client } from "@langchain/langgraph-sdk";

export const createClient = () => {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:3000/api";
  return new Client({ apiUrl });
};
```

### 6.4 迁移步骤

```bash
# 1. 停止 TypeScript 后端
# (如果在 apps/agents 目录运行 yarn dev，先停止它)

# 2. 启动 Python 后端 (使用相同端口)
cd apps/agents-py
langgraph dev --port 54367

# 3. 前端自动连接到新后端，无需重启
```

> **关键点**: Python 后端使用端口 54367（与原 TS 相同），实现零配置迁移。`apps/agents/` 目录保留作为代码参考，但不再运行。

### 6.5 环境变量配置

```bash
# .env (根目录)

# LLM API Keys
OPENAI_API_KEY=sk-xxx
ANTHROPIC_API_KEY=sk-ant-xxx
GOOGLE_API_KEY=xxx
FIREWORKS_API_KEY=xxx

# Supabase
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=xxx

# LangSmith (可选)
LANGCHAIN_API_KEY=xxx
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=open-canvas

# Exa 搜索
EXA_API_KEY=xxx
```

---

## 7. 迁移计划

### 7.1 迁移优先级

| 优先级 | Graph                  | 复杂度 | 文件数 | 说明               |
| ------ | ---------------------- | ------ | ------ | ------------------ |
| 🔴 P0  | **open-canvas**  | 高     | 18     | 核心功能，最先迁移 |
| 🟡 P1  | **reflection**   | 低     | 3      | 记忆功能，依赖主图 |
| 🟡 P1  | **thread-title** | 低     | 3      | 标题生成           |
| 🟢 P2  | **summarizer**   | 低     | 2      | 对话压缩           |
| 🟢 P2  | **web-search**   | 中     | 5      | Exa 集成           |

---

## 8. 验证清单

### 8.1 功能验证

| 功能              | TS 后端 | Python 后端 | 状态   |
| ----------------- | ------- | ----------- | ------ |
| 创建新文档        | ✅      | ⬜          | 待测试 |
| 编辑文档          | ✅      | ⬜          | 待测试 |
| 代码高亮编辑      | ✅      | ⬜          | 待测试 |
| Markdown 高亮编辑 | ✅      | ⬜          | 待测试 |
| 快捷操作          | ✅      | ⬜          | 待测试 |
| 自定义操作        | ✅      | ⬜          | 待测试 |
| 网络搜索          | ✅      | ⬜          | 待测试 |
| 对话压缩          | ✅      | ⬜          | 待测试 |
| 标题生成          | ✅      | ⬜          | 待测试 |
| 反思/记忆         | ✅      | ⬜          | 待测试 |
| 流式传输          | ✅      | ⬜          | 待测试 |
| 版本历史          | ✅      | ⬜          | 待测试 |

### 8.2 API 兼容性验证

```bash
# 验证 API 端点
curl http://localhost:54367/health
curl http://localhost:54367/assistants
curl http://localhost:54367/threads

# 验证流式传输
curl -X POST http://localhost:54367/threads/{thread_id}/runs/stream \
  -H "Content-Type: application/json" \
  -d '{"assistant_id": "agent", "input": {...}}'
```

### 8.3 性能基准

| 指标         | TS 后端 | Python 后端 | 差异 |
| ------------ | ------- | ----------- | ---- |
| 首次响应时间 | TBD     | TBD         | TBD  |
| 流式传输延迟 | TBD     | TBD         | TBD  |
| 内存使用     | TBD     | TBD         | TBD  |
| CPU 使用     | TBD     | TBD         | TBD  |

---

## 附录

### A. 参考资源

- [LangGraph Python 文档](https://langchain-ai.github.io/langgraph/)
- [LangGraph TypeScript 文档](https://langchain-ai.github.io/langgraphjs/)
- [LangGraph Server 部署指南](https://langchain-ai.github.io/langgraph/cloud/)
- [Open Canvas 项目仓库](https://github.com/langchain-ai/open-canvas)

### B. 常见问题

**Q: Python 后端使用什么端口？**
A: Python 后端使用与原 TypeScript 后端相同的端口 54367，实现零配置迁移。前端无需修改任何配置即可切换到 Python 后端。

**Q: 如何验证前端无感知切换？**
A: 由于使用相同端口 54367，只需停止 TypeScript 后端、启动 Python 后端即可完成切换，前端无需任何配置变更，所有功能应正常工作。

**Q: State 字段命名是否需要保持一致？**
A: ⚠️ **必须保持一致**。LangGraph Server **不会**自动转换 snake_case 和 camelCase。Python State 必须使用与 TypeScript/前端完全相同的 camelCase 字段名（如 `highlightedCode`、`artifactLength`），否则前端功能会失效。

**Q: 为什么需要自定义 `_messages` reducer？**
A: TypeScript 版本的 `_messages` reducer 有特殊逻辑：遇到摘要消息时会清空历史再追加新消息。如果使用默认的 `add_messages`，上下文会无限增长导致成本爆炸。

**Q: 浏览器直连后端时为什么被 CORS 拦截？**
A: 需要在 `langgraph.json` 中配置 `http.cors` 允许前端域名。如果使用 Next.js API 代理模式则不需要 CORS 配置。

**Q: `langgraph up` 和 `langgraph dev` 有什么区别？**
A:

- `langgraph dev`: 直接在本机启动开发服务器（本地开发用）
- `langgraph up`: 在本机启动一个 Docker 容器运行服务（需要 Docker）
- `langgraph build`: 构建可部署的 Docker 镜像（生产部署用）

---
