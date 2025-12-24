# Open Canvas TS → Python 迁移审查报告

**关键发现（按严重度）**
- ❌ rewriteArtifact 流式契约缺失：前端依赖 `taskName === "optionally_update_artifact_meta"` 与 `taskName === "rewrite_artifact_model_call"` 来更新元数据与流式内容，但 Python 版未设置对应 runName，导致重写工件可能无法在 UI 中更新。`apps/web/src/contexts/GraphContext.tsx:674` `apps/web/src/contexts/GraphContext.tsx:1184`；`apps/agents-py/src/open_canvas/nodes/rewrite_artifact.py:242` `apps/agents-py/src/open_canvas/nodes/rewrite_artifact.py:264`
- ❌ TEMPERATURE_EXCLUDED_MODELS 不一致：Python 仅含 o1/o3-mini，缺少 shared 中的 gpt-5* 与 o4-mini，可能对这些模型错误传递 temperature/max_tokens 导致 API 报错或行为偏差。`apps/agents-py/src/constants.py:56` `packages/shared/src/models.ts:695`
- ⚠️ 动态路由输入不等价：Python 动态路由未注入上下文文档消息/新文档消息，TS 版本会注入，可能影响是否走 generateArtifact/rewriteArtifact 的决策。`apps/agents-py/src/open_canvas/nodes/generate_path.py:450` `apps/agents/src/open-canvas/nodes/generate-path/dynamic-determine-path.ts:90`
- ⚠️ 文档消息修复行为差异：TS 用 `newMessages.find` 导致旧格式文档修复几乎不触发；Python 用内部消息查找会触发修复，行为不一致。`apps/agents/src/open-canvas/nodes/generate-path/index.ts:30` `apps/agents-py/src/open_canvas/nodes/generate_path.py:556`
- ⚠️ 反思输出字段与需求描述不一致：代码使用 `content`，需求写 `userFacts`；前端也使用 `content`，建议更新需求或加兼容字段。`packages/shared/src/types.ts:163` `apps/agents-py/src/types.py:179`
- ⚠️ 关键节点未见统一异常兜底，异常仍会中断流并触发 error 事件；与“不中断 stream”的要求不一致。`apps/agents-py/src/open_canvas/nodes/rewrite_artifact.py:239` `apps/agents-py/src/open_canvas/nodes/generate_path.py:520`

**开放问题/假设**
- 未做实际流式运行验证，`taskName` 事件是否确实缺失需以运行日志确认。
- 未验证 Exa Python SDK 返回字段名是否为 `publishedDate`（非 `published_date`）；如不匹配会导致元数据为空。

## 审查结果摘要
- ✅ 通过项数量：27
- ⚠️ 警告项数量：5
- ❌ 失败项数量：2

## 详细发现

### 1. langgraph.json 配置对比
| 检查项 | 状态 | 说明 |
|-------|------|------|
| 5 个图定义一致 | ✅ | 两端均包含 agent/reflection/thread_title/summarizer/web_search。`langgraph.json` `apps/agents-py/langgraph.json` |
| 导出路径与入口点正确 | ✅ | TS 指向 `apps/agents/src/...`，Py 指向 `src.*.graph:graph` |
| 环境变量引用正确 | ✅ | TS 用根 `.env`，Py 用 `../../.env` 指向根目录 |

### 2. GraphInput/State 类型一致性
| 检查项 | 状态 | 说明 |
|-------|------|------|
| 字段名 camelCase | ✅ | Python TypedDict 均为 camelCase。`apps/agents-py/src/types.py:1` |
| ArtifactV3 结构一致 | ✅ | `currentIndex` + `contents[]` 一致。`packages/shared/src/types.ts:124` `apps/agents-py/src/types.py:63` |
| CodeHighlight/TextHighlight 一致 | ✅ | 字段结构匹配。`packages/shared/src/types.ts:103` `apps/agents-py/src/types.py:33` |
| SearchResult 嵌套一致 | ✅ | `pageContent` + `metadata`。`packages/shared/src/types.ts:207` `apps/agents-py/src/types.py:205` |
| 枚举值一致 | ✅ | ProgrammingLanguageOptions/LanguageOptions 对齐。`packages/shared/src/types.ts:73` `apps/agents-py/src/types.py:17` |

