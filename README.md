# Open Canvas

一个开源的 AI 协作编辑应用，支持 Markdown 文档编辑、代码撰写和 React 组件实时渲染。

## 特性

- **Markdown 文档编辑** - 基于 BlockNote 的富文本编辑器，支持实时预览
- **代码撰写** - 基于 CodeMirror 的多语言代码编辑器
- **React 代码渲染** - 有效的 React 代码可实时预览和运行
- **AI 协作** - 与 LLM 对话生成和修改内容，支持快捷操作
- **版本历史** - 完整的工件版本控制，支持回滚和对比
- **多 LLM 支持** - OpenAI、Anthropic、Google Gemini、Fireworks、Groq、Ollama 等

## 快速开始

### 环境要求

- Python >= 3.12
- Node.js >= 18
- Yarn 1.22.22
- [uv](https://docs.astral.sh/uv/) (Python 包管理器)

### 一键启动（推荐）

```bash
# 1. 克隆项目
git clone https://github.com/xiaodong528/open-canvas.git
cd open-canvas

# 2. 配置环境变量（见下方"环境配置"章节）
cp apps/agents-py/.env.example apps/agents-py/.env
cp apps/web/.env.example apps/web/.env

# 3. 一键启动所有服务
chmod +x init.sh
./init.sh
```

启动后访问：

- **前端**: <http://localhost:3000>
- **后端**: <http://localhost:54367>

按 `Ctrl+C` 停止所有服务。

### 手动启动

如果需要分别控制各个服务：

```bash
# 终端 1：启动后端 (LangGraph Python)
cd apps/agents-py
uv sync
uv run langgraph dev --port 54367

# 终端 2：启动前端 (Next.js)
cd apps/web
yarn install
yarn build  # 首次运行需要构建共享包
yarn dev

# 终端 3（可选）：共享包热更新
cd packages/shared
npx tsc --watch
```

## 环境配置

### 后端环境变量

创建 `apps/agents-py/.env` 文件：

```bash
# =============================================================================
# LangSmith 追踪（推荐）
# =============================================================================
LANGSMITH_TRACING="true"
LANGSMITH_API_KEY="your-langsmith-api-key"
LANGSMITH_ENDPOINT=https://api.smith.langchain.com

# =============================================================================
# LLM API 密钥（至少配置一个）
# =============================================================================
# OpenAI
OPENAI_API_KEY=""

# Anthropic (Claude)
ANTHROPIC_API_KEY=""

# Google (Gemini)
GOOGLE_API_KEY=""

# Fireworks
FIREWORKS_API_KEY=""

# Groq
GROQ_API_KEY=""

# =============================================================================
# 外部服务
# =============================================================================
# Exa 搜索 API（用于网页搜索功能）
EXA_API_KEY=""

# =============================================================================
# 可选配置
# =============================================================================
# 服务端口（默认 54367）
PORT="54367"

# Ollama 本地 LLM
# OLLAMA_API_URL="http://host.docker.internal:11434"

# Azure OpenAI（注意：变量必须以下划线开头）
# _AZURE_OPENAI_API_KEY=""
# _AZURE_OPENAI_API_INSTANCE_NAME=""
# _AZURE_OPENAI_API_DEPLOYMENT_NAME=""
# _AZURE_OPENAI_API_VERSION="2024-08-01-preview"
```

### 前端环境变量

创建 `apps/web/.env` 文件：

```bash
# =============================================================================
# Supabase 认证（必需）
# =============================================================================
NEXT_PUBLIC_SUPABASE_URL=your-supabase-url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-supabase-anon-key

# 文档上传（可以与上面相同）
NEXT_PUBLIC_SUPABASE_URL_DOCUMENTS=
NEXT_PUBLIC_SUPABASE_ANON_KEY_DOCUMENTS=

# =============================================================================
# 模型可见性开关
# =============================================================================
NEXT_PUBLIC_OPENAI_ENABLED=true
NEXT_PUBLIC_ANTHROPIC_ENABLED=true
NEXT_PUBLIC_GEMINI_ENABLED=true
NEXT_PUBLIC_FIREWORKS_ENABLED=true
NEXT_PUBLIC_OLLAMA_ENABLED=false
NEXT_PUBLIC_AZURE_ENABLED=false
NEXT_PUBLIC_GROQ_ENABLED=false

# =============================================================================
# API 配置
# =============================================================================
NEXT_PUBLIC_API_URL=http://localhost:3000/api

# =============================================================================
# 可选服务
# =============================================================================
# 语音转录
GROQ_API_KEY=

# 网页抓取
FIRECRAWL_API_KEY=
```

## 项目架构

### 目录结构

```text
open-canvas/
├── apps/
│   ├── agents-py/          # LangGraph Python 后端（主要）
│   │   ├── src/
│   │   │   ├── open_canvas/    # 主 Agent 图
│   │   │   ├── reflection/     # 反思/记忆图
│   │   │   ├── thread_title/   # 标题生成图
│   │   │   ├── summarizer/     # 对话压缩图
│   │   │   └── web_search/     # 网页搜索图
│   │   ├── langgraph.json      # 图注册配置
│   │   └── pyproject.toml      # Python 依赖
│   │
│   ├── agents/             # LangGraph TypeScript 后端（遗留）
│   │
│   └── web/                # Next.js 14 前端
│       ├── src/
│       │   ├── app/            # Next.js App Router
│       │   ├── contexts/       # React Context（状态管理）
│       │   ├── components/     # UI 组件
│       │   └── workers/        # Web Workers（流处理）
│       └── package.json
│
├── packages/
│   ├── shared/             # 共享类型、模型配置
│   └── evals/              # 评估测试框架
│
├── scripts/
│   └── system-check.sh     # 系统检查脚本
│
├── init.sh                 # 一键启动脚本
└── CLAUDE.md               # 开发指南
```

### LangGraph 图

| 图               | 入口点                           | 用途                        |
| ---------------- | -------------------------------- | --------------------------- |
| `agent`        | `src.open_canvas.graph:graph`  | 主代理：路由、工件生成/编辑 |
| `reflection`   | `src.reflection.graph:graph`   | 用户洞察和写作风格记忆      |
| `thread_title` | `src.thread_title.graph:graph` | 自动生成对话标题            |
| `summarizer`   | `src.summarizer.graph:graph`   | 压缩长对话历史              |
| `web_search`   | `src.web_search.graph:graph`   | Exa 驱动的网页搜索          |

### 数据流

```text
用户输入 → GraphContext → ThreadProvider (LangGraph SDK)
    → Python 后端 (:54367) → generate_path (路由)
    → 节点执行 (generate_artifact, rewrite_artifact 等)
    → 流式响应 → StreamWorker → GraphContext 更新 → React 渲染
```

## 开发指南

### 代码质量

```bash
# TypeScript/JavaScript
yarn lint                   # 检查所有包
yarn lint:fix              # 自动修复
yarn format                 # Prettier 格式化

# Python
cd apps/agents-py
uv run ruff check src/     # Ruff 检查
uv run ruff check --fix src/
```

### 测试

```bash
# Python 后端测试
cd apps/agents-py
uv run python -m pytest tests/              # 所有测试
uv run python -m pytest tests/unit -v       # 单元测试
uv run python -m pytest tests/integration   # 集成测试
uv run python -m pytest -k "test_name"      # 指定测试

# 前端评估测试
cd apps/web
yarn eval                   # 所有评估测试
yarn eval -t "pattern"      # 匹配的测试

# E2E 测试（需要服务运行）
cd apps/web
yarn playwright test        # 运行所有 E2E 测试
yarn playwright test --ui   # UI 模式
```

### 系统检查

```bash
# 运行所有检查
./scripts/system-check.sh

# 运行指定检查
./scripts/system-check.sh health graphs unit integration
```

## 故障排除

| 问题                    | 原因                    | 解决方案                                    |
| ----------------------- | ----------------------- | ------------------------------------------- |
| 端口 54367/3000 被占用  | 旧进程未关闭            | `lsof -ti:54367 \| xargs kill -9`          |
| "Thread not found" 错误 | 后端数据库不同          | 清除浏览器 `oc_thread_id_v2` cookie       |
| 共享类型未更新          | TypeScript watch 未运行 | 启动 `tsc --watch` 在 `packages/shared` |
| Supabase 连接失败       | 环境变量未配置          | 检查 `NEXT_PUBLIC_SUPABASE_*` 变量        |
| 模型名称缺失            | 模型配置不匹配          | 确保 `customModelName` 在支持列表中       |

## 支持的 LLM 模型

| 提供商       | 模型示例                          | 环境变量              |
| ------------ | --------------------------------- | --------------------- |
| OpenAI       | gpt-4o, gpt-4.1, o3-mini, o4-mini | `OPENAI_API_KEY`    |
| Anthropic    | claude-3.5-sonnet, claude-opus-4  | `ANTHROPIC_API_KEY` |
| Google       | gemini-2.5-pro, gemini-2.5-flash  | `GOOGLE_API_KEY`    |
| Fireworks    | llama-v3.3-70b, deepseek-v3       | `FIREWORKS_API_KEY` |
| Groq         | deepseek-r1-distill-llama-70b     | `GROQ_API_KEY`      |
| Ollama       | llama3.3（本地）                  | `OLLAMA_API_URL`    |
| Azure OpenAI | 自定义部署                        | `_AZURE_OPENAI_*`   |

## 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件
