#!/bin/bash
#
# Phase 7 Gate Check Script
#
# This script runs all tests required for Phase 7 (Integration Testing)
# and reports the gate condition status.
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Track results
declare -A RESULTS
TOTAL_PASSED=0
TOTAL_FAILED=0

# Print header
echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║           Phase 7: Integration Testing Gate Check            ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# Function to log result
log_result() {
    local test_name=$1
    local status=$2
    local details=$3

    if [ "$status" = "PASS" ]; then
        echo -e "${GREEN}✓${NC} $test_name"
        RESULTS["$test_name"]="PASS"
        ((TOTAL_PASSED++))
    else
        echo -e "${RED}✗${NC} $test_name"
        if [ -n "$details" ]; then
            echo -e "  ${YELLOW}→ $details${NC}"
        fi
        RESULTS["$test_name"]="FAIL"
        ((TOTAL_FAILED++))
    fi
}

# Function to check if a port is in use
check_port() {
    local port=$1
    lsof -i :$port >/dev/null 2>&1
    return $?
}

# Change to project root
cd "$(dirname "$0")/.."
PROJECT_ROOT=$(pwd)

echo -e "${BLUE}Project Root:${NC} $PROJECT_ROOT"
echo ""

# ═══════════════════════════════════════════════════════════════════
# Gate Check 1: Backend Health
# ═══════════════════════════════════════════════════════════════════

echo -e "${BLUE}═══ Gate Check 1: Backend Health ═══${NC}"

# Check if backend is running
if check_port 54367; then
    # Try to hit the health endpoint
    HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:54367/ok 2>/dev/null || echo "000")
    if [ "$HTTP_STATUS" = "200" ]; then
        log_result "Python backend /ok returns 200" "PASS"
    else
        log_result "Python backend /ok returns 200" "FAIL" "Got HTTP $HTTP_STATUS"
    fi
else
    log_result "Python backend /ok returns 200" "FAIL" "Backend not running on port 54367"
fi

echo ""

# ═══════════════════════════════════════════════════════════════════
# Gate Check 2: Graph Registration
# ═══════════════════════════════════════════════════════════════════

echo -e "${BLUE}═══ Gate Check 2: Graph Registration ═══${NC}"

if check_port 54367; then
    ASSISTANTS=$(curl -s http://localhost:54367/assistants 2>/dev/null || echo "[]")

    EXPECTED_GRAPHS=("agent" "reflection" "thread_title" "summarizer" "web_search")
    ALL_FOUND=true

    for graph in "${EXPECTED_GRAPHS[@]}"; do
        if echo "$ASSISTANTS" | grep -q "\"graph_id\":\"$graph\""; then
            log_result "Graph '$graph' registered" "PASS"
        else
            log_result "Graph '$graph' registered" "FAIL"
            ALL_FOUND=false
        fi
    done
else
    for graph in agent reflection thread_title summarizer web_search; do
        log_result "Graph '$graph' registered" "FAIL" "Backend not running"
    done
fi

echo ""

# ═══════════════════════════════════════════════════════════════════
# Gate Check 3: Python Unit Tests
# ═══════════════════════════════════════════════════════════════════

echo -e "${BLUE}═══ Gate Check 3: Python Unit Tests ═══${NC}"

cd "$PROJECT_ROOT/apps/agents-py"

if [ -d "tests/unit" ]; then
    # Run unit tests
    if uv run pytest tests/unit -v --tb=short 2>&1 | tail -20; then
        log_result "Python unit tests pass" "PASS"
    else
        log_result "Python unit tests pass" "FAIL"
    fi
else
    log_result "Python unit tests pass" "FAIL" "tests/unit directory not found"
fi

cd "$PROJECT_ROOT"
echo ""

# ═══════════════════════════════════════════════════════════════════
# Gate Check 4: Python Integration Tests
# ═══════════════════════════════════════════════════════════════════

echo -e "${BLUE}═══ Gate Check 4: Python Integration Tests ═══${NC}"

cd "$PROJECT_ROOT/apps/agents-py"

if [ -d "tests/integration" ]; then
    # Run integration tests (graph compilation checks only)
    if uv run pytest tests/integration -v --tb=short -m "not requires_api" 2>&1 | tail -20; then
        log_result "Python integration tests pass" "PASS"
    else
        log_result "Python integration tests pass" "FAIL"
    fi
else
    log_result "Python integration tests pass" "FAIL" "tests/integration directory not found"
fi

cd "$PROJECT_ROOT"
echo ""

# ═══════════════════════════════════════════════════════════════════
# Gate Check 5: E2E Tests (if running)
# ═══════════════════════════════════════════════════════════════════

echo -e "${BLUE}═══ Gate Check 5: E2E Tests ═══${NC}"

if check_port 3000 && check_port 54367; then
    cd "$PROJECT_ROOT/apps/web"

    if [ -d "e2e" ]; then
        echo "Running Playwright E2E tests..."
        if yarn playwright test --reporter=line 2>&1 | tail -30; then
            log_result "E2E tests pass" "PASS"
        else
            log_result "E2E tests pass" "FAIL"
        fi
    else
        log_result "E2E tests pass" "FAIL" "e2e directory not found"
    fi
else
    log_result "E2E tests pass" "FAIL" "Frontend and/or backend not running"
    echo -e "  ${YELLOW}→ Start services with: ./init.sh${NC}"
fi

cd "$PROJECT_ROOT"
echo ""

# ═══════════════════════════════════════════════════════════════════
# Summary
# ═══════════════════════════════════════════════════════════════════

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                         Summary                               ║"
echo "╠══════════════════════════════════════════════════════════════╣"

if [ $TOTAL_FAILED -eq 0 ]; then
    echo -e "║  ${GREEN}✓ ALL GATE CHECKS PASSED${NC}                                    ║"
    echo "║                                                              ║"
    echo -e "║  Passed: ${GREEN}$TOTAL_PASSED${NC}                                              ║"
    echo -e "║  Failed: ${GREEN}0${NC}                                                  ║"
    echo "╠══════════════════════════════════════════════════════════════╣"
    echo "║  Phase 7 is ready for completion!                            ║"
else
    echo -e "║  ${RED}✗ SOME GATE CHECKS FAILED${NC}                                  ║"
    echo "║                                                              ║"
    echo -e "║  Passed: ${GREEN}$TOTAL_PASSED${NC}                                              ║"
    echo -e "║  Failed: ${RED}$TOTAL_FAILED${NC}                                              ║"
    echo "╠══════════════════════════════════════════════════════════════╣"
    echo "║  Please fix the failing tests before proceeding.             ║"
fi

echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# Exit with appropriate code
if [ $TOTAL_FAILED -gt 0 ]; then
    exit 1
else
    exit 0
fi
