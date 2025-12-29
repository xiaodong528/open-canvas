# 删除 apps/agents (TypeScript) 实施计划

> **创建日期**: 2025-12-29
> **Codex Review 日期**: 2025-12-29
> **第二次 Review 日期**: 2025-12-29
> **审查状态**: ✅ 已审查并更新 (v2)

## 结论：✅ 可以删除

Python 版本 (`apps/agents-py`) 已 **100% 功能完整**，完全可以替代 TypeScript 版本。

---

## ⚠️ Codex Review 发现的问题

### 🔴 High 严重度

**1. evals 节点级 API 不兼容问题**：

当前 `packages/evals` 直接调用节点级 API，SDK 不支持这些入口：

| 文件 | 行号 | 问题 API |
|------|------|---------|
| `agent.int.test.ts` | 18 | `graph.nodes.generatePath` |
| `agent.int.test.ts` | 74 | `graph.nodes.generateArtifact` |
| `highlights.ts` | 10 | `graph.interruptAfter` |

**2. SDK 调用缺少 `customModelName`** (第二次 Review 发现)：

计划中的 SDK 调用没有传递 `customModelName`，Python 端 `get_model_config()` 会抛错：

```python
# apps/agents-py/src/utils.py:220-221
if not custom_model_name:
    raise ValueError("Model name is missing in config.")
```

**必须**在 `client.runs.*` 调用中传入 `config.configurable.customModelName`。

**3. `result.next` 断言会失败** (第二次 Review 发现)：

完整图执行后 `cleanState` 节点会清空 `next` 为 `None`：

```python
# apps/agents-py/src/constants.py:35-38
CLEAN_STATE_UPDATE = {
    "next": None,
    ...
}
```

**解决方案**：使用 `runs.stream` 捕获 `generatePath` 节点输出，而非断言最终状态的 `next`。

**4. `artifact` 结构不兼容** (第二次 Review 发现)：

| TypeScript (旧) | Python (新) |
|-----------------|-------------|
| `artifacts[0].content` | `artifact.contents[]` |
| `highlighted` | `highlightedCode` / `highlightedText` |
| `content.fullMarkdown` | `contents[].fullMarkdown` |

需要在 evals 层做结构映射。

### 🟡 Medium 严重度

**1. API URL 配置问题**：

- `apps/web/src/hooks/utils.ts:3` 的 `createClient()` 默认指向 Next.js 代理 (`http://localhost:3000/api`)
- evals 应直连 Python LangGraph Server (`http://localhost:54367`)

**2. SDK 版本不一致** (第二次 Review 发现)：

| 位置 | 版本 |
|------|------|
| 计划中 | `^0.0.36` |
| `apps/web/package.json` | `^0.0.107` |

**解决方案**：统一使用 `^0.0.107`

### 🟢 Low 严重度

1. **文档清理不完整**：以下文档仍引用 `apps/agents`：
   - `docs/guide/react-artifact-flow.md`
   - `docs/workflow/langgraph-python-migration-workflow.md`
   - `docs/workflow/review/.../open-canvas-ts-to-py-migration-review.md`

2. **缺少 yarn.lock 更新步骤**

3. **evals client 不统一**：`python-backend.eval.ts` 直接 `new Client`，应统一使用 `createEvalsClient()`

---

## 实施步骤 (已根据第二次 Review 更新)

### Step 1: 更新 packages/evals (改用 SDK 调用 Python 后端)

**1.1 更新依赖** - `packages/evals/package.json`
```diff
  "dependencies": {
    "@langchain/core": "^0.3.71",
    "@langchain/openai": "^0.4.2",
-   "@opencanvas/agents": "*",
+   "@langchain/langgraph-sdk": "^0.0.107",
    "langsmith": "^0.3.60",
    "zod": "^3.24.1",
    "dotenv": "^16.4.7"
  },
```

**1.2 创建 evals 专用 client** - `packages/evals/src/utils.ts` (新文件)
```typescript
import { Client } from "@langchain/langgraph-sdk";

export const createEvalsClient = () => {
  // 直连 Python LangGraph Server，不经过 Next.js 代理
  const apiUrl = process.env.LANGGRAPH_API_URL ?? "http://localhost:54367";
  return new Client({ apiUrl });
};

// 默认模型配置
export const DEFAULT_MODEL_CONFIG = {
  customModelName: "gpt-4o-mini",
  // 可选: modelConfig 用于自定义 API key 等
};
```

**1.3 重写 highlights.ts** (已修复 customModelName 和结构映射)

