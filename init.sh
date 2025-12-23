#!/bin/bash

# =============================================================================
# Open Canvas 启动脚本
# 同时启动后端 (LangGraph Python) 和前端 (Next.js) 服务
# 日志输出到 logs/ 目录
# =============================================================================

set -e

# === 配置 ===
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/apps/agents-py"
FRONTEND_DIR="$SCRIPT_DIR/apps/web"
LOG_DIR="$SCRIPT_DIR/logs"
BACKEND_PORT=54367
FRONTEND_PORT=3000
SHARED_WATCH_PID=""

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# === 辅助函数 ===
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[OK]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 清理函数 - 终止所有子进程
cleanup() {
    echo ""
    log_info "正在停止服务..."

    if [ -n "$BACKEND_PID" ] && kill -0 "$BACKEND_PID" 2>/dev/null; then
        kill "$BACKEND_PID" 2>/dev/null
        log_info "后端服务已停止 (PID: $BACKEND_PID)"
    fi

    if [ -n "$FRONTEND_PID" ] && kill -0 "$FRONTEND_PID" 2>/dev/null; then
        kill "$FRONTEND_PID" 2>/dev/null
        log_info "前端服务已停止 (PID: $FRONTEND_PID)"
    fi

    if [ -n "$SHARED_WATCH_PID" ] && kill -0 "$SHARED_WATCH_PID" 2>/dev/null; then
        kill "$SHARED_WATCH_PID" 2>/dev/null
        log_info "共享包监听已停止 (PID: $SHARED_WATCH_PID)"
    fi

    # 清理可能残留的端口占用
    lsof -ti:$BACKEND_PORT | xargs kill -9 2>/dev/null || true
    lsof -ti:$FRONTEND_PORT | xargs kill -9 2>/dev/null || true

    log_success "所有服务已停止"
    exit 0
}

# 检查端口是否被占用 - 自动清理
check_port() {
    local port=$1
    local name=$2

    if lsof -ti:$port > /dev/null 2>&1; then
        log_warn "端口 $port ($name) 已被占用，正在自动清理..."
        lsof -ti:$port | xargs kill -9 2>/dev/null || true
        sleep 1
        if lsof -ti:$port > /dev/null 2>&1; then
            log_error "无法释放端口 $port，请手动检查"
            exit 1
        fi
        log_success "端口 $port 已释放"
    fi
}

# 检查目录是否存在
check_directory() {
    local dir=$1
    local name=$2

    if [ ! -d "$dir" ]; then
        log_error "$name 目录不存在: $dir"
        exit 1
    fi
}

# === 信号处理 ===
trap cleanup SIGINT SIGTERM

