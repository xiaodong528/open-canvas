# LangGraph TypeScript → Python 迁移实施工作流

> **创建日期**: 2025-12-16
> **技术方案**: [docs/plan/langgraph-python-migration.md](../plan/langgraph-python-migration.md)
> **目标**: 将 Open Canvas LangGraph 代理从 TypeScript 迁移到 Python
> **版本**: v2.0 (Codex 反思增强版)

---

## 进度追踪

| Phase | 描述 | 任务数 | Gate 条件 | 状态 |
|-------|------|--------|-----------|------|
| 1 | 项目初始化 | 5 | `/health` 返回 200 | ⬜ |
| 2 | 共享组件 | 3 | types/utils 可 import | ⬜ |
| 3 | 主图 - State & Prompts | 3 | State 字段与 TS 对齐 | ⬜ |
| 4 | 主图 - 节点函数 | 12 | 所有节点函数可调用 | ⬜ |
| 5 | 主图 - 控制流 | 5 | 图可编译，路由正确 | ⬜ |
| 6 | 辅助图 | 4 | 4 个子图全部可用 | ⬜ |
| 7 | 集成测试 | 6 | 关键路径全部通过 | ⬜ |
| 8 | 部署 | 3 | 生产环境可访问 | ⬜ |

**状态图例**: ⬜ 待开始 | 🔄 进行中 | ✅ 完成

---

## 关键风险提示

> ⚠️ **必读** - 以下是迁移过程中最容易出错的高风险点

| 风险项 | 影响 | 相关 Phase |
|--------|------|------------|
| **camelCase 字段名** | 前端无法识别状态 | Phase 2, 3 |
| **`_messages` reducer** | 上下文无限增长 | Phase 3 |
| **`DEFAULT_INPUTS` 重置** | 状态污染下一轮 | Phase 2, 5 |
| **路由条件边** | 路由丢失/错误 | Phase 5 |
| **`messages` vs `_messages`** | 模型上下文错误 | Phase 3, 4 |
| **CHARACTER_MAX 阈值** | 摘要永不触发 | Phase 5 |

---

## Phase 1: 项目初始化

**目标**: 创建 Python 项目骨架，配置依赖和 LangGraph Server

**Gate 条件**: `langgraph dev` 启动成功，`/health` 返回 200

### 任务清单

- [ ] **1.1 创建目录结构**
  ```bash
  mkdir -p apps/agents-py/src/{open_canvas/nodes,reflection,thread_title,summarizer,web_search/nodes}
  # 创建所有必要的 __init__.py
  touch apps/agents-py/src/__init__.py
  touch apps/agents-py/src/open_canvas/__init__.py
  touch apps/agents-py/src/open_canvas/nodes/__init__.py
  touch apps/agents-py/src/reflection/__init__.py
  touch apps/agents-py/src/thread_title/__init__.py
  touch apps/agents-py/src/summarizer/__init__.py
  touch apps/agents-py/src/web_search/__init__.py
  touch apps/agents-py/src/web_search/nodes/__init__.py
  ```

