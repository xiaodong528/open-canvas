#!/bin/bash
#
# System Check Script
#
# This script validates the Open Canvas system by checking backend health,
# graph registration, and running all test suites.
#
# Usage: ./system-check.sh [check...] | all
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Track results
TOTAL_PASSED=0
TOTAL_FAILED=0

# Check flags (default: false)
RUN_HEALTH=false
RUN_GRAPHS=false
RUN_UNIT=false
RUN_INTEGRATION=false
RUN_E2E=false

# Show help message
show_help() {
    echo "Usage: $0 [check...] | all"
    echo ""
    echo "Checks:"
    echo "  health       Backend health check (/ok endpoint)"
    echo "  graphs       Graph registration verification"
    echo "  unit         Python unit tests"
    echo "  integration  Python integration tests"
    echo "  e2e          E2E Playwright tests"
    echo "  all          Run all checks (default)"
    echo ""
    echo "Examples:"
    echo "  $0                      # Run all checks"
    echo "  $0 all                  # Run all checks"
    echo "  $0 health               # Run only health check"
    echo "  $0 health graphs        # Run health and graphs checks"
    echo "  $0 unit integration     # Run unit and integration tests"
}

# Parse arguments
if [ $# -eq 0 ] || [ "$1" = "all" ]; then
    RUN_HEALTH=true
    RUN_GRAPHS=true
    RUN_UNIT=true
    RUN_INTEGRATION=true
    RUN_E2E=true
else
    for arg in "$@"; do
        case $arg in
            health) RUN_HEALTH=true ;;
            graphs) RUN_GRAPHS=true ;;
            unit) RUN_UNIT=true ;;
            integration) RUN_INTEGRATION=true ;;
            e2e) RUN_E2E=true ;;
            -h|--help) show_help; exit 0 ;;
            *) echo -e "${RED}Unknown check: $arg${NC}"; echo ""; show_help; exit 1 ;;
        esac
    done
fi