# === 主流程 ===
main() {
    echo ""
    echo "============================================"
    echo "       Open Canvas 服务启动脚本"
    echo "============================================"
    echo ""

    # 1. 检查目录
    log_info "检查项目目录..."
    echo -e "    → 后端: ${BLUE}$BACKEND_DIR${NC}"
    echo -e "    → 前端: ${BLUE}$FRONTEND_DIR${NC}"
    check_directory "$BACKEND_DIR" "后端 (agents-py)"
    check_directory "$FRONTEND_DIR" "前端 (web)"
    log_success "目录检查通过"

    # 2. 创建日志目录
    log_info "创建日志目录..."
    mkdir -p "$LOG_DIR"
    log_success "日志目录已就绪: $LOG_DIR/"

    # 3. 清理旧日志文件
    log_info "清理旧日志文件..."
    rm -f "$LOG_DIR/agents-py.log" "$LOG_DIR/web.log" "$LOG_DIR/shared-watch.log"
    log_success "日志文件已清理: agents-py.log, web.log, shared-watch.log"

    # 4. 检查端口
    log_info "检查端口占用: $BACKEND_PORT (后端), $FRONTEND_PORT (前端)..."
    check_port $BACKEND_PORT "后端"
    check_port $FRONTEND_PORT "前端"
    log_success "端口检查通过"

    # 5. 同步后端依赖
    log_info "同步后端依赖 (uv sync)..."
    echo -e "    → 目录: ${BLUE}$BACKEND_DIR${NC}"
    cd "$BACKEND_DIR"
    uv sync --quiet
    log_success "后端依赖同步完成"

    # 6. 安装 monorepo 依赖
    log_info "安装 monorepo 依赖 (yarn install)..."
    echo -e "    → 目录: ${BLUE}$SCRIPT_DIR${NC} (根目录)"
    cd "$SCRIPT_DIR"
    yarn install --silent
    log_success "monorepo 依赖安装完成"

    # 7. 构建共享包
    log_info "构建共享包 (yarn build)..."
    echo -e "    → packages/shared"
    echo -e "    → packages/evals"
    yarn build
    log_success "共享包构建完成"

    # 8. 启动后端服务
    log_info "启动后端服务 (LangGraph Python)..."
    cd "$BACKEND_DIR"

    # 使用 uv 运行 langgraph dev
    if command -v uv &> /dev/null; then
        uv run langgraph dev --port $BACKEND_PORT > "$LOG_DIR/agents-py.log" 2>&1 &
    else
        # 回退到直接运行
        langgraph dev --port $BACKEND_PORT > "$LOG_DIR/agents-py.log" 2>&1 &
    fi
    BACKEND_PID=$!
    log_success "后端服务已启动"
    echo -e "    → PID: ${GREEN}$BACKEND_PID${NC}"
    echo -e "    → 端口: ${GREEN}$BACKEND_PORT${NC}"
    echo -e "    → 日志: ${BLUE}$LOG_DIR/agents-py.log${NC}"

    # 9. 启动共享包监听
    log_info "启动共享包监听 (tsc --watch)..."
    cd "$SCRIPT_DIR/packages/shared"
    npx tsc --watch --preserveWatchOutput > "$LOG_DIR/shared-watch.log" 2>&1 &
    SHARED_WATCH_PID=$!
    log_success "共享包监听已启动"
    echo -e "    → PID: ${GREEN}$SHARED_WATCH_PID${NC}"
    echo -e "    → 日志: ${BLUE}$LOG_DIR/shared-watch.log${NC}"

    # 10. 启动前端服务
    log_info "启动前端服务 (Next.js)..."
    cd "$FRONTEND_DIR"
    yarn dev > "$LOG_DIR/web.log" 2>&1 &
    FRONTEND_PID=$!
    log_success "前端服务已启动"
    echo -e "    → PID: ${GREEN}$FRONTEND_PID${NC}"
    echo -e "    → 端口: ${GREEN}$FRONTEND_PORT${NC}"
    echo -e "    → 日志: ${BLUE}$LOG_DIR/web.log${NC}"

    # 11. 等待服务启动
    log_info "等待服务启动..."
    sleep 3

    # 12. 显示状态信息
    echo ""
    echo "============================================"
    echo "            服务启动完成"
    echo "============================================"
    echo ""
    echo -e "  ${GREEN}前端${NC}:  http://localhost:$FRONTEND_PORT"
    echo -e "  ${GREEN}后端${NC}:  http://localhost:$BACKEND_PORT"
    echo ""
    echo "  日志文件:"
    echo "    - 后端: $LOG_DIR/agents-py.log"
    echo "    - 共享包: $LOG_DIR/shared-watch.log"
    echo "    - 前端: $LOG_DIR/web.log"
    echo ""
    echo "  实时查看日志:"
    echo "    tail -f $LOG_DIR/agents-py.log"
    echo "    tail -f $LOG_DIR/shared-watch.log"
    echo "    tail -f $LOG_DIR/web.log"
    echo ""
    echo -e "  ${YELLOW}按 Ctrl+C 停止所有服务${NC}"
    echo "============================================"
    echo ""

    # 13. 实时显示日志
    log_info "显示实时日志 (Ctrl+C 停止)..."
    echo ""

    # 使用 tail 同时监控三个日志文件
    tail -f "$LOG_DIR/agents-py.log" "$LOG_DIR/shared-watch.log" "$LOG_DIR/web.log" &
    TAIL_PID=$!

    # 等待子进程
    wait $BACKEND_PID $SHARED_WATCH_PID $FRONTEND_PID 2>/dev/null || true
}

# 运行主函数
main "$@"