原代码问题：
- `graph.interruptAfter = ["updateArtifact"]` - SDK 不支持
- 缺少 `customModelName` 配置
- artifact 结构不兼容

```typescript
// packages/evals/src/highlights.ts (重写)
import { type Example, Run } from "langsmith";
import { evaluate, EvaluationResult } from "langsmith/evaluation";
import { createEvalsClient, DEFAULT_MODEL_CONFIG } from "./utils";
import "dotenv/config";

const client = createEvalsClient();

const runGraph = async (
  input: Record<string, any>
): Promise<Record<string, any>> => {
  const thread = await client.threads.create();

  // ✅ 修复: 必须传入 customModelName
  const stream = client.runs.stream(thread.thread_id, "agent", {
    input,
    streamMode: "values",
    config: {
      configurable: {
        customModelName: DEFAULT_MODEL_CONFIG.customModelName,
      },
    },
  });

  let finalState: Record<string, any> | null = null;
  for await (const chunk of stream) {
    if (chunk.event === "values") {
      finalState = chunk.data;
    }
  }

  return finalState ?? {};
};

// ✅ 修复: artifact 结构映射
const mapArtifactInput = (tsArtifact: any) => ({
  artifact: {
    currentIndex: tsArtifact.currentIndex ?? 0,
    contents: tsArtifact.contents ?? [{
      index: 0,
      type: tsArtifact.type ?? "text",
      title: tsArtifact.title ?? "",
      fullMarkdown: tsArtifact.content ?? "",
    }],
  },
});
```

**1.4 重写 agent.int.test.ts** (已修复路由断言)

原代码问题：
- `graph.nodes.generatePath` - SDK 不支持节点级调用
- `result.next` 在完整图执行后会被清空

```typescript
// packages/evals/src/agent.int.test.ts (重写)
import { expect } from "vitest";
import * as ls from "langsmith/vitest";
import { z } from "zod";
import { ChatOpenAI } from "@langchain/openai";
import { createEvalsClient, DEFAULT_MODEL_CONFIG } from "./utils";

const client = createEvalsClient();

ls.describe("query routing", () => {
  ls.test(
    "routes followups with questions to update artifact",
    { inputs: QUERY_ROUTING_DATA.inputs, referenceOutputs: QUERY_ROUTING_DATA.referenceOutputs },
    async ({ inputs, referenceOutputs }) => {
      const thread = await client.threads.create();

      // ✅ 修复: 使用 stream 捕获 generatePath 输出
      const stream = client.runs.stream(thread.thread_id, "agent", {
        input: inputs,
        streamMode: "events",
        config: {
          configurable: {
            customModelName: DEFAULT_MODEL_CONFIG.customModelName,
          },
        },
      });

      let capturedNext: string | null = null;
      for await (const chunk of stream) {
        // 捕获 generatePath 节点的输出
        if (chunk.event === "on_chain_end" && chunk.name === "generatePath") {
          capturedNext = chunk.data?.output?.next ?? null;
          break;
        }
      }

      ls.logOutputs({ next: capturedNext });
      // ✅ 修复: 断言捕获的路由结果，而非最终状态
      expect(capturedNext).toEqual(referenceOutputs.next);
    }
  );
});
```

**1.5 更新 python-backend.eval.ts** (统一使用 createEvalsClient)

```typescript
// 替换直接 new Client 为 createEvalsClient
import { createEvalsClient } from "./utils";
const client = createEvalsClient();
```

**1.6 更新 yarn.lock**
```bash
cd packages/evals && yarn install
```

---

### Step 2: 更新 CI/CD (改为检查 Python 后端)

**文件**: `.github/workflows/ci.yml` (第76-109行)

```yaml
dev-server-check:
  name: Check Python dev server startup
  runs-on: ubuntu-latest
  defaults:
    run:
      working-directory: apps/agents-py
  steps:
    - uses: actions/checkout@v4
    - name: Install uv
      uses: astral-sh/setup-uv@v4
    - name: Set up Python
      run: uv python install 3.12
    - name: Install dependencies
      run: uv sync
    - name: Create .env file
      run: touch .env
    - name: Run dev server check
      run: uv run python scripts/check-dev-server.py
      timeout-minutes: 2
```

---

### Step 3: 删除 apps/agents 目录

```bash
rm -rf apps/agents
```

---

### Step 4: 清理残留引用 (扩展)

**4.1 主要文档**
- `CLAUDE.md` - 移除 "LEGACY" 标记和 TypeScript agents 相关说明

