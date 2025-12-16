# Open Canvas React App Artifact 完整流程详解

本文档详细解释从用户输入到 React App Artifact 生成、渲染，以及后续对话修改代码的完整技术流程。

---

## 目录

1. [系统架构概览](#1-系统架构概览)
2. [用户输入处理](#2-用户输入处理)
3. [Agent 路由决策](#3-agent-路由决策)
4. [Artifact 生成流程](#4-artifact-生成流程)
5. [前端渲染机制](#5-前端渲染机制)
6. [代码修改机制](#6-代码修改机制)
7. [版本管理系统](#7-版本管理系统)
8. [关键文件映射](#8-关键文件映射)

---

## 1. 系统架构概览

Open Canvas 采用前后端分离架构：

```
┌─────────────────────────────────────────────────────────────────┐
│                        前端 (Next.js)                           │
│  ┌─────────────┐    ┌─────────────┐    ┌──────────────────┐   │
│  │ Composer    │───▶│ GraphContext│───▶│ StreamWorker     │   │
│  │ (用户输入)   │    │ (状态管理)   │    │ (Web Worker)     │   │
│  └─────────────┘    └─────────────┘    └────────┬─────────┘   │
│                                                  │              │
│  ┌─────────────────────────────────────────────┐│              │
│  │           ArtifactRenderer                  ││              │
│  │  ┌─────────────┐  ┌───────────────────┐    ││              │
│  │  │ CodeRenderer│  │ CodePreviewer     │    ││              │
│  │  │ (CodeMirror)│  │ (react-live预览)   │    ││              │
│  │  └─────────────┘  └───────────────────┘    ││              │
│  └─────────────────────────────────────────────┘│              │
└──────────────────────────────────────────────────┼──────────────┘
                                                   │ Streaming
                                                   ▼
┌─────────────────────────────────────────────────────────────────┐
│                    后端 (LangGraph Server)                       │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                  open-canvas Graph                       │   │
│  │                                                          │   │
│  │   START → generatePath → ┬→ generateArtifact            │   │
│  │                          ├→ rewriteArtifact             │   │
│  │                          ├→ updateArtifact              │   │
│  │                          ├→ updateHighlightedText       │   │
│  │                          ├→ customAction                │   │
│  │                          └→ replyToGeneralInput         │   │
│  │                                      │                   │   │
│  │                                      ▼                   │   │
│  │                          generateFollowup → reflect      │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. 用户输入处理

### 2.1 前端消息初始化

当用户在 Composer 组件中输入文本并提交时：

**文件**: `apps/web/src/contexts/GraphContext.tsx`

```typescript
const handleSubmit = async (content: string) => {
  // 1. 创建 HumanMessage 对象
  const humanMessage = new HumanMessage({
    content,
    id: uuidv4(),
  });

  // 2. 添加到消息列表
  setMessages((prevMessages) => [...prevMessages, humanMessage]);

  // 3. 发起流式请求
  await streamMessage({
    messages: [convertToOpenAIFormat(humanMessage)],
    // 如果有高亮选中，附加高亮信息
    ...(selectionIndexes && {
      highlightedCode: {
        startCharIndex: selectionIndexes.start,
        endCharIndex: selectionIndexes.end,
      }
    }),
  });
};
```

### 2.2 GraphInput 数据结构

**文件**: `packages/shared/src/types.ts`

```typescript
export interface GraphInput {
  messages?: Record<string, any>[];      // 消息列表
  highlightedCode?: CodeHighlight;       // 代码高亮信息
  highlightedText?: TextHighlight;       // 文本高亮信息
  artifact?: ArtifactV3;                 // 当前 artifact
  language?: LanguageOptions;            // 快速操作：语言
  artifactLength?: ArtifactLengthOptions;// 快速操作：长度
  customQuickActionId?: string;          // 自定义快捷操作 ID
  webSearchEnabled?: boolean;            // 是否启用网络搜索
  // ... 更多参数
}
```

### 2.3 Web Worker 流传输

前端通过 Web Worker 处理流式响应，避免阻塞主线程：

**文件**: `apps/web/src/workers/graph-stream/streamWorker.ts`

```typescript
const workerService = new StreamWorkerService();
const stream = workerService.streamData({
  threadId: currentThreadId,
  assistantId: assistantsData.selectedAssistant.assistant_id,
  input,
  modelName: threadData.modelName,
});

// 处理每个流式 chunk
for await (const chunk of stream) {
  const { event, langgraphNode, nodeChunk } = extractChunkFields(chunk);

  if (event === "on_chat_model_stream") {
    if (langgraphNode === "generateArtifact") {
      // 累积并解析 artifact 工具调用 JSON
      generateArtifactToolCallStr += message?.tool_call_chunks?.[0]?.args;
      const result = handleGenerateArtifactToolCallChunk(generateArtifactToolCallStr);
      if (result) setArtifact(result);
    }
  }
}
```

---

## 3. Agent 路由决策

### 3.1 generatePath 节点

**文件**: `apps/agents/src/open-canvas/nodes/generate-path/index.ts`

`generatePath` 是 LangGraph 的核心路由节点，根据输入状态决定下一步执行哪个节点：

```typescript
export async function generatePath(
  state: typeof OpenCanvasGraphAnnotation.State,
  config: LangGraphRunnableConfig
): Promise<OpenCanvasGraphReturnType> {

  // 优先级 1: 代码高亮修改
  if (state.highlightedCode) {
    return { next: "updateArtifact" };
  }

  // 优先级 2: 文本高亮修改
  if (state.highlightedText) {
    return { next: "updateHighlightedText" };
  }

  // 优先级 3: 快速操作（语言、长度等）
  if (state.language || state.artifactLength || state.regenerateWithEmojis) {
    return { next: "rewriteArtifactTheme" };
  }

  // 优先级 4: 代码快速操作（添加注释、修复 bug 等）
  if (state.addComments || state.addLogs || state.fixBugs) {
    return { next: "rewriteCodeArtifactTheme" };
  }

  // 优先级 5: 自定义快捷操作
  if (state.customQuickActionId) {
    return { next: "customAction" };
  }

  // 优先级 6: 网络搜索
  if (state.webSearchEnabled) {
    return { next: "webSearch" };
  }

  // 默认: 动态决策（生成新 artifact 还是重写现有）
  const route = await dynamicDeterminePath(state, config);
  return { next: route };
}
```

### 3.2 动态路由决策

**文件**: `apps/agents/src/open-canvas/nodes/generate-path/dynamic-determine-path.ts`

当没有明确的状态标志时，通过 LLM 判断用户意图：

```typescript
const dynamicDeterminePath = async (state, config) => {
  const currentArtifactContent = state.artifact
    ? getArtifactContent(state.artifact)
    : undefined;

  // 如果不存在 artifact，生成新的
  if (!currentArtifactContent) {
    return "generateArtifact";
  }

  // 存在 artifact，让 LLM 判断是重写还是回复
  const route = await routeModel.invoke([
    { role: "system", content: ROUTE_PROMPT },
    { role: "user", content: state._messages.slice(-1)[0].content }
  ]);

  return route; // "rewriteArtifact" 或 "replyToGeneralInput"
};
```

---

## 4. Artifact 生成流程

### 4.1 generateArtifact 节点

**文件**: `apps/agents/src/open-canvas/nodes/generate-artifact/index.ts`

```typescript
export const generateArtifact = async (state, config) => {
  // 1. 获取模型并绑定 artifact 生成工具
  const modelWithArtifactTool = smallModel.bindTools([
    {
      name: "generate_artifact",
      schema: ARTIFACT_TOOL_SCHEMA,
    }
  ]);

  // 2. 构建系统 prompt（包含用户 memories/风格规则）
  const formattedPrompt = formatNewArtifactPrompt(memoriesAsString, modelName);

  // 3. 调用 LLM
  const response = await modelWithArtifactTool.invoke([
    { role: "system", content: fullSystemPrompt },
    ...contextDocumentMessages,
    ...state._messages,
  ]);

  // 4. 提取工具调用结果
  const args = response.tool_calls?.[0].args;

  // 5. 创建 artifact 内容对象
  const newArtifactContent = createArtifactContent(args);

  // 6. 返回新 artifact
  return {
    artifact: {
      currentIndex: 1,
      contents: [newArtifactContent],
    },
  };
};
```

### 4.2 Artifact 工具 Schema

**文件**: `apps/agents/src/open-canvas/nodes/generate-artifact/schemas.ts`

```typescript
export const ARTIFACT_TOOL_SCHEMA = z.object({
  type: z.enum(["code", "text"]),
  language: z.enum([
    "typescript", "javascript", "jsx", "tsx",
    "python", "java", "cpp", "html", "css", "json"
  ]).optional(),
  isValidReact: z.boolean().optional(),  // React 代码标记
  artifact: z.string(),                   // 实际内容
  title: z.string(),
});
```

### 4.3 Artifact 内容创建

**文件**: `apps/agents/src/open-canvas/nodes/generate-artifact/utils.ts`

```typescript
export const createArtifactContent = (toolCall) => {
  if (toolCall.type === "code") {
    return {
      index: 1,
      type: "code",
      title: toolCall.title,
      code: toolCall.artifact,
      language: toolCall.language,
      isValidReact: toolCall.isValidReact,  // 决定是否显示预览
    };
  }

  return {
    index: 1,
    type: "text",
    title: toolCall.title,
    fullMarkdown: toolCall.artifact,
  };
};
```

---

## 5. 前端渲染机制

### 5.1 ArtifactRenderer 组件

**文件**: `apps/web/src/components/artifacts/ArtifactRenderer.tsx`

```typescript
function ArtifactRendererComponent(props) {
  const { graphData } = useGraphContext();
  const { artifact, isStreaming } = graphData;

  const currentArtifactContent = artifact
    ? getArtifactContent(artifact)  // 根据 currentIndex 获取当前版本
    : undefined;

  if (!artifact || !currentArtifactContent) {
    return <div className="w-full h-full" />;
  }

  return (
    <div className="relative w-full h-full">
      <ArtifactHeader {...} />
      <div>
        {/* 条件渲染：文本或代码 */}
        {currentArtifactContent.type === "text" && (
          <TextRenderer {...} />
        )}
        {currentArtifactContent.type === "code" && (
          <CodeRenderer {...} />
        )}
      </div>
    </div>
  );
}
```

### 5.2 CodeRenderer 组件

**文件**: `apps/web/src/components/artifacts/CodeRenderer.tsx`

```typescript
function CodeRendererComponent(props) {
  const { artifact, isStreaming } = graphData;
  const [isCodePreviewVisible, setIsCodePreviewVisible] = useState(false);

  const artifactContent = getArtifactContent(artifact);
  const extensions = [getLanguageExtension(artifactContent.language)];

  return (
    <motion.div className="flex flex-row w-full">
      {/* 左侧: CodeMirror 编辑器 */}
      <motion.div animate={{ flex: isCodePreviewVisible ? 0.5 : 1 }}>
        {/* 预览切换按钮（仅 React 代码显示） */}
        {props.isHovering && (
          <ToggleCodePreview
            isCodePreviewVisible={isCodePreviewVisible}
            codePreviewDisabled={!artifactContent.isValidReact}
            setIsCodePreviewVisible={setIsCodePreviewVisible}
          />
        )}

        <CodeMirror
          value={cleanContent(artifactContent.code)}
          extensions={extensions}
          onChange={(c) => setArtifactContent(artifactContent.index, c)}
        />
      </motion.div>

      {/* 右侧: React 代码预览（仅 isValidReact 时显示） */}
      {!isStreaming && artifactContent.isValidReact && (
        <CodePreviewer
          artifact={artifactContent}
          isExpanded={isCodePreviewVisible}
        />
      )}
    </motion.div>
  );
}
```

### 5.3 CodePreviewer 组件 (React Live 预览)

**文件**: `apps/web/src/components/artifacts/CodePreviewer.tsx`

```typescript
export function CodePreviewer({ isExpanded, artifact }) {
  const cleanedCode = getPreviewCode(artifact.code);

  return (
    <motion.div
      animate={{
        flex: isExpanded ? 0.5 : 0,
        opacity: isExpanded ? 1 : 0,
      }}
      className="border-l border-gray-200 h-screen"
    >
      {isExpanded && (
        <LiveProvider noInline code={cleanedCode}>
          <LivePreview />  {/* 实时渲染 React 组件 */}
          <LiveError />    {/* 显示运行时错误 */}
        </LiveProvider>
      )}
    </motion.div>
  );
}
```

**react-live 工作原理**:
- `LiveProvider`: 创建代码执行沙箱环境
- `LivePreview`: 实时编译并渲染 React 组件
- `LiveError`: 捕获并显示编译/运行时错误

---

## 6. 代码修改机制

### 6.1 三种修改模式对比

| 模式 | 触发条件 | 修改范围 | 适用场景 |
|------|----------|----------|----------|
| `rewriteArtifact` | 常规对话 | 整个 artifact | 大幅修改、重构 |
| `updateArtifact` | 代码高亮 | 高亮部分 | 局部代码修改 |
| `updateHighlightedText` | 文本高亮 | 高亮所在块 | 局部文本修改 |

### 6.2 rewriteArtifact（整体重写）

**文件**: `apps/agents/src/open-canvas/nodes/rewrite-artifact/index.ts`

```typescript
export const rewriteArtifact = async (state, config) => {
  // 1. 获取当前 artifact 内容
  const currentArtifactContent = getArtifactContent(state.artifact);

  // 2. 可选：更新元数据（类型、标题、语言）
  const artifactMetaToolCall = await optionallyUpdateArtifactMeta(state, config);

  // 3. 构建 prompt（包含当前内容 + memories）
  const formattedPrompt = buildPrompt({
    artifactContent: currentArtifactContent,
    memoriesAsString,
  });

  // 4. 调用 LLM 生成新内容
  const response = await model.invoke([
    { role: "system", content: fullSystemPrompt },
    ...state._messages,
  ]);

  // 5. 创建新版本（追加到 contents 数组）
  const newArtifactContent = {
    ...currentArtifactContent,
    index: state.artifact.contents.length + 1,
    code: response.content,  // 或 fullMarkdown
  };

  return {
    artifact: {
      ...state.artifact,
      currentIndex: state.artifact.contents.length + 1,
      contents: [...state.artifact.contents, newArtifactContent],
    },
  };
};
```

### 6.3 updateArtifact（高亮代码修改）

**文件**: `apps/agents/src/open-canvas/nodes/updateArtifact.ts`

```typescript
export const updateArtifact = async (state, config) => {
  const { highlightedCode } = state;
  const { startCharIndex, endCharIndex } = highlightedCode;
  const code = currentArtifactContent.code;

  // 1. 提取上下文（高亮 + 前后 500 字符）
  const beforeHighlight = code.slice(
    Math.max(0, startCharIndex - 500),
    startCharIndex
  );
  const highlightedText = code.slice(startCharIndex, endCharIndex);
  const afterHighlight = code.slice(
    endCharIndex,
    Math.min(code.length, endCharIndex + 500)
  );

  // 2. 构建 prompt（只修改高亮部分）
  const formattedPrompt = UPDATE_HIGHLIGHTED_ARTIFACT_PROMPT
    .replace("{highlightedText}", highlightedText)
    .replace("{beforeHighlight}", beforeHighlight)
    .replace("{afterHighlight}", afterHighlight);

  // 3. 调用 LLM
  const updatedCode = await model.invoke([
    { role: "system", content: formattedPrompt },
    recentHumanMessage,
  ]);

  // 4. 拼接：前部分 + LLM 输出 + 后部分
  const entireTextBefore = code.slice(0, startCharIndex);
  const entireTextAfter = code.slice(endCharIndex);
  const entireUpdatedContent = `${entireTextBefore}${updatedCode}${entireTextAfter}`;

  // 5. 创建新版本
  return {
    artifact: {
      ...state.artifact,
      currentIndex: state.artifact.contents.length + 1,
      contents: [...state.artifact.contents, {
        ...currentArtifactContent,
        index: state.artifact.contents.length + 1,
        code: entireUpdatedContent,
      }],
    },
  };
};
```

### 6.4 customAction（自定义快捷操作）

**文件**: `apps/agents/src/open-canvas/nodes/customAction.ts`

```typescript
export const customAction = async (state, config) => {
  // 1. 从 store 获取自定义操作定义
  const customQuickAction = store.get(
    ["custom_actions", userId],
    state.customQuickActionId
  );

  // 2. 构建 prompt
  let formattedPrompt = `<custom-instructions>
${customQuickAction.prompt}
</custom-instructions>`;

  // 3. 条件追加上下文
  if (customQuickAction.includeReflections) {
    formattedPrompt += formatReflectionsIntoPrompt(memories);
  }
  if (customQuickAction.includeRecentHistory) {
    formattedPrompt += formatConversationHistory(state._messages.slice(-5));
  }

  // 4. 追加当前 artifact 内容
  formattedPrompt += `\n\nArtifact content:\n${artifactContent}`;

  // 5. 调用 LLM 并创建新版本
  const response = await model.invoke([
    { role: "user", content: formattedPrompt }
  ]);

  return {
    artifact: {
      ...state.artifact,
      currentIndex: state.artifact.contents.length + 1,
      contents: [...state.artifact.contents, newArtifactContent],
    },
  };
};
```

---

## 7. 版本管理系统

### 7.1 ArtifactV3 数据结构

**文件**: `packages/shared/src/types.ts`

```typescript
// Artifact 容器
export interface ArtifactV3 {
  currentIndex: number;                              // 当前显示的版本号
  contents: (ArtifactMarkdownV3 | ArtifactCodeV3)[]; // 所有版本历史
}

// 代码 Artifact 版本
export interface ArtifactCodeV3 {
  index: number;                        // 版本号 (1, 2, 3...)
  type: "code";
  title: string;
  language: ProgrammingLanguageOptions;
  code: string;
  isValidReact?: boolean;               // 是否可预览
}

// Markdown Artifact 版本
export interface ArtifactMarkdownV3 {
  index: number;
  type: "text";
  title: string;
  fullMarkdown: string;
}
```

### 7.2 版本追踪示例

```
初始创建:
{
  currentIndex: 1,
  contents: [
    { index: 1, code: "console.log('v1')" }
  ]
}

第一次修改:
{
  currentIndex: 2,
  contents: [
    { index: 1, code: "console.log('v1')" },
    { index: 2, code: "console.log('v2')" }
  ]
}

第二次修改:
{
  currentIndex: 3,
  contents: [
    { index: 1, code: "console.log('v1')" },
    { index: 2, code: "console.log('v2')" },
    { index: 3, code: "console.log('v3')" }
  ]
}
```

### 7.3 版本切换

**文件**: `apps/web/src/contexts/GraphContext.tsx`

```typescript
const setSelectedArtifact = (index: number) => {
  setArtifact((prev) => {
    if (!prev) return prev;
    return {
      ...prev,
      currentIndex: index,  // 只改变指针，不改变内容
    };
  });
};
```

**UI 导航**: `apps/web/src/components/artifacts/header/navigate-artifact-history.tsx`

```
[←] 2/5 [→]
```

---

## 8. 关键文件映射

| 功能模块 | 文件路径 |
|----------|----------|
| **前端状态管理** | `apps/web/src/contexts/GraphContext.tsx` |
| **Web Worker** | `apps/web/src/workers/graph-stream/streamWorker.ts` |
| **Agent 图定义** | `apps/agents/src/open-canvas/index.ts` |
| **路由决策** | `apps/agents/src/open-canvas/nodes/generate-path/index.ts` |
| **生成 Artifact** | `apps/agents/src/open-canvas/nodes/generate-artifact/index.ts` |
| **重写 Artifact** | `apps/agents/src/open-canvas/nodes/rewrite-artifact/index.ts` |
| **更新高亮代码** | `apps/agents/src/open-canvas/nodes/updateArtifact.ts` |
| **更新高亮文本** | `apps/agents/src/open-canvas/nodes/updateHighlightedText.ts` |
| **自定义操作** | `apps/agents/src/open-canvas/nodes/customAction.ts` |
| **Artifact 渲染** | `apps/web/src/components/artifacts/ArtifactRenderer.tsx` |
| **代码编辑器** | `apps/web/src/components/artifacts/CodeRenderer.tsx` |
| **React 预览** | `apps/web/src/components/artifacts/CodePreviewer.tsx` |
| **类型定义** | `packages/shared/src/types.ts` |
| **Prompt 模板** | `apps/agents/src/open-canvas/prompts.ts` |

---

## 完整时序图

```
用户输入 "创建一个 React 计数器组件"
         │
         ▼
┌─────────────────────────────────────┐
│  前端: ContentComposer              │
│  → 创建 HumanMessage                │
│  → 调用 streamMessage(GraphInput)   │
└─────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│  前端: StreamWorkerService          │
│  → Web Worker 发起流式请求          │
└─────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│  后端: generatePath                 │
│  → 无 artifact → generateArtifact   │
└─────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│  后端: generateArtifact             │
│  → 绑定 artifact 工具               │
│  → 调用 LLM                         │
│  → 返回 ArtifactV3                  │
│    { currentIndex: 1,               │
│      contents: [{ type: "code",     │
│        code: "...", isValidReact }] │
│    }                                │
└─────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│  后端: generateFollowup             │
│  → 生成后续响应消息                  │
└─────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│  前端: 处理 streaming chunks        │
│  → 累积 JSON                        │
│  → setArtifact(result)              │
└─────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│  前端: ArtifactRenderer             │
│  → type === "code"                  │
│  → CodeRenderer (CodeMirror)        │
│  → isValidReact → CodePreviewer     │
│    → react-live 实时渲染            │
└─────────────────────────────────────┘
```

---

## 总结

Open Canvas 的 React App Artifact 系统具有以下核心特点：

1. **流式生成**: 通过 Web Worker + Streaming 实现实时响应
2. **智能路由**: generatePath 节点根据状态自动选择处理路径
3. **版本控制**: ArtifactV3 的 contents 数组保留完整历史
4. **精准修改**: 支持整体重写和局部高亮修改两种模式
5. **实时预览**: react-live 提供 React 代码的即时渲染

---

*文档生成时间: 2025-12-15*
*项目版本: main 分支*