### 3. 节点名称一致性（关键）
| 检查项 | 状态 | 说明 |
|-------|------|------|
| 主图节点名称匹配 | ✅ | generatePath/generateArtifact/.../customAction 均存在。`apps/agents-py/src/open_canvas/graph.py:262` |
| web_search 子图节点匹配 | ✅ | queryGenerator/search 均存在。`apps/agents-py/src/web_search/graph.py:29` |

### 4. 消息格式一致性
| 检查项 | 状态 | 说明 |
|-------|------|------|
| add_messages reducer 行为 | ✅ | 使用 add_messages。`apps/agents-py/src/open_canvas/state.py:74` |
| _messages_reducer 摘要处理 | ✅ | OC_SUMMARIZED_MESSAGE_KEY 清空逻辑一致。`apps/agents-py/src/open_canvas/state.py:29` `apps/agents/src/open-canvas/state.ts:26` |
| additional_kwargs 传递 | ✅ | webSearchResults/webSearchStatus 已写入。`apps/agents-py/src/utils.py:507` |
| rewriteArtifact 流式 taskName 契约 | ❌ | 前端依赖 taskName，Python 未设置 runName。`apps/web/src/contexts/GraphContext.tsx:674` `apps/agents-py/src/open_canvas/nodes/rewrite_artifact.py:242` |

### 5. 常量一致性
| 检查项 | 状态 | 说明 |
|-------|------|------|
| OC_* 常量一致 | ✅ | 三个 key 一致。`packages/shared/src/constants.ts:3` `apps/agents-py/src/constants.py:12` |
| CHARACTER_MAX = 300000 | ✅ | 一致。`packages/shared/src/constants.ts` `apps/agents-py/src/constants.py:31` |
| CONTEXT_DOCUMENTS_NAMESPACE tuple | ✅ | Python 为 tuple。`apps/agents-py/src/constants.py:18` |
| DEFAULT_INPUTS 对齐 | ✅ | 字段集合一致。`packages/shared/src/constants.ts:9` `apps/agents-py/src/constants.py:33` |

### 6. 辅助图实现
| 检查项 | 状态 | 说明 |
|-------|------|------|
| reflection store namespace/key | ✅ | `("memories", assistant_id)` + `reflection`。`apps/agents-py/src/reflection/graph.py:73` |
| 反思输出字段 | ⚠️ | 代码是 `content`，需求写 `userFacts`。`packages/shared/src/types.ts:163` `apps/agents-py/src/types.py:179` |
| thread_title 更新 metadata | ✅ | 使用 SDK `metadata.thread_title`。`apps/agents-py/src/thread_title/graph.py:121` |
| summarizer 标记与更新 _messages | ✅ | OC_SUMMARIZED_MESSAGE_KEY + update_state。`apps/agents-py/src/summarizer/graph.py:78` |
| web_search 三节点结构 | ✅ | classifyMessage→queryGenerator→search。`apps/agents-py/src/web_search/graph.py:26` |

### 7. 路由逻辑一致性
| 检查项 | 状态 | 说明 |
|-------|------|------|
| 硬编码优先级顺序 | ✅ | 顺序一致。`apps/agents-py/src/open_canvas/nodes/generate_path.py:598` |
| 动态路由输入等价 | ⚠️ | Python 未注入 context docs/newMessages。`apps/agents-py/src/open_canvas/nodes/generate_path.py:510` `apps/agents/src/open-canvas/nodes/generate-path/dynamic-determine-path.ts:90` |
| webSearch 路由条件 | ✅ | `webSearchEnabled` 一致。`apps/agents-py/src/open_canvas/nodes/generate_path.py:620` |
| 工件存在性判断 | ✅ | `contents.length > 1` 一致。`apps/agents-py/src/open_canvas/graph.py:110` |
| 文档修复行为一致 | ⚠️ | Python 会修复，TS 目前几乎不触发。`apps/agents-py/src/open_canvas/nodes/generate_path.py:566` `apps/agents/src/open-canvas/nodes/generate-path/index.ts:36` |

