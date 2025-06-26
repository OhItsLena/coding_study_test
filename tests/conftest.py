"""
Pytest configuration and shared fixtures for the coding study test suite.
"""

import os
import pytest
import tempfile
import shutil
from unittest.mock import Mock, patch

# Set up test environment variables
os.environ['DEVELOPMENT_MODE'] = 'true'
os.environ['DEV_PARTICIPANT_ID'] = 'test-participant'
os.environ['DEV_STAGE'] = '1'
os.environ['SURVEY_URL'] = 'https://example.com/test-survey'
os.environ['UX_SURVEY_URL'] = 'https://example.com/test-ux-survey'
os.environ['GITHUB_ORG'] = 'test-org'
os.environ['SECRET_KEY'] = 'test-secret-key'


@pytest.fixture(scope="session")
def temp_workspace():
    """Create a temporary workspace directory for the entire test session."""
    temp_dir = tempfile.mkdtemp(prefix="coding_study_workspace_")
    yield temp_dir
    # Cleanup
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)


@pytest.fixture
def mock_environment():
    """Mock environment variables for testing."""
    with patch.dict(os.environ, {
        'DEVELOPMENT_MODE': 'true',
        'DEV_PARTICIPANT_ID': 'test-participant',
        'DEV_STAGE': '1',
        'GITHUB_TOKEN': 'test-token',
        'GITHUB_ORG': 'test-org',
        'SECRET_KEY': 'test-secret-key',
        'ASYNC_GITHUB_MODE': 'false'  # Use sync mode for testing by default
    }):
        yield


@pytest.fixture
def test_participant_id():
    """Standard test participant ID."""
    return "test-participant-001"


@pytest.fixture
def test_github_config():
    """Standard GitHub configuration for tests."""
    return {
        'token': 'test-github-token',
        'org': 'test-org'
    }


@pytest.fixture(autouse=True)
def clean_session():
    """Ensure clean session state for each test."""
    # This fixture automatically runs before each test
    # Import here to avoid circular imports
    try:
        from flask import session
        session.clear()
    except (ImportError, RuntimeError):
        # Not in Flask context, skip
        pass
    yield
    # Cleanup after test
    try:
        from flask import session
        session.clear()
    except (ImportError, RuntimeError):
        pass


def pytest_configure(config):
    """Pytest configuration hook."""
    # Add custom markers
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests"
    )
    config.addinivalue_line(
        "markers", "repository: marks tests related to repository management"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test items during collection."""
    # Add markers based on test file names
    for item in items:
        if "repository" in item.nodeid:
            item.add_marker(pytest.mark.repository)
        if "integration" in item.nodeid:
            item.add_marker(pytest.mark.integration)
        elif "test_" in item.nodeid and not any(marker.name == "integration" for marker in item.iter_markers()):
            item.add_marker(pytest.mark.unit)