- [ ] **1.2 配置 pyproject.toml**
  - 参考: [技术方案 §5.1](../plan/langgraph-python-migration.md#51-pyprojecttoml)
  - 核心依赖（锁定版本）:
    ```toml
    langgraph = "0.2.60"
    langchain-core = "0.3.25"
    langchain-openai = "0.3.0"
    langchain-anthropic = "0.3.0"
    ```
  - 可选 Provider 依赖:
    ```toml
    langchain-google-genai = "2.0.8"
    langchain-fireworks = "0.2.8"
    langchain-ollama = "0.3.0"
    ```

- [ ] **1.3 配置 langgraph.json**
  - 参考: [技术方案 §5.2](../plan/langgraph-python-migration.md#52-langgraphjson)
  - 定义 5 个图: `agent`, `reflection`, `thread_title`, `summarizer`, `web_search`
  - ⚠️ 如需浏览器直连，配置 CORS

- [ ] **1.4 创建 .env 模板**
  - 必需: `OPENAI_API_KEY`, `LANGCHAIN_API_KEY`
  - 可选: `ANTHROPIC_API_KEY`, `GOOGLE_API_KEY`, `EXA_API_KEY`

- [ ] **1.5 验证启动**
  ```bash
  cd apps/agents-py
  pip install -e ".[dev]"
  langgraph dev --port 54367
  curl http://localhost:54367/health  # 应返回 200
  ```

**参考文件**:
- 技术方案: `docs/plan/langgraph-python-migration.md` §5

---

## Phase 2: 共享组件

**目标**: 创建共享类型定义、常量和工具函数

**Gate 条件**: `from src.types import *` 和 `from src.utils import *` 成功

### 任务清单

- [ ] **2.1 创建 constants.py**
  - 参考 TS: `packages/shared/src/constants.ts`
  - ⚠️ **关键**: 必须与 TS 完全一致
  ```python
  # 消息标记常量
  OC_SUMMARIZED_MESSAGE_KEY = "__oc_summarized_message"
  OC_HIDE_FROM_UI_KEY = "__oc_hide_from_ui"
  OC_WEB_SEARCH_RESULTS_KEY = "__oc_web_search_results_message"

  # 状态重置常量 - 必须与 TS DEFAULT_INPUTS 对齐
  DEFAULT_INPUTS = {
      "highlightedCode": None,
      "highlightedText": None,
      "next": None,
      "language": None,
      "artifactLength": None,
      "regenerateWithEmojis": None,
      "readingLevel": None,
      "addComments": None,
      "addLogs": None,
      "fixBugs": None,
      "portLanguage": None,
      "customQuickActionId": None,
      "webSearchEnabled": None,
      "webSearchResults": None,
  }

  # 摘要触发阈值 (~75000 tokens)
  CHARACTER_MAX = 300000
  ```

- [ ] **2.2 创建 types.py**
  - 参考 TS: `packages/shared/src/types.ts`
  - ⚠️ **关键**: 所有字段名必须保持 **camelCase**
  - 定义类型:
    - `LanguageOptions = Literal["english", "mandarin", "spanish", "french", "hindi"]`
    - `ArtifactLengthOptions = Literal["shortest", "short", "long", "longest"]`
    - `ReadingLevelOptions = Literal["pirate", "child", "teenager", "college", "phd"]`
    - `ProgrammingLanguageOptions` (14 种语言)
    - `CodeHighlight(TypedDict)`: `startCharIndex`, `endCharIndex`
    - `TextHighlight(TypedDict)`: `fullMarkdown`, `markdownBlock`, `selectedText`
    - `ArtifactMarkdownV3`, `ArtifactCodeV3`, `ArtifactV3`
    - `SearchResult`

- [ ] **2.3 创建 utils.py**
  - 参考 TS: `apps/agents/src/utils.ts` (656 行)
  - 关键函数及其契约:

  | 函数 | 输入 | 输出 | 说明 |
  |------|------|------|------|
  | `get_model_config(name)` | 模型名 | `{provider, model_name}` | 识别 8 个提供商 |
  | `get_model_from_config(config)` | RunnableConfig | BaseChatModel | 初始化 LLM |
  | `get_formatted_reflections(config)` | RunnableConfig | `str \| None` | 从 Store 读取 |
  | `create_ai_message_from_web_results(results)` | SearchResult[] | AIMessage | 转换搜索结果 |
  | `format_messages(messages)` | Message[] | Message[] | 格式化消息 |

**参考文件**:
- TS 源码: `apps/agents/src/utils.ts`
- TS 常量: `packages/shared/src/constants.ts`
- 共享类型: `packages/shared/src/types.ts`

---

## Phase 3: 主图 - State & Prompts

**目标**: 迁移主图的 State 定义和 Prompt 模板

**Gate 条件**: State 字段与 TS `apps/agents/src/open-canvas/state.ts` 完全对齐

### 任务清单

- [ ] **3.1 创建 open_canvas/state.py**
  - 参考 TS: `apps/agents/src/open-canvas/state.ts` (140 行)
  - ⚠️ **关键**: 字段名必须 camelCase，与以下列表完全一致:

  **State 字段清单** (与 TS 对齐):
  ```python
  class OpenCanvasState(TypedDict):
      messages: Annotated[list[AnyMessage], add_messages]
      _messages: Annotated[list[AnyMessage], messages_reducer]  # 自定义 reducer
      highlightedCode: Optional[CodeHighlight]
      highlightedText: Optional[TextHighlight]
      artifact: Optional[ArtifactV3]
      next: Optional[str]
      language: Optional[LanguageOptions]
      artifactLength: Optional[ArtifactLengthOptions]
      regenerateWithEmojis: Optional[bool]
      readingLevel: Optional[ReadingLevelOptions]
      addComments: Optional[bool]
      addLogs: Optional[bool]
      portLanguage: Optional[ProgrammingLanguageOptions]
      fixBugs: Optional[bool]
      customQuickActionId: Optional[str]
      webSearchEnabled: Optional[bool]
      webSearchResults: Optional[list[SearchResult]]
  ```

- [ ] **3.2 实现 `_messages` reducer**
  - 参考 TS: `apps/agents/src/open-canvas/state.ts` 第 24-71 行
  - ⚠️ **关键逻辑**: 遇到摘要消息时清空历史再追加
  ```python
  def is_summary_message(msg) -> bool:
      """检测是否为摘要消息"""
      additional_kwargs = getattr(msg, "additional_kwargs", {})
      if additional_kwargs.get(OC_SUMMARIZED_MESSAGE_KEY) is True:
          return True
      # 还需检查 kwargs.additional_kwargs 情况
      kwargs = getattr(msg, "kwargs", {})
      if kwargs.get("additional_kwargs", {}).get(OC_SUMMARIZED_MESSAGE_KEY) is True:
          return True
      return False

  def messages_reducer(left: list, right: list | AnyMessage) -> list:
      right_list = right if isinstance(right, list) else [right]
      if right_list and is_summary_message(right_list[-1]):
          return add_messages([], right_list)  # 清空历史
      return add_messages(left, right_list)
  ```

- [ ] **3.3 创建 open_canvas/prompts.py**
  - 参考 TS: `apps/agents/src/open-canvas/prompts.ts` (374 行)
  - 迁移所有 Prompt 模板（保持动态变量占位符一致）

**参考文件**:
- TS 源码: `apps/agents/src/open-canvas/state.ts`
- TS 源码: `apps/agents/src/open-canvas/prompts.ts`

---

## Phase 4: 主图 - 节点函数

**目标**: 迁移所有主图节点函数

**Gate 条件**: 所有节点函数可独立调用，输入输出符合契约

### 节点契约模板

每个节点函数必须明确:
- **输入字段**: 从 state 读取哪些字段
- **输出字段**: 返回 dict 更新哪些字段
- **错误处理**: LLM 失败、tool_calls 缺失等

### 任务清单

- [ ] **4.1 generate_path.py** (路由决策)
  - 参考 TS: `apps/agents/src/open-canvas/nodes/generate-path/`
  - **功能**: 分析用户输入，设置 `next` 字段决定路由
  - **输入**: `messages`, `artifact`, `highlightedCode`, `highlightedText`, 各种 flags
  - **输出**: `{ "next": "<target_node>" }`
  - **路由目标** (共 9 个):
    - `updateArtifact` - 代码高亮编辑
    - `updateHighlightedText` - Markdown 高亮编辑
    - `rewriteArtifactTheme` - 文本主题变换
    - `rewriteCodeArtifactTheme` - 代码主题变换
    - `customAction` - 自定义操作
    - `webSearch` - 网络搜索
    - `replyToGeneralInput` - 纯对话
    - `generateArtifact` - 新建文档
    - `rewriteArtifact` - 重写文档
  - ⚠️ URL 抓取需要: 超时控制、最大长度、错误降级

- [ ] **4.2 generate_artifact.py** (新建文档)
  - 参考 TS: `apps/agents/src/open-canvas/nodes/generate-artifact/`
  - **输入**: `messages`, `_messages`
  - **输出**: `{ "artifact": ArtifactV3, "messages": [...], "_messages": [...] }`
  - **Schema**: 迁移 `ARTIFACT_TOOL_SCHEMA` → Pydantic BaseModel
  - ⚠️ 使用 `.bind_tools()` 绑定工具

- [ ] **4.3 rewrite_artifact.py** (重写文档)
  - 参考 TS: `apps/agents/src/open-canvas/nodes/rewrite-artifact/`
  - **输入**: `messages`, `_messages`, `artifact`
  - **输出**: `{ "artifact": ArtifactV3, "messages": [...], "_messages": [...] }`
  - ⚠️ 包含思考模型检测和文本提取逻辑

- [ ] **4.4 update_artifact.py** (代码高亮编辑)
  - 参考 TS: `apps/agents/src/open-canvas/nodes/updateArtifact.ts`
  - **输入**: `highlightedCode`, `artifact`, `messages`
  - **输出**: `{ "artifact": ArtifactV3, "messages": [...] }`

- [ ] **4.5 update_highlighted_text.py** (Markdown 高亮编辑)
  - 参考 TS: `apps/agents/src/open-canvas/nodes/updateHighlightedText.ts`
  - **输入**: `highlightedText`, `artifact`, `messages`
  - **输出**: `{ "artifact": ArtifactV3, "messages": [...] }`

- [ ] **4.6 generate_followup.py** (跟进消息)
  - 参考 TS: `apps/agents/src/open-canvas/nodes/generateFollowup.ts`
  - **输入**: `messages`, `artifact`
  - **输出**: `{ "messages": [...] }`
  - **配置**: `max_tokens=250`

- [ ] **4.7 reply_to_general_input.py** (纯对话)
  - 参考 TS: `apps/agents/src/open-canvas/nodes/replyToGeneralInput.ts`
  - **输入**: `messages`, `_messages`
  - **输出**: `{ "messages": [...], "_messages": [...] }`

- [ ] **4.8 custom_action.py** (自定义操作)
  - 参考 TS: `apps/agents/src/open-canvas/nodes/customAction.ts`
  - **输入**: `customQuickActionId`, `artifact`, `messages`
  - **输出**: `{ "artifact": ArtifactV3, "messages": [...] }`
  - ⚠️ 需要从 Store 读取用户自定义 Prompt

- [ ] **4.9 reflect.py** (反思)
  - 参考 TS: `apps/agents/src/open-canvas/nodes/reflect.ts`
  - **功能**: 触发 reflection 子图

- [ ] **4.10 rewrite_artifact_theme.py** (文本主题变换)
  - 参考 TS: `apps/agents/src/open-canvas/nodes/rewriteArtifactTheme.ts`
  - **输入**: `language`, `artifactLength`, `readingLevel`, `regenerateWithEmojis`, `artifact`
  - **输出**: `{ "artifact": ArtifactV3 }`

- [ ] **4.11 rewrite_code_artifact_theme.py** (代码主题变换)
  - 参考 TS: `apps/agents/src/open-canvas/nodes/rewriteCodeArtifactTheme.ts`
  - **输入**: `addComments`, `addLogs`, `portLanguage`, `fixBugs`, `artifact`
  - **输出**: `{ "artifact": ArtifactV3 }`

- [ ] **4.12 generate_title.py** (标题生成)
  - 参考 TS: `apps/agents/src/open-canvas/nodes/generateTitle.ts`
  - **功能**: 使用 GPT-4o-mini 生成对话标题

**参考文件**:
- TS 源码目录: `apps/agents/src/open-canvas/nodes/`

---

## Phase 5: 主图 - 控制流与组装

**目标**: 实现主图控制流函数并组装完整的 StateGraph

**Gate 条件**: 图可编译，`generatePath` 能正确路由到 9 个目标节点

### 任务清单

- [ ] **5.1 实现 route_node 函数**
  - 参考 TS: `apps/agents/src/open-canvas/index.ts` 第 20-28 行
  ```python
  def route_node(state: OpenCanvasState) -> Send:
      if not state.get("next"):
          raise ValueError("'next' state field not set.")
      return Send(state["next"], dict(state))
  ```

- [ ] **5.2 实现 clean_state 函数**
  - 参考 TS: `apps/agents/src/open-canvas/index.ts` 第 30-34 行
  - ⚠️ **关键**: 必须使用 `DEFAULT_INPUTS` 重置状态，防止污染下一轮
  ```python
  def clean_state(state: OpenCanvasState) -> dict:
      return DEFAULT_INPUTS.copy()
  ```

- [ ] **5.3 实现 conditionally_generate_title 函数**
  - 参考 TS: `apps/agents/src/open-canvas/index.ts` 第 64-72 行
  - **逻辑**:
    - 如果 `messages` 长度 > 2 → 调用 `simple_token_calculator`
    - 否则 → 返回 `"generateTitle"`
  ```python
  def conditionally_generate_title(state: OpenCanvasState) -> str:
      if len(state.get("messages", [])) > 2:
          return simple_token_calculator(state)
      return "generateTitle"

  def simple_token_calculator(state: OpenCanvasState) -> str:
      """基于字符数决定是否触发摘要"""
      total_chars = 0
      for msg in state.get("_messages", []):
          content = msg.content
          if isinstance(content, str):
              total_chars += len(content)
          elif isinstance(content, list):
              for c in content:
                  if hasattr(c, "text"):
                      total_chars += len(c.text)
      return "summarizer" if total_chars > CHARACTER_MAX else END
  ```

- [ ] **5.4 实现 route_post_web_search 函数**
  - 参考 TS: `apps/agents/src/open-canvas/index.ts` 第 78-106 行
  - **逻辑**:
    - 如果无搜索结果 → `Send` 到 `generateArtifact/rewriteArtifact`
    - 如果有搜索结果 → `Command` 更新 `messages/_messages` 并路由
  ```python
  def route_post_web_search(state: OpenCanvasState) -> Send | Command:
      includes_artifacts = len(state.get("artifact", {}).get("contents", [])) > 1
      target = "rewriteArtifact" if includes_artifacts else "generateArtifact"

      if not state.get("webSearchResults"):
          return Send(target, {**state, "webSearchEnabled": False})

      web_results_msg = create_ai_message_from_web_results(state["webSearchResults"])
      return Command(
          goto=target,
          update={
              "webSearchEnabled": False,
              "messages": [web_results_msg],
              "_messages": [web_results_msg],
          }
      )
  ```

- [ ] **5.5 组装 StateGraph**
  - 参考 TS: `apps/agents/src/open-canvas/index.ts` 第 108-162 行

  **节点清单** (共 15 个):
  ```python
  builder = StateGraph(OpenCanvasState)
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
  builder.add_node("generateTitle", generate_title)
  builder.add_node("summarizer", summarizer)
  builder.add_node("webSearch", web_search_graph)  # 子图
  builder.add_node("routePostWebSearch", route_post_web_search)
  ```

  **边配置**:
  ```python
  # 起始边
  builder.add_edge(START, "generatePath")

  # 条件路由 (9 个目标)
  builder.add_conditional_edges("generatePath", route_node, [
      "updateArtifact", "rewriteArtifactTheme", "rewriteCodeArtifactTheme",
      "replyToGeneralInput", "generateArtifact", "rewriteArtifact",
      "customAction", "updateHighlightedText", "webSearch",
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
      END, "generateTitle", "summarizer"
  ])
  builder.add_edge("generateTitle", END)
  builder.add_edge("summarizer", END)

  graph = builder.compile()
  ```

**参考文件**:
- TS 源码: `apps/agents/src/open-canvas/index.ts`

---

## Phase 6: 辅助图

**目标**: 迁移 4 个辅助图

**Gate 条件**: 4 个子图全部可独立编译和调用

### 任务清单

- [ ] **6.1 reflection 图**
  - 参考 TS: `apps/agents/src/reflection/`
  - 功能: 生成风格规则和用户事实，存储到 LangGraph Store
  - ⚠️ 使用 `config["store"]` 进行 async put 操作

- [ ] **6.2 thread-title 图**
  - 参考 TS: `apps/agents/src/thread-title/`
  - 功能: 使用 GPT-4o-mini 生成对话标题
  - ⚠️ 使用 LangGraph SDK Client 更新线程元数据

- [ ] **6.3 summarizer 图**
  - 参考 TS: `apps/agents/src/summarizer/`
  - 功能: 压缩长对话
  - ⚠️ 标记摘要消息以触发 reducer 清空历史

- [ ] **6.4 web-search 图**
  - 参考 TS: `apps/agents/src/web-search/`
  - 功能: 3 节点图 (classify → query_generator → search)
  - ⚠️ 使用 Exa API，需要 `EXA_API_KEY`
  - ⚠️ 超时控制、空结果降级

**参考文件**:
- TS 源码目录: `apps/agents/src/{reflection,thread-title,summarizer,web-search}/`

---

## Phase 7: 集成测试

**目标**: 验证 Python 后端与前端的完整集成

**Gate 条件**: 所有关键路径测试通过

### 任务清单

- [ ] **7.1 单元测试** (新增)
  - `_messages reducer` 测试: 摘要消息触发清空
  - `clean_state` 测试: 返回值与 `DEFAULT_INPUTS` 一致
  - `simple_token_calculator` 测试: 阈值分支正确
  - `conditionally_generate_title` 测试: 消息数分支正确

- [ ] **7.2 路由矩阵测试** (新增)

  | State 条件 | 期望目标节点 |
  |------------|--------------|
  | `highlightedCode` 存在 | `updateArtifact` |
  | `highlightedText` 存在 | `updateHighlightedText` |
  | `language` 或 `artifactLength` 存在 | `rewriteArtifactTheme` |
  | `addComments` 或 `fixBugs` 存在 | `rewriteCodeArtifactTheme` |
  | `customQuickActionId` 存在 | `customAction` |
  | `webSearchEnabled=True` | `webSearch` |
  | 无 artifact | `generateArtifact` |
  | 有 artifact，用户请求修改 | `rewriteArtifact` |
  | 一般对话 | `replyToGeneralInput` |

- [ ] **7.3 本地启动验证**
  ```bash
  cd apps/agents-py && langgraph dev --port 54367
  cd apps/web && yarn dev
  # 访问 http://localhost:3000
  ```

- [ ] **7.4 API 端点测试**
  ```bash
  curl http://localhost:54367/health
  curl http://localhost:54367/assistants
  ```

- [ ] **7.5 流式传输测试**
  - 前端发送消息，验证 SSE 流正常

- [ ] **7.6 功能回归测试**
  - [ ] 创建新文档 (Markdown/代码)
  - [ ] 代码高亮编辑
  - [ ] Markdown 高亮编辑
  - [ ] 快捷操作 (翻译/长度/阅读级别)
  - [ ] 自定义操作
  - [ ] 网络搜索
  - [ ] 对话压缩 (发送足够长的对话触发)
  - [ ] 标题生成 (首次对话后检查)

---

## Phase 8: 部署

**目标**: 配置生产环境部署

**Gate 条件**: 生产环境 `/health` 可访问

### 任务清单

- [ ] **8.1 Docker 构建**
  ```bash
  cd apps/agents-py
  langgraph build -t open-canvas-agents:latest
  ```

- [ ] **8.2 Docker Compose 配置**
  - 容器内端口: 8000
  - 宿主映射端口: 54367
  - 环境变量注入: `--env-file .env`

- [ ] **8.3 生产环境部署**
  - K8s/CI/CD 配置
  - 监控和日志

---

## 验证清单

### 功能验证 (12 项)

| 功能 | 验证方法 | 状态 |
|------|----------|------|
| 创建新 Markdown 文档 | 发送 "写一篇关于..." | ⬜ |
| 创建新代码文档 | 发送 "写一个 Python 函数..." | ⬜ |
| 代码高亮编辑 | 选中代码后发送修改请求 | ⬜ |
| Markdown 高亮编辑 | 选中文本后发送修改请求 | ⬜ |
| 快捷操作 - 翻译 | 使用翻译快捷按钮 | ⬜ |
| 快捷操作 - 长度调整 | 使用长度调整按钮 | ⬜ |
| 自定义操作 | 创建并执行自定义操作 | ⬜ |
| 网络搜索 | 启用搜索后发送请求 | ⬜ |
| 对话压缩 | 长对话后检查消息历史 | ⬜ |
| 标题生成 | 检查对话标题自动更新 | ⬜ |
| 反思/记忆 | 验证风格规则被记住 | ⬜ |
| 版本历史 | 检查 artifact 版本切换 | ⬜ |

### API 兼容性 (4 项)

| 检查项 | 状态 |
|--------|------|
| `/health` 端点 | ⬜ |
| `/assistants` 端点 | ⬜ |
| `/threads` 端点 | ⬜ |
| 流式传输 SSE | ⬜ |

---

## 常见问题

### Q: State 字段名必须用 camelCase 吗？
**A**: ⚠️ **必须**。LangGraph Server 不会自动转换。

### Q: `_messages` reducer 为什么重要？
**A**: 遇到摘要消息时清空历史。否则上下文无限增长。

### Q: `DEFAULT_INPUTS` 重置为什么重要？
**A**: 防止上一轮的 `language`/`artifactLength` 等 flags 污染下一轮路由。

### Q: 路由到底有多少个目标节点？
**A**: **9 个** (见 Phase 5.5)，不是 13 个。

### Q: `messages` 和 `_messages` 有什么区别？
**A**:
- `messages`: 对 UI 友好的完整对话流
- `_messages`: 给模型的内部上下文（可能被摘要压缩）

### Q: 摘要什么时候触发？
**A**: 当 `_messages` 总字符数超过 `CHARACTER_MAX` (300000) 时。

---

## 参考资源

- **技术方案**: [docs/plan/langgraph-python-migration.md](../plan/langgraph-python-migration.md)
- **TS 源码**: `apps/agents/src/`
- **TS 常量**: `packages/shared/src/constants.ts`
- **LangGraph Python 文档**: https://langchain-ai.github.io/langgraph/
