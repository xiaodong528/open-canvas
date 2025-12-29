# Open Canvas

![Screenshot of app](./static/screenshot.png)

一个开源的 AI 协作编辑应用，支持 Markdown 文档编辑、代码撰写和 React 组件实时渲染。灵感来源于 [OpenAI Canvas](https://openai.com/index/introducing-canvas/)，但有以下关键差异。

## 为什么选择 Open Canvas？

1. **开源**: 从前端到内容生成代理、反思代理，全部代码开源且采用 MIT 许可证。
2. **内置记忆**: 内置[反思代理](https://langchain-ai.github.io/langgraphjs/tutorials/reflection/reflection/)，将写作风格规则和用户洞察存储在[共享记忆存储](https://langchain-ai.github.io/langgraphjs/concepts/memory/)中，让 Open Canvas 能够跨会话记住你的偏好。
3. **从现有文档开始**: 允许用户从空白编辑器或已有内容开始，而不是强制从聊天交互开始。这是理想的用户体验，因为很多时候你已经有一些内容，想要在此基础上迭代。

## 特性

- **记忆系统** - 自动生成关于你和聊天历史的反思和记忆，在后续对话中提供更个性化的体验
- **自定义快捷操作** - 定义与用户绑定的自定义提示词，跨会话持久保存，一键应用到当前工件
- **预设快捷操作** - 常用写作和编码任务的预设快捷操作，随时可用
- **工件版本控制** - 所有工件都有版本记录，支持回溯查看历史版本
- **代码与 Markdown** - 工件视图支持代码和 Markdown 的查看与编辑，可在两者之间切换
- **实时 Markdown 渲染** - 边编辑边查看渲染后的 Markdown，无需来回切换
- **React 代码渲染** - 有效的 React 代码可实时预览和运行
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

- **前端**: [http://localhost:3000](http://localhost:3000)
- **后端**: [http://localhost:54367](http://localhost:54367)

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

## Supabase 认证设置

### 创建 Supabase 项目

1. 注册 [Supabase](https://supabase.com/) 账户
2. 访问 [Dashboard](https://supabase.com/dashboard/projects) 创建新项目

### 获取 API 密钥

1. 进入项目的 `Project Settings` 页面
2. 点击 `API` 标签
3. 复制 `Project URL` 和 `anon public` 项目 API 密钥
4. 粘贴到 `apps/web/.env` 文件的对应变量中：
   - `NEXT_PUBLIC_SUPABASE_URL`
   - `NEXT_PUBLIC_SUPABASE_ANON_KEY`

### 配置认证提供商

1. 进入 `Authentication` 页面，点击 `Providers` 标签
2. 确保 `Email` 已启用（同时确保启用 `Confirm Email`）
3. 可选启用 `GitHub` 和/或 `Google`：
   - [GitHub 认证配置](https://supabase.com/docs/guides/auth/social-login/auth-github)
   - [Google 认证配置](https://supabase.com/docs/guides/auth/social-login/auth-google)

### 验证认证功能

1. 运行 `yarn dev` 并访问 [localhost:3000](http://localhost:3000)
2. 页面应重定向到[登录页面](http://localhost:3000/auth/login)
3. 使用 Google/GitHub 登录，或访问[注册页面](http://localhost:3000/auth/signup)创建账户
4. 确认邮箱后应重定向到[首页](http://localhost:3000)

## Ollama 本地模型

Open Canvas 支持调用本地 Ollama 运行的 LLM。托管版本未启用此功能，但你可以在本地/自部署实例中使用。

### 配置步骤

1. 安装 [Ollama](https://ollama.com)
2. 拉取支持工具调用的模型（默认使用 `llama3.3`）：

   ```bash
   ollama pull llama3.3
   ```
3. 启动 Ollama 服务：

   ```bash
   ollama run llama3.3
   ```
4. 设置环境变量：

   - `NEXT_PUBLIC_OLLAMA_ENABLED=true`（在 `apps/web/.env`）
   - `OLLAMA_API_URL`（默认 `http://host.docker.internal:11434`，通常无需修改）

> **注意**: 开源 LLM 的指令遵循能力通常不如 GPT5 或 Claude Sonnet 等专有模型。使用本地 LLM 时可能会遇到错误或意外行为。

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
