# Open Canvas LangGraph 智能体架构

本文档详细介绍 Open Canvas 后端的 LangGraph 智能体系统架构，包括各图的功能、节点设计、状态管理和协作机制。

## 目录

- [系统概览](#系统概览)
- [架构图](#架构图)
- [主智能体图 (Open Canvas)](#主智能体图-open-canvas)
- [反思图 (Reflection)](#反思图-reflection)
- [网络搜索图 (Web Search)](#网络搜索图-web-search)
- [标题生成图 (Thread Title)](#标题生成图-thread-title)
- [摘要图 (Summarizer)](#摘要图-summarizer)
- [工具函数库](#工具函数库)
- [提示词策略](#提示词策略)
- [多模型支持](#多模型支持)

---

## 系统概览

Open Canvas 采用 **多图协作架构**，通过 LangGraph 编排 5 个专门的图来处理不同的工作流：

```
langgraph.json 配置的 5 个图：
├── agent (open-canvas)     → 主图：路由、工件生成与编辑
├── reflection              → 记忆反思：用户风格学习
├── thread_title            → 标题生成：对话命名
├── summarizer              → 对话摘要：长对话压缩
└── web_search              → 网络搜索：实时信息检索
```

### 核心设计理念

| 设计特征 | 说明 |
|---------|------|
| **高度模块化** | 5 个独立图，各司其职，易于维护和扩展 |
| **智能路由** | generatePath 通过条件规则精准导航到目标节点 |
| **版本管理** | 完整的工件历史，支持版本回滚 |
| **记忆系统** | 持久化用户风格偏好和事实信息 |
| **多 LLM 支持** | 灵活的模型选择和智能降级策略 |
| **消息分层** | 用户界面消息与模型输入消息分离 |

---

## 架构图

### 整体系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        Open Canvas 系统                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐       │
│  │   Frontend   │───▶│  LangGraph   │───▶│   LLM APIs   │       │
│  │   (Next.js)  │◀───│   Server     │◀───│  (Multi-LLM) │       │
│  └──────────────┘    └──────────────┘    └──────────────┘       │
│                             │                                    │
│                             ▼                                    │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                    LangGraph 图编排                       │    │
│  │  ┌─────────┐ ┌────────────┐ ┌────────────┐ ┌─────────┐  │    │
│  │  │  Main   │ │ Reflection │ │ Web Search │ │ Title   │  │    │
│  │  │  Agent  │ │   Graph    │ │   Graph    │ │ Graph   │  │    │
│  │  └─────────┘ └────────────┘ └────────────┘ └─────────┘  │    │
│  │                    ┌────────────┐                        │    │
│  │                    │ Summarizer │                        │    │
│  │                    │   Graph    │                        │    │
│  │                    └────────────┘                        │    │
│  └─────────────────────────────────────────────────────────┘    │
│                             │                                    │
│                             ▼                                    │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                    持久化存储                             │    │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐      │    │
│  │  │  Memories   │  │   Threads   │  │  Artifacts  │      │    │
│  │  │  (反思记忆)  │  │  (对话线程)  │  │  (版本工件)  │      │    │
│  │  └─────────────┘  └─────────────┘  └─────────────┘      │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 主智能体流程图

```
                              START
                                │
                                ▼
                        ┌───────────────┐
                        │  generatePath │ ◀─── 路由决策引擎
                        └───────────────┘
                                │
            ┌───────────────────┼───────────────────┐
            │                   │                   │
            ▼                   ▼                   ▼
    ┌───────────────┐   ┌───────────────┐   ┌───────────────┐
    │ Artifact 操作  │   │   主题修改     │   │   其他路由     │
    ├───────────────┤   ├───────────────┤   ├───────────────┤
    │generateArtifact│   │rewriteTheme   │   │replyToGeneral │
    │rewriteArtifact │   │rewriteCode    │   │customAction   │
    │updateArtifact  │   │Theme          │   │webSearch      │
    │updateHighlight │   │               │   │               │
    └───────────────┘   └───────────────┘   └───────────────┘
            │                   │                   │
            └───────────────────┼───────────────────┘
                                │
                                ▼
                        ┌───────────────┐
                        │generateFollowup│ ◀─── 生成跟进消息
                        └───────────────┘
                                │
                                ▼
                        ┌───────────────┐
                        │    reflect    │ ◀─── 触发记忆更新
                        └───────────────┘
                                │
                                ▼
                        ┌───────────────┐
                        │  cleanState   │ ◀─── 重置状态参数
                        └───────────────┘
                                │
                    ┌───────────┼───────────┐
                    │           │           │
                    ▼           ▼           ▼
               ┌────────┐ ┌──────────┐ ┌──────────┐
               │  END   │ │ genTitle │ │summarizer│
               └────────┘ └──────────┘ └──────────┘
```

---

## 主智能体图 (Open Canvas)

主智能体是系统的核心，负责处理所有用户交互和工件操作。

### 状态定义 (State)

```typescript
interface OpenCanvasGraphAnnotation {
  // ═══════════════════════════════════════════════════
  // 消息管理
  // ═══════════════════════════════════════════════════
  messages: BaseMessage[];      // 用户可见的完整对话
  _messages: BaseMessage[];     // 内部消息（含摘要，用于模型输入）

  // ═══════════════════════════════════════════════════
  // 工件管理
  // ═══════════════════════════════════════════════════
  artifact: ArtifactV3;         // 版本控制工件
  // └─ currentIndex: number    // 当前版本索引
  // └─ contents: Array<...>    // 版本历史数组

  // ═══════════════════════════════════════════════════
  // 用户交互状态
  // ═══════════════════════════════════════════════════
  highlightedCode: CodeHighlight;   // 代码高亮选区
  highlightedText: TextHighlight;   // 文本高亮选区

  // ═══════════════════════════════════════════════════
  // 快捷操作参数
  // ═══════════════════════════════════════════════════
  customQuickActionId: string;      // 自定义操作 ID
  language: LanguageOptions;        // 翻译语言
  artifactLength: ArtifactLengthOptions;  // 调整长度
  readingLevel: ReadingLevelOptions;      // 阅读级别
  regenerateWithEmojis: boolean;    // 添加表情符号
  addComments: boolean;             // 代码注释
  addLogs: boolean;                 // 调试日志
  portLanguage: ProgrammingLanguageOptions;  // 代码转换语言
  fixBugs: boolean;                 // 修复漏洞

  // ═══════════════════════════════════════════════════
  // 搜索相关
  // ═══════════════════════════════════════════════════
  webSearchEnabled: boolean;        // 是否启用网络搜索
  webSearchResults: SearchResult[]; // 搜索结果

  // ═══════════════════════════════════════════════════
  // 路由控制
  // ═══════════════════════════════════════════════════
  next: string;                     // 下一个节点名称
}
```

### 核心节点详解

#### 1. generatePath（路由决策引擎）

这是系统的"智能交通枢纽"，通过优先级规则决定请求流向：

```typescript
async function generatePath(state, config) {
  // ┌─────────────────────────────────────────────────────┐
  // │ 优先级 1: 高亮选区操作                               │
  // └─────────────────────────────────────────────────────┘
  if (state.highlightedCode) return "updateArtifact";
  if (state.highlightedText) return "updateHighlightedText";

  // ┌─────────────────────────────────────────────────────┐
  // │ 优先级 2: 文本主题修改                               │
  // └─────────────────────────────────────────────────────┘
  if (state.language || state.artifactLength ||
      state.regenerateWithEmojis || state.readingLevel) {
    return "rewriteArtifactTheme";
  }

  // ┌─────────────────────────────────────────────────────┐
  // │ 优先级 3: 代码主题修改                               │
  // └─────────────────────────────────────────────────────┘
  if (state.addComments || state.addLogs ||
      state.portLanguage || state.fixBugs) {
    return "rewriteCodeArtifactTheme";
  }

  // ┌─────────────────────────────────────────────────────┐
  // │ 优先级 4: 特殊操作                                   │
  // └─────────────────────────────────────────────────────┘
  if (state.customQuickActionId) return "customAction";
  if (state.webSearchEnabled) return "webSearch";

  // ┌─────────────────────────────────────────────────────┐
  // │ 优先级 5: 动态路由（LLM 决策）                        │
  // └─────────────────────────────────────────────────────┘
  return await dynamicDeterminePath({ state, config });
  // 返回: "generateArtifact" | "rewriteArtifact" | "replyToGeneralInput"
}
```

**路由决策矩阵**：

| 条件 | 目标节点 | 说明 |
|------|---------|------|
| `highlightedCode` 存在 | updateArtifact | 更新选中的代码 |
| `highlightedText` 存在 | updateHighlightedText | 更新选中的文本 |
| 语言/长度/表情/阅读级别 | rewriteArtifactTheme | 文本主题修改 |
| 注释/日志/转换/修复 | rewriteCodeArtifactTheme | 代码主题修改 |
| `customQuickActionId` 存在 | customAction | 执行自定义操作 |
| `webSearchEnabled` 为 true | webSearch | 网络搜索 |
| 无工件 + 生成请求 | generateArtifact | 创建新工件 |
| 有工件 + 修改请求 | rewriteArtifact | 重写现有工件 |
| 一般性问题 | replyToGeneralInput | 直接回复 |

#### 2. generateArtifact（工件生成）

创建新的工件（代码或文档）：

```typescript
async function generateArtifact(state, config) {
  // 1. 获取模型配置
  const model = await getModelFromConfig(config, { isToolCalling: true });

  // 2. 构建提示词
  const systemPrompt = buildSystemPrompt({
    appContext: APP_CONTEXT,
    reflections: await getFormattedReflections(config),
    codeRules: DEFAULT_CODE_PROMPT_RULES
  });

  // 3. 绑定工具并调用
  const modelWithTool = model.bindTools([{
    name: "generate_artifact",
    schema: {
      title: z.string(),
      type: z.enum(["text", "code"]),
      language: z.string().optional(),
      content: z.string()
    }
  }]);

  // 4. 创建工件版本 1
  return {
    artifact: {
      currentIndex: 1,
      contents: [newArtifactContent]
    }
  };
}
```

#### 3. rewriteArtifact（工件重写）

完整重写现有工件：

```typescript
async function rewriteArtifact(state, config) {
  // 1. 验证工件存在
  if (!state.artifact) throw new Error("No artifact to rewrite");

  // 2. 可选：更新元数据（标题/类型）
  const metadata = await getUpdatedMetadata(state, config);

  // 3. 使用 UPDATE_ENTIRE_ARTIFACT_PROMPT 重写
  const newContent = await model.invoke([
    systemPrompt,
    ...state._messages
  ]);

  // 4. 添加新版本（保留历史）
  return {
    artifact: {
      currentIndex: state.artifact.currentIndex + 1,
      contents: [...state.artifact.contents, newVersion]
    }
  };
}
```

#### 4. updateArtifact（部分更新）

更新高亮选中的代码部分：

```typescript
async function updateArtifact(state, config) {
  // 1. 提取高亮区域上下文（±500 字符）
  const { before, highlighted, after } = extractContext(
    currentContent,
    state.highlightedCode
  );

  // 2. 模型只生成替换内容
  const replacement = await model.invoke(
    UPDATE_HIGHLIGHTED_ARTIFACT_PROMPT
  );

  // 3. 拼接完整内容
  const newContent = before + replacement + after;

  // 4. 创建新版本
  return { artifact: createNewVersion(state.artifact, newContent) };
}
```

#### 5. generateFollowup（跟进生成）

生成简短的跟进消息：

```typescript
async function generateFollowup(state, config) {
  const model = await getModelFromConfig(config, {
    isToolCalling: true,
    maxTokens: 250  // 限制长度
  });

  const response = await model.invoke([
    FOLLOWUP_ARTIFACT_PROMPT,
    { artifact: getArtifactContent(state.artifact) },
    { reflections: await getFormattedReflections(config) }
  ]);

  // 返回简短、友好的跟进消息
  // 例: "Does this capture what you had in mind?"
  return { messages: [new AIMessage(response)] };
}
```

#### 6. cleanState（状态清理）

重置所有快捷操作参数：

```typescript
function cleanState(state) {
  return {
    language: undefined,
    artifactLength: undefined,
    readingLevel: undefined,
    addComments: undefined,
    addLogs: undefined,
    portLanguage: undefined,
    fixBugs: undefined,
    customQuickActionId: undefined,
    webSearchEnabled: false
  };
}
```

### 快捷操作一览

#### 文本操作 (rewriteArtifactTheme)

| 操作 | 提示词 | 说明 |
|------|--------|------|
| 翻译 | CHANGE_ARTIFACT_LANGUAGE_PROMPT | 翻译到指定语言 |
| 阅读级别 | CHANGE_ARTIFACT_READING_LEVEL_PROMPT | 调整文本复杂度 |
| 添加表情 | ADD_EMOJIS_TO_ARTIFACT_PROMPT | 在文本中加入表情符号 |
| 调整长度 | CHANGE_ARTIFACT_LENGTH_PROMPT | 扩展或缩短文本 |

#### 代码操作 (rewriteCodeArtifactTheme)

| 操作 | 提示词 | 说明 |
|------|--------|------|
| 添加注释 | ADD_COMMENTS_TO_CODE_ARTIFACT_PROMPT | 添加代码注释 |
| 添加日志 | ADD_LOGS_TO_CODE_ARTIFACT_PROMPT | 添加调试日志语句 |
| 修复漏洞 | FIX_BUGS_CODE_ARTIFACT_PROMPT | 识别并修复潜在 bug |
| 语言转换 | PORT_LANGUAGE_CODE_ARTIFACT_PROMPT | 转换到其他编程语言 |

---

## 反思图 (Reflection)

反思图负责学习用户的写作风格和偏好，构建持久化的用户记忆。

### 架构

```
START ──▶ [reflect] ──▶ END
```

### 状态定义

```typescript
interface ReflectionGraphAnnotation {
  messages: BaseMessage[];      // 对话历史
  artifact: ArtifactV3 | undefined;  // 当前工件
}
```

### 反思节点实现

```typescript
async function reflect(state, config) {
  const store = config.configurable.store;
  const memoryNamespace = ["memories", assistantId];

  // 1. 检索现有记忆
  const existingMemories = await store.get(memoryNamespace, "reflection");

  // 2. 使用固定模型生成反思
  const model = new ChatAnthropic({
    model: "claude-3-5-sonnet-20240620",
    temperature: 0
  }).bindTools([{
    name: "generate_reflections",
    schema: {
      styleRules: z.array(z.string()),  // 风格规则列表
      content: z.array(z.string())      // 用户事实列表
    }
  }]);

  // 3. 调用并存储
  const result = await model.invoke([systemPrompt, userPrompt]);
  await store.put(memoryNamespace, "reflection", result.tool_calls[0].args);
}
```

### 记忆结构

```typescript
interface Reflections {
  styleRules: string[];  // 写作风格偏好
  // 例: ["偏好简洁的句子", "使用技术术语", "避免被动语态"]

  content: string[];     // 用户事实/偏好
  // 例: ["是一名前端开发者", "主要使用 React", "偏好 TypeScript"]
}
```

### 记忆使用流程

```
┌─────────────────┐
│ generateArtifact │ ◀─── 注入 reflections 到提示词
└─────────────────┘
         │
         ▼
┌─────────────────┐
│ generateFollowup │ ◀─── 使用 reflections 个性化回复
└─────────────────┘
         │
         ▼
┌─────────────────┐
│     reflect     │ ◀─── 更新 reflections
└─────────────────┘
         │
         ▼
┌─────────────────┐
│   LangGraph     │
│     Store       │ ◀─── 持久化存储
└─────────────────┘
```

---

## 网络搜索图 (Web Search)

网络搜索图提供实时信息检索能力，基于 Exa API 实现。

### 架构

```
        START
          │
          ▼
  ┌───────────────┐
  │classifyMessage│ ◀─── 判断是否需要搜索
  └───────────────┘
          │
    ┌─────┴─────┐
    │           │
    ▼           ▼
 需要搜索    不需要搜索
    │           │
    ▼           │
┌──────────┐    │
│queryGen  │    │
└──────────┘    │
    │           │
    ▼           │
┌──────────┐    │
│  search  │    │
└──────────┘    │
    │           │
    └─────┬─────┘
          │
          ▼
         END
```

### 状态定义

```typescript
interface WebSearchGraphAnnotation {
  messages: BaseMessage[];
  query: string;                    // 搜索查询
  webSearchResults: SearchResult[]; // 搜索结果
  shouldSearch: boolean;            // 是否执行搜索
}
```

### 节点实现

#### classifyMessage（搜索分类）

```typescript
async function classifyMessage(state) {
  const model = new ChatAnthropic({
    model: "claude-3-5-sonnet-latest",
    temperature: 0
  }).withStructuredOutput({
    schema: z.object({ shouldSearch: z.boolean() })
  });

  // 评估消息是否需要网络搜索
  const response = await model.invoke([
    ["user", CLASSIFIER_PROMPT.replace("{message}", latestMessage)]
  ]);

  return { shouldSearch: response.shouldSearch };
}
```

#### queryGenerator（查询生成）

```typescript
async function queryGenerator(state) {
  const model = new ChatAnthropic({
    model: "claude-3-5-sonnet-latest"
  });

  // 将对话转换为搜索友好的查询
  const formattedPrompt = QUERY_GENERATOR_PROMPT
    .replace("{conversation}", formatMessages(state.messages))
    .replace("{additional_context}", `Current date: ${today}`);

  const response = await model.invoke([["user", formattedPrompt]]);
  return { query: response.content };
}
```

### 主图中的搜索集成

```typescript
// 搜索完成后的路由
function routePostWebSearch(state) {
  if (!state.webSearchResults?.length) {
    return hasArtifact ? "rewriteArtifact" : "generateArtifact";
  }

  // 创建搜索结果消息并注入到状态
  const searchResultsMessage = createAIMessageFromWebResults(
    state.webSearchResults
  );

  return new Command({
    goto: hasArtifact ? "rewriteArtifact" : "generateArtifact",
    update: {
      webSearchEnabled: false,
      messages: [searchResultsMessage],
      _messages: [searchResultsMessage]
    }
  });
}
```

---

## 标题生成图 (Thread Title)

自动为对话线程生成有意义的标题。

### 架构

```
START ──▶ [generateTitle] ──▶ END
```

### 实现

```typescript
async function generateTitle(state, config) {
  const threadId = config.configurable.open_canvas_thread_id;

  // 使用轻量级模型生成标题
  const model = new ChatOpenAI({
    model: "gpt-4o-mini",
    temperature: 0
  }).bindTools([{
    name: "generate_title",
    schema: { title: z.string() }
  }]);

  const result = await model.invoke([
    { role: "system", content: TITLE_SYSTEM_PROMPT },
    { role: "user", content: TITLE_USER_PROMPT
        .replace("{conversation}", formatMessages(state.messages))
        .replace("{artifact_context}", artifactContent)
    }
  ]);

  // 更新线程元数据
  const langGraphClient = new Client();
  await langGraphClient.threads.update(threadId, {
    metadata: { thread_title: result.tool_calls[0].args.title }
  });
}
```

### 触发条件

```typescript
// 仅在首次交互时触发
if (state.messages.length <= 2) {
  return "generateTitle";
}
```

---

## 摘要图 (Summarizer)

当对话过长时自动压缩历史消息。

### 架构

```
START ──▶ [summarize] ──▶ END
```

### 触发条件

```typescript
const CHARACTER_MAX = 300_000;  // ~75K tokens

function shouldSummarize(state) {
  const totalChars = state.messages
    .map(m => getStringFromContent(m.content))
    .join('')
    .length;

  return totalChars > CHARACTER_MAX;
}
```

### 实现

```typescript
async function summarizer(state) {
  const model = new ChatAnthropic({
    model: "claude-3-5-sonnet-latest"
  });

  // 生成摘要
  const response = await model.invoke([
    ["system", SUMMARIZER_PROMPT],
    ["user", `Messages to summarize:\n${formatMessages(state.messages)}`]
  ]);

  // 创建带特殊标记的摘要消息
  const summaryMessage = new HumanMessage({
    id: uuidv4(),
    content: `Summary of past messages:\n${response.content}`,
    additional_kwargs: {
      [OC_SUMMARIZED_MESSAGE_KEY]: true  // 特殊标记
    }
  });

  // 状态缩减器识别此标记，清空旧消息
  await client.threads.updateState(threadId, {
    values: { _messages: [summaryMessage] }
  });
}
```

### 消息缩减机制

```typescript
// 状态注解中的消息缩减器
_messages: Annotation<BaseMessage[]>({
  reducer: (existing, update) => {
    // 检测摘要消息
    if (update.some(m => m.additional_kwargs[OC_SUMMARIZED_MESSAGE_KEY])) {
      return update;  // 清空旧消息，只保留摘要
    }
    return [...existing, ...update];
  }
})
```

---

## 工具函数库

### 反思管理

```typescript
// 格式化反思为提示词
formatReflections(reflections, { onlyStyle?, onlyContent? })
  → 将 styleRules 和 content 格式化为 XML 标签

// 从存储检索反思
getFormattedReflections(config)
  → 返回格式化后的用户反思字符串

// 验证存储配置
ensureStoreInConfig(config)
  → 确保 LangGraph Store 可用
```

### 消息管理

```typescript
// 格式化消息为可读文本
formatMessages(messages)
  → "Human: ...\nAssistant: ..."

// 搜索结果转 AI 消息
createAIMessageFromWebResults(results)
  → AIMessage with formatted search results

// 提取消息文本内容
getStringFromContent(content)
  → 从复杂消息结构中提取纯文本
```

### 模型管理

```typescript
// 获取模型配置
getModelConfig(config, options)
  → { modelName, modelProvider }

// 初始化模型实例
getModelFromConfig(config, { isToolCalling, maxTokens })
  → ChatOpenAI | ChatAnthropic | ChatGoogleGenerativeAI | ...

// 检测特殊模型
isUsingO1MiniModel(config)  // o1 系列需特殊处理
isThinkingModel(modelName)  // 思维模型需提取 thinking

// 提取思维内容
extractThinkingAndResponseTokens(content)
  → { thinking: string, response: string }
```

### 工件操作

```typescript
// 获取当前版本内容
getArtifactContent(artifact)
  → artifact.contents[artifact.currentIndex - 1]

// 类型判断
isArtifactMarkdownContent(content)  → boolean
isArtifactCodeContent(content)      → boolean
```

---

## 提示词策略

### 核心提示词原则

| 原则 | 说明 |
|------|------|
| **应用上下文** | 解释 Open Canvas 是什么，说明单工件设计 |
| **代码规则** | React 样式放 style 元素，不包含三反引号 |
| **修改约束** | 仅修改请求的方面，不改变原始含义 |
| **输出格式** | 返回完整内容，不添加 XML 标签 |

### 提示词清单

| 提示词 | 用途 | 使用模型 |
|--------|------|---------|
| `NEW_ARTIFACT_PROMPT` | 生成新工件 | 配置模型 |
| `UPDATE_ENTIRE_ARTIFACT_PROMPT` | 完整重写 | 配置模型 |
| `UPDATE_HIGHLIGHTED_ARTIFACT_PROMPT` | 部分编辑 | 配置模型 |
| `CHANGE_ARTIFACT_LANGUAGE_PROMPT` | 翻译 | 配置模型 |
| `CHANGE_ARTIFACT_READING_LEVEL_PROMPT` | 阅读级别 | 配置模型 |
| `ADD_EMOJIS_TO_ARTIFACT_PROMPT` | 添加表情 | 配置模型 |
| `ADD_COMMENTS_TO_CODE_ARTIFACT_PROMPT` | 代码注释 | 配置模型 |
| `ADD_LOGS_TO_CODE_ARTIFACT_PROMPT` | 调试日志 | 配置模型 |
| `FIX_BUGS_CODE_ARTIFACT_PROMPT` | 修复漏洞 | 配置模型 |
| `PORT_LANGUAGE_CODE_ARTIFACT_PROMPT` | 代码转换 | 配置模型 |
| `FOLLOWUP_ARTIFACT_PROMPT` | 跟进消息 | 小模型 |
| `ROUTE_QUERY_PROMPT` | 路由决策 | 配置模型 |
| `REFLECT_SYSTEM_PROMPT` | 记忆生成 | Claude 3.5 |
| `CLASSIFIER_PROMPT` | 搜索分类 | Claude 3.5 |
| `QUERY_GENERATOR_PROMPT` | 查询优化 | Claude 3.5 |
| `TITLE_USER_PROMPT` | 标题生成 | GPT-4o-mini |
| `SUMMARIZER_PROMPT` | 对话摘要 | Claude 3.5 |

---

## 多模型支持

### 模型选择策略

| 节点 | 模型选择 | 说明 |
|------|---------|------|
| generatePath | 配置模型 | 用户选择的主模型 |
| generateArtifact | 配置模型 | 支持工具调用 |
| rewriteArtifact | 配置模型 | 支持工具调用 |
| updateArtifact | 配置模型/降级 | 简单模型降级到 GPT-4o |
| generateFollowup | 配置模型（小） | maxTokens: 250 |
| reflect | Claude 3.5 Sonnet | 固定，确保质量 |
| generateTitle | GPT-4o-mini | 固定，轻量级 |
| classifyMessage | Claude 3.5 Sonnet | 固定 |
| queryGenerator | Claude 3.5 Sonnet | 固定 |
| summarizer | Claude 3.5 Sonnet | 固定 |

### 特殊模型处理

#### O1 系列模型

```typescript
if (isUsingO1MiniModel(modelName)) {
  // o1 系列不支持 system 角色
  // 将系统提示作为用户消息发送
  messages = [
    { role: "user", content: systemPrompt },
    ...userMessages
  ];
}
```

#### 思维模型 (Claude Extended Thinking)

```typescript
if (isThinkingModel(modelName)) {
  const { thinking, response } = extractThinkingAndResponseTokens(content);

  // thinking 保存为单独的 AI 消息
  // 供用户在 UI 中查看思考过程
  return {
    messages: [
      new AIMessage({ content: thinking, name: "thinking" }),
      new AIMessage({ content: response })
    ]
  };
}
```

### 支持的 LLM 提供商

| 提供商 | 包 | 典型模型 |
|--------|-----|---------|
| OpenAI | `@langchain/openai` | GPT-4o, GPT-4o-mini, o1 |
| Anthropic | `@langchain/anthropic` | Claude 3.5 Sonnet, Claude 3 Opus |
| Google | `@langchain/google-genai` | Gemini Pro, Gemini Ultra |
| Groq | `@langchain/groq` | Llama, Mixtral |
| Fireworks | `@langchain/community` | 各种开源模型 |
| Ollama | `@langchain/ollama` | 本地模型 |

---

## 数据流总结

### 完整请求流程

```
┌─────────────────────────────────────────────────────────────────┐
│                         用户请求                                 │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│ 1. generatePath 路由决策                                         │
│    - 检查快捷操作参数                                             │
│    - 检查高亮选区                                                 │
│    - 动态 LLM 分类                                               │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│ 2. 核心处理节点                                                   │
│    - generateArtifact / rewriteArtifact / updateArtifact        │
│    - rewriteTheme / customAction / webSearch                    │
│    - replyToGeneralInput                                        │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│ 3. 后处理                                                        │
│    - generateFollowup（生成跟进消息）                             │
│    - reflect（更新用户记忆）                                      │
│    - cleanState（重置状态）                                       │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│ 4. 条件后处理                                                     │
│    - generateTitle（首次对话）                                    │
│    - summarizer（超长对话）                                       │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                         响应返回                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 版本控制机制

```
ArtifactV3 {
  currentIndex: 3,           // 当前显示版本 3
  contents: [
    { v1 content... },       // 版本 1（初始）
    { v2 content... },       // 版本 2（第一次修改）
    { v3 content... },       // 版本 3（当前）← currentIndex 指向这里
  ]
}

用户可以：
- 浏览历史版本
- 回滚到任意版本
- 从历史版本分支
```

---

## 扩展指南

### 添加新的快捷操作

1. 在 `state.ts` 中添加新的状态字段
2. 在 `generatePath` 中添加路由条件
3. 创建新的处理节点或复用现有节点
4. 在 `prompts.ts` 中添加对应提示词
5. 在 `cleanState` 中添加状态重置

### 添加新的图

1. 在 `apps/agents/src/` 下创建新目录
2. 实现 `index.ts`（图定义）、`state.ts`（状态）、`nodes.ts`（节点）
3. 在 `langgraph.json` 中注册新图
4. 在主图中添加调用逻辑（如需要）

### 支持新的 LLM 提供商

1. 安装对应的 `@langchain/*` 包
2. 在 `packages/shared/src/models.ts` 中添加模型配置
3. 在 `apps/agents/src/utils.ts` 的 `getModelFromConfig` 中添加初始化逻辑
4. 测试：生成工件、跟进消息、快捷操作

---

## 参考资源

- [LangGraph 官方文档](https://langchain-ai.github.io/langgraph/)
- [Open Canvas GitHub](https://github.com/langchain-ai/open-canvas)
- [LangChain TypeScript](https://js.langchain.com/)
