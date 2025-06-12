#!/bin/bash

# Test runner script for the coding study Flask application
# This script sets up the environment and runs the test suite

echo "🧪 Running Coding Study Test Suite"
echo "=================================="

# Check if we're in the right directory
if [ ! -f "app.py" ]; then
    echo "❌ Error: Please run this script from the project root directory"
    exit 1
fi

# Check if pytest is installed
if ! command -v pytest &> /dev/null; then
    echo "📦 Installing test dependencies..."
    pip install -r requirements.txt
fi

# Set up test environment variables
export DEVELOPMENT_MODE=true
export DEV_PARTICIPANT_ID=test-participant
export DEV_STAGE=1
export SURVEY_URL=https://example.com/test-survey
export UX_SURVEY_URL=https://example.com/test-ux-survey
export GITHUB_ORG=test-org
export SECRET_KEY=test-secret-key

echo "🏃 Running tests..."
echo ""

# Run the test suite
pytest

# Check exit code
if [ $? -eq 0 ]; then
    echo ""
    echo "✅ All tests passed!"
    echo ""
    echo "💡 To run specific test categories:"
    echo "   pytest tests/test_task_manager.py       # Task management tests"
    echo "   pytest tests/test_participant_manager.py # Participant tests"
    echo "   pytest tests/test_azure_service.py      # Azure service tests"
    echo "   pytest tests/test_github_service.py     # GitHub service tests"
    echo "   pytest tests/test_study_logger.py       # Logging tests"
    echo "   pytest tests/test_app.py                # Flask route tests"
    echo "   pytest tests/test_services.py           # Services facade tests"
    echo ""
    echo "💡 To run with coverage:"
    echo "   pip install pytest-cov"
    echo "   pytest --cov=. --cov-report=html"
else
    echo ""
    echo "❌ Some tests failed. Check the output above for details."
    exit 1
fi
