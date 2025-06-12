# Testing Documentation

This directory contains comprehensive tests for the coding study Flask application.

## Test Structure

- **tests/test_task_manager.py** - Tests for task loading and session management
- **tests/test_participant_manager.py** - Tests for participant identification and coding conditions
- **tests/test_azure_service.py** - Tests for Azure metadata service integration
- **tests/test_github_service.py** - Tests for GitHub connectivity and authentication
- **tests/test_study_logger.py** - Tests for logging functionality and session tracking
- **tests/test_app.py** - Tests for Flask routes and web application functionality
- **tests/test_services.py** - Tests for the service facade module
- **tests/test_integration.py** - Integration tests for complete study flow

## Running Tests

### Run All Tests
```bash
./run-tests.sh
```

### Run Specific Test Files
```bash
pytest tests/test_task_manager.py -v
pytest tests/test_app.py -v
```

### Run with Coverage
```bash
pip install pytest-cov
pytest --cov=. --cov-report=html
```

## Key Testing Principles

1. **Unit Tests**: Each component is tested in isolation with mocked dependencies
2. **Integration Tests**: Key workflows are tested end-to-end
3. **Realistic Mocking**: Tests use mocks that reflect actual behavior
4. **Development Safety**: Tests can run safely without affecting real GitHub repos or Azure services

## Implementation Notes

### Coding Conditions
- The system uses "vibe" and "ai-assisted" conditions
- Assignment is hash-based for consistency per participant
- Default fallback is "vibe" for unknown participants

### Session Management
- Session data is separated by study stage (stage1/stage2)
- Timer and task completion are tracked independently per stage

### Logging
- Development logs go to `./logs-{participant_id}`
- Production logs go to `~/workspace/logs-{participant_id}`
- Route logging prevents duplicate entries per session

### Azure Integration
- Development mode uses mock participant IDs
- Production failures fall back to "Study Participant"
- Stage determination uses Azure VM tags

## Fixtures and Helpers

The `conftest.py` file provides shared fixtures:
- `client`: Flask test client
- `temp_dir`: Temporary directory for file operations
- `mock_session`: Empty session for testing
- `sample_participant_id`: Consistent test participant ID
- Various service mocks for isolated testing