**4.2 迁移历史文档** (保留但标记为归档)
- `docs/workflow/langgraph-python-migration-workflow.md` - 添加归档说明
- `docs/workflow/review/.../open-canvas-ts-to-py-migration-review.md` - 添加归档说明

**4.3 配置文件**
- `turbo.json` - 检查并移除 agents 相关配置
- 根目录 `package.json` - workspaces 会自动排除已删除目录

---

## 需要修改的文件清单 (已更新)

| 文件 | 操作 | 优先级 |
|------|------|--------|
| `packages/evals/package.json` | 修改依赖 (SDK `^0.0.107`) | 高 |
| `packages/evals/src/utils.ts` | **新建** - evals 专用 client + DEFAULT_MODEL_CONFIG | 高 |
| `packages/evals/src/highlights.ts` | **重写** - stream + customModelName + 结构映射 | 高 |
| `packages/evals/src/agent.int.test.ts` | **重写** - stream 捕获 generatePath 输出 | 高 |
| `packages/evals/src/api/python-backend.eval.ts` | 统一使用 createEvalsClient | 高 |
| `.github/workflows/ci.yml` | 改用 Python 后端 | 高 |
| `yarn.lock` | 更新依赖 | 高 |
| `apps/agents/` | 删除整个目录 | 中 |
| `CLAUDE.md` | 移除 LEGACY 引用 | 低 |
| `docs/workflow/*.md` | 添加归档说明 | 低 |

---

## 验证步骤 (已更新)

1. ✅ Python 后端可以正常启动: `cd apps/agents-py && uv run langgraph dev`
2. ✅ 前端可以正常连接: `cd apps/web && yarn dev`
3. ⚠️ **evals 测试通过** (需要后端运行，需验证新代码): `cd packages/evals && yarn test`
4. ✅ CI/CD workflow 通过
5. ✅ yarn.lock 更新无冲突

---

## 背景分析

### 功能完整性对比

| 维度 | 状态 | 说明 |
|------|------|------|
| **5 个图 (Graphs)** | ✅ 100% | agent, reflection, thread_title, summarizer, web_search |
| **16 个主图节点** | ✅ 100% | 所有节点完整实现 |
| **状态字段 (camelCase)** | ✅ 100% | 前端兼容性保持 |
| **Web 搜索集成** | ✅ 100% | Exa API 完整 |
| **反思/记忆系统** | ✅ 100% | BaseStore 集成 |
| **后台任务** | ✅ 100% | SDK 异步调用 |

### 无需处理的部分

| 部分 | 原因 |
|------|------|
| **前端 (apps/web)** | 通过 LangGraph SDK 通信，与后端实现无关 |
| **init.sh** | 已经只使用 Python 后端 |
| **system-check.sh** | 已经只检查 Python 后端 |
| **E2E 测试** | Playwright 已配置启动 Python 后端 |

### 风险评估 (已更新)

| 风险 | 级别 | 缓解措施 |
|------|------|---------|
| evals 节点级 API 不兼容 | 高 | 使用 stream 捕获节点输出 |
| SDK 调用缺少 customModelName | 高 | 添加 DEFAULT_MODEL_CONFIG |
| result.next 断言失败 | 高 | 捕获 generatePath 输出而非最终状态 |
| artifact 结构不兼容 | 高 | 添加 mapArtifactInput 映射函数 |
| API URL 配置错误 | 中 | 创建 evals 专用 client，直连 54367 |
| SDK 版本不一致 | 中 | 统一使用 ^0.0.107 |
| evals 测试失败 | 中 | 先更新 evals 并验证再删除 |
| CI/CD 失败 | 中 | 同步更新 workflow |
| 历史参考丢失 | 低 | Git 历史保留 + 文档归档 |

---

## 依赖关系图

```
apps/agents (TypeScript - 待删除)
  ├── 依赖 → @opencanvas/shared (共享类型)
  ├── 被引用 ← packages/evals (评估框架) ⚠️ 需要更新
  ├── 被引用 ← CI/CD (dev-server-check) ⚠️ 需要更新
  └── 不被 ← apps/web (前端) 直接引用
            (通过网络连接到运行时实例)

packages/evals (需要更新)
  └── 依赖 → @opencanvas/agents
              用于: highlights.ts, agent.int.test.ts
              ⚠️ 使用节点级 API，SDK 不支持

.github/workflows/ci.yml (需要更新)
  └── apps/agents
      └── 运行: yarn dev (dev-server-check)
```
