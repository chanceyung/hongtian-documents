#!/bin/bash
# Test runner script for HongTian Docs

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}===========================================${NC}"
echo -e "${GREEN}  HongTian Docs Test Suite${NC}"
echo -e "${GREEN}===========================================${NC}"
echo ""

# Check if we're in the right directory
if [ ! -f "backend/requirements-v4.txt" ]; then
    echo -e "${RED}Error: Please run this script from the project root directory${NC}"
    echo "Expected to find backend/requirements-v4.txt"
    exit 1
fi

# Change to backend directory
cd backend

# Function to print section headers
print_header() {
    echo ""
    echo -e "${YELLOW}>>> $1${NC}"
    echo ""
}

# Check if test dependencies are installed
print_header "Checking test dependencies..."
if ! python -c "import pytest" 2>/dev/null; then
    echo -e "${YELLOW}Test dependencies not found. Installing...${NC}"
    pip install -r tests/requirements-test.txt
fi

# Run tests based on arguments
TEST_TYPE="${1:-all}"

case $TEST_TYPE in
    "all")
        print_header "Running all tests with coverage..."
        pytest tests/ -v --cov=app --cov-report=html --cov-report=term-missing
        ;;
    "agents")
        print_header "Running agent tests..."
        pytest tests/test_agents/ -v
        ;;
    "workflow")
        print_header "Running workflow tests..."
        pytest tests/test_workflow/ -v
        ;;
    "api")
        print_header "Running API tests..."
        pytest tests/test_api/ -v
        ;;
    "parser")
        print_header "Running parser agent tests..."
        pytest tests/test_agents/test_parser_agent.py -v
        ;;
    "analyzer")
        print_header "Running analyzer agent tests..."
        pytest tests/test_agents/test_analyzer_agent.py -v
        ;;
    "designer")
        print_header "Running designer agent tests..."
        pytest tests/test_agents/test_designer_agent.py -v
        ;;
    "renderer")
        print_header "Running renderer agent tests..."
        pytest tests/test_agents/test_renderer_agent.py -v
        ;;
    "fidelity")
        print_header "Running fidelity agent tests..."
        pytest tests/test_agents/test_fidelity_agent.py -v
        ;;
    "supplement")
        print_header "Running supplement agent tests..."
        pytest tests/test_agents/test_supplement_agent.py -v
        ;;
    "coverage")
        print_header "Running tests and generating coverage report..."
        pytest tests/ --cov=app --cov-report=html --cov-report=term-missing --cov-report=xml
        echo ""
        echo -e "${GREEN}Coverage report generated in htmlcov/index.html${NC}"
        ;;
    "fast")
        print_header "Running fast tests only (skipping slow tests)..."
        pytest tests/ -v -m "not slow"
        ;;
    "parallel")
        print_header "Running tests in parallel..."
        pytest tests/ -v -n auto
        ;;
    *)
        echo -e "${RED}Unknown test type: $TEST_TYPE${NC}"
        echo ""
        echo "Available test types:"
        echo "  all       - Run all tests with coverage (default)"
        echo "  agents    - Run all agent tests"
        echo "  workflow  - Run workflow tests"
        echo "  api       - Run API tests"
        echo "  parser    - Run parser agent tests"
        echo "  analyzer  - Run analyzer agent tests"
        echo "  designer  - Run designer agent tests"
        echo "  renderer  - Run renderer agent tests"
        echo "  fidelity  - Run fidelity agent tests"
        echo "  supplement- Run supplement agent tests"
        echo "  coverage  - Generate coverage report"
        echo "  fast      - Run fast tests only"
        echo "  parallel  - Run tests in parallel"
        exit 1
        ;;
esac

# Print summary
EXIT_CODE=$?
echo ""
if [ $EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed!${NC}"
else
    echo -e "${RED}✗ Some tests failed!${NC}"
fi

exit $EXIT_CODE