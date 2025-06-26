# Repository Management Flow Tests

This directory contains comprehensive tests for the repository management logic that handles Git operations throughout the coding study.

## Test Coverage

### `test_repository_flow.py`
Unit tests for the core repository management functionality:

- **Stage 1 Complete Flow**: Tests repository cloning, tutorial branch setup, stage-1 branch creation, and all commit/push operations
- **Stage 2 Complete Flow**: Tests stage-2 branch creation from stage-1 and subsequent operations
- **Branch Creation Logic**: Tests the specific logic for creating branches from different sources (origin/main for stage-1, local stage-1 for stage-2)
- **Commit and Backup Workflow**: Tests the unified commit and push workflow used at transition points
- **Tutorial Workflow**: Tests tutorial branch setup and code pushing when transitioning from tutorial to task
- **Error Handling**: Tests graceful handling of Git operation failures
- **Services Integration**: Tests integration with the services layer facade

### `test_repository_integration.py`
Integration tests that simulate the actual Flask application flow:

- **Stage 1 User Journey**: Complete end-to-end test of Stage 1 participant flow through the web application
- **Stage 2 User Journey**: Complete end-to-end test of Stage 2 participant flow
- **Async Mode Operations**: Tests that async repository operations are properly queued
- **Error Handling**: Tests that the application continues working even when repository operations fail
- **Complete Study Flow Timing**: Tests the sequence and timing of repository operations throughout a complete study session

## Repository Flow Overview

The tests validate this normal flow:

### Stage 1:
1. **Session Start**: Repository is cloned from GitHub when user visits background questionnaire
2. **Tutorial Access**: Tutorial branch (from remote) is checked out when user visits tutorial page first time
3. **Tutorial to Task Transition**: Code is committed on active branch, all branches pushed when user goes from tutorial to task
4. **Task Page First Visit**: Stage-1 branch created from main branch, checked out and pushed
5. **Requirement Completion**: Code committed and all branches pushed when user marks requirements as completed
6. **Timer Expiration**: Code committed and all branches pushed when 40-minute timer ends
7. **UX Questionnaire Transition**: Code committed and all branches pushed when user goes to UX survey

### Stage 2:
1. **Task Page First Visit**: Stage-2 branch created from remote stage-1 branch, checked out and pushed
2. **Requirement Completion**: Code committed and all branches pushed when user marks requirements as completed
3. **Timer Expiration**: Code committed and all branches pushed when timer ends
4. **UX Questionnaire Transition**: Code committed and all branches pushed when user goes to UX survey

## Key Features Tested

- **Branch Management**: Correct creation of stage-specific branches from appropriate sources
- **Automatic Commits**: Code is automatically committed at all major transition points
- **Backup Strategy**: All local branches are pushed to remote for comprehensive backup
- **Error Resilience**: Application continues functioning even when Git operations fail
- **Async Support**: Repository operations can be queued for background processing
- **Development Mode**: Proper handling of development vs production repository paths

## Bug Found and Fixed

During test development, we discovered and fixed a bug in `services.py` where `commit_code_changes()` was calling a non-existent method `_repository_manager.commit_code_changes()`. This was corrected to call `_repository_manager.commit_and_backup_all()`.

## Running the Tests

```bash
# Run all repository tests
pytest tests/test_repository_flow.py tests/test_repository_integration.py -v

# Run specific test categories
pytest tests/test_repository_flow.py -v                    # Unit tests
pytest tests/test_repository_integration.py -v            # Integration tests

# Run with coverage
pytest --cov=models.repository_manager --cov=services tests/test_repository_flow.py tests/test_repository_integration.py

# Run only fast tests (exclude slow timing tests)
pytest -m "not slow" tests/test_repository_flow.py tests/test_repository_integration.py
```

## Test Philosophy

These tests demonstrate that **testing the repository management flow is not only a good idea but essential** because:

1. **Core Functionality**: Repository management is central to the study's data collection
2. **Complex State Management**: Multiple branches, stages, and transition points create complex state
3. **Error Handling**: Network and Git failures must be handled gracefully to maintain study continuity
4. **Integration Points**: Repository operations span multiple layers (Flask routes, services, models)
5. **Data Integrity**: Proper commits and backups ensure no participant work is lost
6. **Bug Detection**: Tests helped identify and fix actual bugs in the codebase

The repository management system handles the most critical aspect of the study - preserving participant code changes - making comprehensive testing absolutely necessary.
