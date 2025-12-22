# Phase 5 控制流迁移审查（LangGraph Python）

审查范围：对比 `agents/src/open-canvas/index.ts` 与 `agents-py/src/open_canvas/graph.py`，聚焦 Phase 5 控制流与组装逻辑。

## 功能对齐情况

- **route_node（Send 动态路由到 9 个目标节点）**：
  Python `route_node` 与 TS 一致：检查 `next`，返回 `Send(next, dict(state))`。目标节点列表也完整一致。

- **clean_state（DEFAULT_INPUTS 状态重置）**：
  Python `clean_state` 返回 `DEFAULT_INPUTS.copy()`，与 TS 的 `{...DEFAULT_INPUTS}` 一致。

- **conditionally_generate_title（三分支）**：
  Python 实现为「`messages` 长度 ≤ 2 → generateTitle，否则 → simple_token_calculator」；与 TS 的「`messages` > 2 → simpleTokenCalculator，否则 → generateTitle」逻辑等价。

- **simple_token_calculator（CHARACTER_MAX=300000）**：
  Python 通过 `CHARACTER_MAX` 判定 `summarizer`/`END`，阈值与 TS 一致（300000）。

- **route_post_web_search（Send/Command 双模式）**：
  Python 逻辑与 TS 对齐：无搜索结果 `Send` 到 `generateArtifact/rewriteArtifact` 并关闭 `webSearchEnabled`；有结果用 `Command` 更新 `messages/_messages` 并路由。

- **StateGraph 边配置（控制流映射）**：
  Python 的节点与边整体映射与 TS 对齐：`generatePath` 条件路由 9 个目标节点，`webSearch → routePostWebSearch`，`generateFollowup → reflect → cleanState`，`cleanState` 条件路由到 `generateTitle/summarizer/END` 等均完整存在。

结论：**Phase 5 控制流整体迁移正确**，核心路由与边配置与 TS 对齐。

## 发现的问题或差异

1. **`simple_token_calculator` 的内容解析覆盖不完整**
   - TS：对 `msg.content` 非字符串情况使用 `flatMap` 并检查 `"text" in c`。
   - Python：仅处理 `content` 为 list 且元素是 dict 且含 `"text"`。如果内容元素为对象（有 `text` 属性但非 dict），Python 会漏算字符数。
   - 影响：可能低估字符数，导致未触发 `summarizer`。

2. **`simple_token_calculator` 返回 `"__end__"` 字符串而非 `END` 常量**
   - TS 使用 `END` 常量返回；Python 返回字面字符串 `"__end__"`。
   - LangGraph 当前 `END == "__end__"`，运行上大概率等价，但**可维护性/一致性略低**。

3. **`webSearch` 节点是占位实现（非 TS 子图）**
   - TS 使用 `webSearchGraph` 子图；Python 目前用 `web_search` stub 返回空结果。
   - 影响：`route_post_web_search` 逻辑虽正确，但**行为总是走无结果分支**，与 TS 运行效果不一致。

4. **编译配置不一致（非控制流）**
   - TS `graph.compile().withConfig({ runName: "open_canvas" })`；Python 直接 `compile()`。
   - 不影响控制流，但会影响运行可观测性/追踪标识。

## 改进建议

1. **增强 `simple_token_calculator` 的内容解析**
   - 建议同时支持 dict 与对象类型：
     - dict：`"text" in c`
     - 对象：`hasattr(c, "text")`
   - 以确保与 TS 的 `"text" in c` 语义一致。

2. **返回 `END` 常量而非 `"__end__"` 字面值**
   - 统一风格并避免未来常量变化造成隐患。

3. **Phase 6 前可显式标注 stub 行为**
   - 在 `web_search` stub 的 docstring 或 TODO 中说明“当前始终无结果”，避免误以为已接入真实 web 搜索子图。

4. **可选：补齐 `runName` 配置**
   - 若需要与 TS 可观测性一致，可在 Python `graph.compile()` 后补 `with_config(run_name="open_canvas")` 或对应 API。

---

审查文件：
- TS：`agents/src/open-canvas/index.ts`
- Python：`agents-py/src/open_canvas/graph.py`
- 规范参考：`../docs/workflow/langgraph-python-migration-workflow.md`（Phase 5）
