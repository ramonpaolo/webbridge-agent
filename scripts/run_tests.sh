#!/bin/bash
# Test runner script for webbridge-agent

set -e

echo "========================================"
echo "  webbridge-agent Test Suite"
echo "========================================"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to run tests and report
run_tests() {
    local description="$1"
    local command="$2"
    
    echo -e "\n${YELLOW}Running: ${description}${NC}"
    if eval "$command"; then
        echo -e "${GREEN}✓ PASSED${NC}"
        return 0
    else
        echo -e "${RED}✗ FAILED${NC}"
        return 1
    fi
}

# Track results
FAILED=0

# Unit tests
run_tests "Unit Tests" "pytest tests/unit/ -v --tb=short" || FAILED=1

# Integration tests
run_tests "Integration Tests" "pytest tests/integration/ -v --tb=short" || FAILED=1

# Security tests
run_tests "Security Tests" "pytest tests/security/ -v --tb=short" || FAILED=1

# Summary
echo -e "\n========================================"
echo "  Test Summary"
echo "========================================"
if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}Some tests failed.${NC}"
    exit 1
fi
