# Open Canvas 辅助图架构详解

本文档详细介绍 Open Canvas Python 后端的四个辅助图（Auxiliary Graphs），包括它们的功能、实现细节以及与主图的交互方式。

## 目录

- [概述](#概述)
- [Web Search 网络搜索图](#web-search-网络搜索图)
- [Thread Title 标题生成图](#thread-title-标题生成图)
- [Summarizer 摘要图](#summarizer-摘要图)
- [Reflection 反思图](#reflection-反思图)
- [主图调用机制](#主图调用机制)
- [架构图](#架构图)

---

## 概述

Open Canvas 采用多图架构设计，将不同职责分离到独立的子图中。这种设计的优势：

| 特性 | 说明 |
|------|------|
| **关注点分离** | 每个图专注于单一职责 |
| **异步执行** | 子图可后台运行，不阻塞主流程 |
| **去抖动策略** | 支持延迟执行，避免频繁调用 |
| **独立扩展** | 各图可独立优化和扩展 |

### 图清单

| 图名称 | 文件路径 | 功能 | 触发时机 |
|--------|----------|------|----------|
| Web Search | `src/web_search/` | 网络搜索集成 | 用户启用搜索且消息需要搜索 |
| Thread Title | `src/thread_title/` | 自动生成对话标题 | 首次对话 (messages ≤ 2) |
| Summarizer | `src/summarizer/` | 压缩长对话历史 | 消息字符数超过阈值 |
| Reflection | `src/reflection/` | 用户洞察/风格规则记忆 | 每次工件操作后 |

---

## Web Search 网络搜索图

### 功能概述

基于 [Exa API](https://exa.ai/) 的网络搜索集成，为用户提供实时网络信息。

### 文件结构

```
src/web_search/
├── __init__.py
├── graph.py          # 图定义和编译
├── state.py          # 状态类型定义
└── nodes/
    ├── __init__.py
    ├── classify_message.py   # 消息分类节点
    ├── query_generator.py    # 查询生成节点
    └── search.py             # 搜索执行节点
```

### 状态定义

```python
class WebSearchState(TypedDict, total=False):
    messages: Annotated[list[AnyMessage], add_messages]  # 消息列表
    shouldSearch: Optional[bool]                          # 是否需要搜索
    query: Optional[str]                                  # 搜索查询
    webSearchResults: Optional[list[SearchResult]]        # 搜索结果
```

### 图结构

```
┌─────────────────┐
│      START      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ classifyMessage │ ── 判断消息是否需要搜索
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
   END   ┌────────────────┐
         │ queryGenerator │ ── 生成搜索友好的查询
         └───────┬────────┘
                 │
                 ▼
         ┌───────────────┐
         │    search     │ ── 执行 Exa 搜索
         └───────┬───────┘
                 │
                 ▼
               END
```

### 节点详解

#### 1. classify_message - 消息分类

**功能**: 判断用户最新消息是否需要进行网络搜索

**使用模型**: `claude-3-5-sonnet-latest`

**逻辑**:
- 分析用户最新消息内容
- 使用结构化输出返回 `shouldSearch` 布尔值
- 如果不需要搜索，直接结束图执行

```python
# 提示词模板
CLASSIFIER_PROMPT = """You're a helpful AI assistant tasked with classifying...
Analyze their latest message in isolation and determine if it warrants a web search..."""
```

#### 2. query_generator - 查询生成

**功能**: 将用户消息转换为搜索引擎友好的查询

**使用模型**: `claude-3-5-sonnet-latest`

**特点**:
- 注入当前日期上下文（格式: `Dec 22, 2024, 10:30 AM`）
- 保持查询与原消息相似，同时优化搜索效果

#### 3. search - 搜索执行

**功能**: 使用 Exa API 执行网络搜索

**配置**:
- 返回 5 条结果
- 搜索类型: `auto`
- 获取文本内容

**输出格式**:
```python
SearchResult = {
    "pageContent": str,      # 页面内容
    "metadata": {
        "id": str,
        "url": str,
        "title": str,
        "author": Optional[str],
        "publishedDate": Optional[str],
        "image": Optional[str],
        "favicon": Optional[str],
    }
}
```

---

## Thread Title 标题生成图

### 功能概述

在对话初期自动生成简洁的对话标题，并更新线程元数据。

### 文件结构

```
src/thread_title/
├── __init__.py
├── graph.py          # 图定义
├── prompts.py        # 提示词模板
└── state.py          # 状态定义
```

### 状态定义

```python
class ThreadTitleState(TypedDict, total=False):
    messages: Annotated[list[AnyMessage], add_messages]  # 消息列表
    artifact: Optional[ArtifactV3]                        # 当前工件
```

### 图结构

```
┌─────────────────┐
│      START      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  generateTitle  │ ── 生成标题并更新线程
└────────┬────────┘
         │
         ▼
       END
```

### 节点详解

#### generateTitle - 标题生成

**功能**: 基于对话内容和工件生成 2-5 词的简洁标题

**使用模型**: `gpt-4o-mini` (快速且经济)

**工具调用**: 使用 `GenerateTitle` Pydantic schema 确保输出格式

**关键步骤**:
1. 从 config 获取 `open_canvas_thread_id`
2. 格式化对话为 XML 格式
3. 提取工件内容（Markdown 或代码）
4. 调用模型生成标题
5. 使用 LangGraph SDK 更新线程元数据

**提示词指南**:
- 保持标题极短 (2-5 词)
- 聚焦主题或目标
- 使用自然可读的语言
- 避免不必要的冠词

---

## Summarizer 摘要图

### 功能概述

当对话历史过长时，压缩消息为摘要，保持上下文窗口在合理范围内。

### 文件结构

```
src/summarizer/
├── __init__.py
├── graph.py          # 图定义和摘要节点
└── state.py          # 状态定义
```

### 状态定义

```python
class SummarizerState(TypedDict, total=False):
    messages: Annotated[list[AnyMessage], add_messages]   # 消息列表
    _messages: Annotated[list[AnyMessage], add_messages]  # 内部消息列表
    threadId: Optional[str]                                # 线程 ID
```

### 图结构

```
┌─────────────────┐
│      START      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   summarize     │ ── 压缩对话历史
└────────┬────────┘
         │
         ▼
       END
```

### 节点详解

#### summarize - 摘要

**功能**: 将长对话历史压缩为结构化摘要

**使用模型**: `claude-3-5-sonnet-latest`

**关键特性**:
1. **透明摘要**: 用户不应知道摘要存在
2. **上下文保持**: 摘要包含足够信息支持后续对话
3. **消息计数**: 摘要末尾标记 `[End of Notes, Message #X]`
4. **特殊标记**: 使用 `OC_SUMMARIZED_MESSAGE_KEY` 标识摘要消息

**输出处理**:
- 创建带特殊标记的 `HumanMessage`
- 使用 LangGraph SDK 更新线程状态

### 触发条件

```python
CHARACTER_MAX = 300000  # ~75,000 tokens (4 chars/token)

def simple_token_calculator(state: OpenCanvasState):
    total_chars = sum(len(msg.content) for msg in state["_messages"])
    if total_chars > CHARACTER_MAX:
        return "summarizer"
    return END
```

---

## Reflection 反思图

### 功能概述

分析用户对话和工件，提取风格规则和用户信息，持久化到 Store 中实现记忆功能。

### 文件结构

```
src/reflection/
├── __init__.py
├── graph.py          # 图定义和反思节点
├── prompts.py        # 提示词模板
└── state.py          # 状态定义
```

### 状态定义

```python
class ReflectionState(TypedDict, total=False):
    messages: Annotated[list[AnyMessage], add_messages]  # 消息列表
    artifact: Optional[ArtifactV3]                        # 当前工件
```

### 图结构

```
┌─────────────────┐
│      START      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│     reflect     │ ── 分析并存储记忆
└────────┬────────┘
         │
         ▼
       END
```

### 节点详解

#### reflect - 反思

**功能**: 提取用户风格规则和事实信息

**使用模型**: `claude-3-5-sonnet-20240620`

**存储结构**:
```python
{
    "styleRules": [str],  # 风格规则列表
    "content": [str]      # 用户事实/记忆列表
}
```

**关键步骤**:
1. 从 config 获取 `open_canvas_assistant_id`
2. 从 Store 读取现有记忆
3. 格式化工件内容和对话
4. 调用模型生成新反思
5. 将新反思存储到 Store

**存储命名空间**:
```python
memory_namespace = ("memories", assistant_id)
memory_key = "reflection"
```

### 反思指南

**风格规则 (styleRules)**:
- 写作风格偏好
- 代码风格偏好
- 设计风格偏好

**内容记忆 (content)**:
- 用户兴趣
- 用户目标
- 用户个性特征

**约束**:
- 不基于猜测生成规则
- 必须有证据支持
- 保持规则数量精简但描述详尽

---

## 主图调用机制

### 调用方式对比

| 子图 | 调用方式 | 延迟 | 说明 |
|------|----------|------|------|
| Web Search | 直接节点调用 | 同步 | 在主图流程中直接执行 |
| Thread Title | LangGraph SDK | 0秒 | 立即后台执行 |
| Summarizer | 直接节点调用 | 同步 | 在主图流程中条件执行 |
| Reflection | LangGraph SDK | 5分钟 | 延迟后台执行（去抖动） |

### 主图中的调用节点

#### 1. Web Search 调用

**文件**: `src/open_canvas/graph.py`

**触发条件**: `generatePath` 返回 `next="webSearch"`

**调用方式**: 作为主图节点直接执行

```python
# 当前为占位实现
async def web_search(state, config, *, store):
    # TODO(Phase 6): 替换为 web_search 子图调用
    return {"webSearchResults": []}
```

**后续处理**: `routePostWebSearch` 节点处理搜索结果

#### 2. Thread Title 调用

**文件**: `src/open_canvas/nodes/generate_title.py`

**触发条件**: `cleanState` 后 `messages.length <= 2`

**调用方式**: LangGraph SDK 异步调用

```python
async def generate_title_node(state, config, *, store):
    langgraph_client = get_client(url=f"http://localhost:{port}")

    # 准备输入
    title_input = {
        "messages": messages,
        "artifact": state.get("artifact"),
    }

    # 配置 - 传递 thread_id
    title_config = {
        "configurable": {
            "open_canvas_thread_id": config["configurable"]["thread_id"],
        },
    }

    # 创建后台运行 (立即执行)
    await langgraph_client.runs.create(
        thread_id=new_thread["thread_id"],
        assistant_id="thread_title",
        input=title_input,
        config=title_config,
        multitask_strategy="enqueue",
        after_seconds=0,
    )
```

#### 3. Summarizer 调用

**文件**: `src/open_canvas/graph.py`

**触发条件**: `cleanState` 后消息字符数 > `CHARACTER_MAX` (300,000)

**调用方式**: 作为主图节点直接执行

```python
def conditionally_generate_title(state):
    if len(messages) <= 2:
        return "generateTitle"
    return simple_token_calculator(state)  # 可能返回 "summarizer"
```

#### 4. Reflection 调用

**文件**: `src/open_canvas/nodes/reflect.py`

**触发条件**: 每次 `generateFollowup` 后

**调用方式**: LangGraph SDK 异步调用（5分钟延迟）

```python
async def reflect_node(state, config, *, store):
    langgraph_client = get_client(url=f"http://localhost:{port}")

    # 准备输入
    reflection_input = {
        "messages": state.get("_messages", []),
        "artifact": state.get("artifact"),
    }

    # 配置 - 传递 assistant_id
    reflection_config = {
        "configurable": {
            "open_canvas_assistant_id": config["configurable"]["assistant_id"],
        },
    }

    # 创建后台运行 (5分钟延迟去抖动)
    await langgraph_client.runs.create(
        thread_id=new_thread["thread_id"],
        assistant_id="reflection",
        input=reflection_input,
        config=reflection_config,
        multitask_strategy="enqueue",
        after_seconds=5 * 60,  # 300秒
    )
```

**去抖动机制**:
- 如果 5 分钟内有新请求，旧任务被取消
- 新任务重新排队，从头计时
- 避免用户活跃对话时频繁调用

---

## 架构图

### 主图与子图关系

```
┌────────────────────────────────────────────────────────────────────────┐
│                          Open Canvas 主图                               │
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  START → generatePath ─┬─→ webSearch → routePostWebSearch ─┐          │
│                        │                                     │          │
│                        ├─→ generateArtifact ────────────────┤          │
│                        ├─→ rewriteArtifact ─────────────────┤          │
│                        ├─→ updateArtifact ──────────────────┤          │
│                        ├─→ updateHighlightedText ───────────┤          │
│                        ├─→ rewriteArtifactTheme ────────────┤          │
│                        ├─→ rewriteCodeArtifactTheme ────────┤          │
│                        ├─→ customAction ────────────────────┤          │
│                        │                                     │          │
│                        └─→ replyToGeneralInput ─────────────┼─┐        │
│                                                              │ │        │
│                                 ┌────────────────────────────┘ │        │
│                                 ▼                              │        │
│                          generateFollowup                      │        │
│                                 │                              │        │
│                                 ▼                              │        │
│                            reflect ←───────────────────────────┘        │
│                                 │         │                             │
│                                 ▼         │ (后台调用)                  │
│                           cleanState      └──→ [Reflection 子图]       │
│                                 │                                       │
│                    ┌────────────┼────────────┐                         │
│                    │            │            │                          │
│                    ▼            ▼            ▼                          │
│             generateTitle   summarizer     END                          │
│                    │            │                                       │
│    (后台调用)      │            │                                       │
│                    ▼            ▼                                       │
│         [Thread Title 子图]  [Summarizer 子图]                          │
│                    │            │                                       │
│                    └────────────┴────→ END                             │
└────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                              子图详情                                    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐         │
│  │   Web Search    │  │  Thread Title   │  │   Summarizer    │         │
│  ├─────────────────┤  ├─────────────────┤  ├─────────────────┤         │
│  │ classifyMessage │  │  generateTitle  │  │    summarize    │         │
│  │       ↓         │  │       ↓         │  │       ↓         │         │
│  │ queryGenerator  │  │      END        │  │      END        │         │
│  │       ↓         │  └─────────────────┘  └─────────────────┘         │
│  │    search       │                                                    │
│  │       ↓         │  ┌─────────────────┐                              │
│  │      END        │  │   Reflection    │                              │
│  └─────────────────┘  ├─────────────────┤                              │
│                       │     reflect     │                              │
│                       │       ↓         │                              │
│                       │      END        │                              │
│                       └─────────────────┘                              │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 数据流向

```
用户输入
    │
    ▼
┌─────────────────┐
│  主图执行流程   │
│                 │
│  messages ─────────────→ Thread Title (生成标题)
│     │                          │
│     │                          ▼
│     │                    更新线程元数据
│     │
│  _messages + artifact ─────→ Reflection (记忆更新)
│     │                              │
│     │                              ▼
│     │                         Store 持久化
│     │
│  messages (过长时) ──────→ Summarizer (压缩)
│     │                           │
│     │                           ▼
│     │                    更新线程状态
│     │
│  messages + webSearchEnabled ─→ Web Search
│                                      │
│                                      ▼
│                               搜索结果返回主图
└─────────────────────────────────────────────────┘
```

---

## 配置参考

### langgraph.json

```json
{
  "graphs": {
    "open-canvas": "./src/open_canvas/graph.py:graph",
    "reflection": "./src/reflection/graph.py:graph",
    "thread_title": "./src/thread_title/graph.py:graph",
    "summarizer": "./src/summarizer/graph.py:graph",
    "web_search": "./src/web_search/graph.py:graph"
  }
}
```

### 环境变量

| 变量 | 用途 | 必需 |
|------|------|------|
| `EXA_API_KEY` | Exa 搜索 API | Web Search |
| `PORT` | LangGraph 服务端口 | SDK 调用 |
| `ANTHROPIC_API_KEY` | Claude API | 所有 Anthropic 模型 |
| `OPENAI_API_KEY` | OpenAI API | Thread Title |

---

## 总结

Open Canvas 的辅助图设计体现了以下架构原则：

1. **单一职责**: 每个子图专注于一个特定功能
2. **异步解耦**: 非关键路径子图通过 SDK 异步调用
3. **智能去抖**: 反思图使用延迟执行避免资源浪费
4. **状态隔离**: 子图有独立的状态定义，通过输入/输出与主图交互
5. **可观测性**: 每个子图可独立监控和调试