### 8. 模型配置兼容性
| 检查项 | 状态 | 说明 |
|-------|------|------|
| provider 映射覆盖 | ✅ | openai/anthropic/fireworks/groq/gemini/azure/ollama 覆盖。`apps/agents-py/src/utils.py:170` |
| TEMPERATURE_EXCLUDED_MODELS 对齐 | ❌ | Python 列表缺 gpt-5* 与 o4-mini。`apps/agents-py/src/constants.py:56` `packages/shared/src/models.ts:695` |
| O1 System→Human 处理 | ✅ | o1-mini 处理一致。`apps/agents-py/src/utils.py:463` |
| 思考模型提取 | ✅ | extract_thinking_and_response 已用。`apps/agents-py/src/open_canvas/nodes/rewrite_artifact.py:317` |

### 9. 错误处理
| 检查项 | 状态 | 说明 |
|-------|------|------|
| 异常不中断 stream | ⚠️ | 关键节点仍抛异常，无统一兜底。`apps/agents-py/src/open_canvas/nodes/rewrite_artifact.py:249` |
| 错误格式与前端兼容 | ⚠️ | 依赖 LangGraph server 默认错误事件，未在 Python 侧统一格式 |

## 关键问题（必须修复）
1. rewriteArtifact 流式契约缺失 → 前端无法更新重写工件内容与元数据，UI 可能停滞或错误。建议：为可选元数据更新与主模型调用设置 runName，与前端一致；将 `_optionally_update_artifact_meta` 改为具名 runnable 或 `with_config({"run_name": "optionally_update_artifact_meta"})`；主模型调用加 `with_config({"run_name": "rewrite_artifact_model_call"})`。`apps/agents-py/src/open_canvas/nodes/rewrite_artifact.py:242` `apps/web/src/contexts/GraphContext.tsx:674`
2. TEMPERATURE_EXCLUDED_MODELS 不一致 → 选择 gpt-5/o4-mini 等模型时可能发送不受支持的 temperature/max_tokens。建议同步 `packages/shared/src/models.ts` 的列表到 Python 常量。`apps/agents-py/src/constants.py:56` `packages/shared/src/models.ts:695`

## 警告事项（建议修复）
1. 动态路由未注入 context docs/newMessages → 路由决策可能与 TS 不同，尤其在上传文档场景。建议按 TS 注入 `create_context_document_messages` 与 `newMessages`。`apps/agents-py/src/open_canvas/nodes/generate_path.py:510`
2. 旧格式文档修复行为不一致 → Python 会修复，TS 目前几乎不修复。建议统一策略（修正 TS 或保留 Python）。`apps/agents/src/open-canvas/nodes/generate-path/index.ts:36`
3. 反思输出字段命名与需求不一致 → 需求写 userFacts，实际为 content。建议修正文档或增加兼容字段。`packages/shared/src/types.ts:163`
4. 异常兜底不足 → 出错时 stream 可能中断。建议增加统一异常包装并返回前端可识别错误。`apps/agents-py/src/open_canvas/nodes/generate_path.py:520`

## 结论
当前 Python 后端在 **rewriteArtifact 流式契约** 和 **TEMPERATURE_EXCLUDED_MODELS** 上存在阻断性不一致，前端尚不能“无缝”切换。修复上述两项后，整体结构与 TS 版本基本对齐，切换风险将显著降低。  
测试缺口：未实际运行流式对话与重写工件场景；建议在修复后至少验证 rewriteArtifact、web_search、summarizer 三条链路的流式事件与 UI 更新。
