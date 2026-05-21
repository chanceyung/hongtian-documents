@echo off
REM Test runner script for HongTian Docs (Windows)

setlocal enabledelayedexpansion

set "RED=[91m"
set "GREEN=[92m"
set "YELLOW=[93m"
set "NC=[0m"

echo %GREEN%===========================================%NC%
echo %GREEN%  HongTian Docs Test Suite%NC%
echo %GREEN%===========================================%NC%
echo.

REM Check if we're in the right directory
if not exist "backend\requirements-v4.txt" (
    echo %RED%Error: Please run this script from the project root directory%NC%
    echo Expected to find backend\requirements-v4.txt
    exit /b 1
)

REM Change to backend directory
cd backend

REM Check if test dependencies are installed
echo %YELLOW%>>> Checking test dependencies...%NC%
python -c "import pytest" 2>nul
if errorlevel 1 (
    echo %YELLOW%Test dependencies not found. Installing...%NC%
    pip install -r tests\requirements-test.txt
)

REM Run tests based on arguments
set "TEST_TYPE=%~1"
if "%TEST_TYPE%"=="" set "TEST_TYPE=all"

if "%TEST_TYPE%"=="all" (
    echo.
    echo %YELLOW%>>> Running all tests with coverage...%NC%
    pytest tests/ -v --cov=app --cov-report=html --cov-report=term-missing
) else if "%TEST_TYPE%"=="agents" (
    echo.
    echo %YELLOW%>>> Running agent tests...%NC%
    pytest tests\test_agents/ -v
) else if "%TEST_TYPE%"=="workflow" (
    echo.
    echo %YELLOW%>>> Running workflow tests...%NC%
    pytest tests\test_workflow/ -v
) else if "%TEST_TYPE%"=="api" (
    echo.
    echo %YELLOW%>>> Running API tests...%NC%
    pytest tests\test_api/ -v
) else if "%TEST_TYPE%"=="parser" (
    echo.
    echo %YELLOW%>>> Running parser agent tests...%NC%
    pytest tests\test_agents\test_parser_agent.py -v
) else if "%TEST_TYPE%"=="analyzer" (
    echo.
    echo %YELLOW%>>> Running analyzer agent tests...%NC%
    pytest tests\test_agents\test_analyzer_agent.py -v
) else if "%TEST_TYPE%"=="designer" (
    echo.
    echo %YELLOW%>>> Running designer agent tests...%NC%
    pytest tests\test_agents\test_designer_agent.py -v
) else if "%TEST_TYPE%"=="renderer" (
    echo.
    echo %YELLOW%>>> Running renderer agent tests...%NC%
    pytest tests\test_agents\test_renderer_agent.py -v
) else if "%TEST_TYPE%"=="fidelity" (
    echo.
    echo %YELLOW%>>> Running fidelity agent tests...%NC%
    pytest tests\test_agents\test_fidelity_agent.py -v
) else if "%TEST_TYPE%"=="supplement" (
    echo.
    echo %YELLOW%>>> Running supplement agent tests...%NC%
    pytest tests\test_agents\test_supplement_agent.py -v
) else if "%TEST_TYPE%"=="coverage" (
    echo.
    echo %YELLOW%>>> Running tests and generating coverage report...%NC%
    pytest tests/ --cov=app --cov-report=html --cov-report=term-missing --cov-report=xml
    echo.
    echo %GREEN%Coverage report generated in htmlcov\index.html%NC%
) else if "%TEST_TYPE%"=="fast" (
    echo.
    echo %YELLOW%>>> Running fast tests only (skipping slow tests)...%NC%
    pytest tests/ -v -m "not slow"
) else if "%TEST_TYPE%"=="parallel" (
    echo.
    echo %YELLOW%>>> Running tests in parallel...%NC%
    pytest tests/ -v -n auto
) else (
    echo %RED%Unknown test type: %TEST_TYPE%%NC%
    echo.
    echo Available test types:
    echo   all       - Run all tests with coverage (default)
    echo   agents    - Run all agent tests
    echo   workflow  - Run workflow tests
    echo   api       - Run API tests
    echo   parser    - Run parser agent tests
    echo   analyzer  - Run analyzer agent tests
    echo   designer  - Run designer agent tests
    echo   renderer  - Run renderer agent tests
    echo   fidelity  - Run fidelity agent tests
    echo   supplement- Run supplement agent tests
    echo   coverage  - Generate coverage report
    echo   fast      - Run fast tests only
    echo   parallel  - Run tests in parallel
    exit /b 1
)

REM Print summary
if errorlevel 1 (
    echo.
    echo %RED%✗ Some tests failed!%NC%
    exit /b 1
) else (
    echo.
    echo %GREEN%✓ All tests passed!%NC%
    exit /b 0
)