# Function to log result
log_result() {
    local test_name=$1
    local status=$2
    local details=$3

    if [ "$status" = "PASS" ]; then
        echo -e "${GREEN}✓${NC} $test_name"
        TOTAL_PASSED=$((TOTAL_PASSED + 1))
    else
        echo -e "${RED}✗${NC} $test_name"
        if [ -n "$details" ]; then
            echo -e "  ${YELLOW}→ $details${NC}"
        fi
        TOTAL_FAILED=$((TOTAL_FAILED + 1))
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

# Print header
echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║              Open Canvas System Check                        ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo -e "${BLUE}Project Root:${NC} $PROJECT_ROOT"
echo ""

# ═══════════════════════════════════════════════════════════════════
# Check 1: Backend Health
# ═══════════════════════════════════════════════════════════════════

if [ "$RUN_HEALTH" = true ]; then
    echo -e "${BLUE}═══ Check: Backend Health ═══${NC}"

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
fi

# ═══════════════════════════════════════════════════════════════════
# Check 2: Graph Registration
# ═══════════════════════════════════════════════════════════════════

if [ "$RUN_GRAPHS" = true ]; then
    echo -e "${BLUE}═══ Check: Graph Registration ═══${NC}"

    if check_port 54367; then
        ASSISTANTS=$(curl -s -X POST http://localhost:54367/assistants/search -H "Content-Type: application/json" -d '{}' 2>/dev/null || echo "[]")

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
fi

# ═══════════════════════════════════════════════════════════════════
# Check 3: Python Unit Tests
# ═══════════════════════════════════════════════════════════════════

if [ "$RUN_UNIT" = true ]; then
    echo -e "${BLUE}═══ Check: Python Unit Tests ═══${NC}"

    cd "$PROJECT_ROOT/apps/agents-py"

    if [ -d "tests/unit" ]; then
        # Run unit tests and capture exit code
        set +e
        uv run python -m pytest tests/unit -v --tb=short 2>&1 | tail -20
        TEST_EXIT_CODE=${PIPESTATUS[0]}
        set -e
        if [ "$TEST_EXIT_CODE" -eq 0 ]; then
            log_result "Python unit tests pass" "PASS"
        else
            log_result "Python unit tests pass" "FAIL" "Exit code: $TEST_EXIT_CODE"
        fi
    else
        log_result "Python unit tests pass" "FAIL" "tests/unit directory not found"
    fi

    cd "$PROJECT_ROOT"
    echo ""
fi

# ═══════════════════════════════════════════════════════════════════
# Check 4: Python Integration Tests
# ═══════════════════════════════════════════════════════════════════

if [ "$RUN_INTEGRATION" = true ]; then
    echo -e "${BLUE}═══ Check: Python Integration Tests ═══${NC}"

    cd "$PROJECT_ROOT/apps/agents-py"

    if [ -d "tests/integration" ]; then
        # Run integration tests and capture exit code
        set +e
        uv run python -m pytest tests/integration -v --tb=short -m "not requires_api" 2>&1 | tail -20
        TEST_EXIT_CODE=${PIPESTATUS[0]}
        set -e
        if [ "$TEST_EXIT_CODE" -eq 0 ]; then
            log_result "Python integration tests pass" "PASS"
        else
            log_result "Python integration tests pass" "FAIL" "Exit code: $TEST_EXIT_CODE"
        fi
    else
        log_result "Python integration tests pass" "FAIL" "tests/integration directory not found"
    fi

    cd "$PROJECT_ROOT"
    echo ""
fi

# ═══════════════════════════════════════════════════════════════════
# Check 5: E2E Tests (if running)
# ═══════════════════════════════════════════════════════════════════

if [ "$RUN_E2E" = true ]; then
    echo -e "${BLUE}═══ Check: E2E Tests ═══${NC}"

    if check_port 3000 && check_port 54367; then
        cd "$PROJECT_ROOT/apps/web"

        if [ -d "e2e" ]; then
            echo "Running Playwright E2E tests..."
            set +e
            yarn playwright test --reporter=line 2>&1 | tail -30
            TEST_EXIT_CODE=${PIPESTATUS[0]}
            set -e
            if [ "$TEST_EXIT_CODE" -eq 0 ]; then
                log_result "E2E tests pass" "PASS"
            else
                log_result "E2E tests pass" "FAIL" "Exit code: $TEST_EXIT_CODE"
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
fi

# ═══════════════════════════════════════════════════════════════════
# Summary
# ═══════════════════════════════════════════════════════════════════

# Only show summary if at least one check was run
if [ $TOTAL_PASSED -gt 0 ] || [ $TOTAL_FAILED -gt 0 ]; then
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║                         Summary                               ║"
    echo "╠══════════════════════════════════════════════════════════════╣"

    if [ $TOTAL_FAILED -eq 0 ]; then
        echo -e "║  ${GREEN}✓ ALL CHECKS PASSED${NC}                                         ║"
        echo "║                                                              ║"
        echo -e "║  Passed: ${GREEN}$TOTAL_PASSED${NC}                                              ║"
        echo -e "║  Failed: ${GREEN}0${NC}                                                  ║"
        echo "╠══════════════════════════════════════════════════════════════╣"
        echo "║  System is healthy and ready!                                ║"
    else
        echo -e "║  ${RED}✗ SOME CHECKS FAILED${NC}                                       ║"
        echo "║                                                              ║"
        echo -e "║  Passed: ${GREEN}$TOTAL_PASSED${NC}                                              ║"
        echo -e "║  Failed: ${RED}$TOTAL_FAILED${NC}                                              ║"
        echo "╠══════════════════════════════════════════════════════════════╣"
        echo "║  Please fix the failing tests before proceeding.             ║"
    fi

    echo "╚══════════════════════════════════════════════════════════════╝"
    echo ""
fi

# Exit with appropriate code
if [ $TOTAL_FAILED -gt 0 ]; then
    exit 1
else
    exit 0
fi
