"""
Test configuration and fixtures for the coding study Flask application tests.
"""
import pytest
import tempfile
import shutil
import os
from unittest.mock import Mock, patch

# Add project root to Python path
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app
from models.task_manager import TaskManager
from models.participant_manager import ParticipantManager
from models.azure_service import AzureMetadataService
from models.github_service import GitHubService
from models.repository_manager import RepositoryManager
from models.study_logger import StudyLogger


@pytest.fixture
def client():
    """Create a test client for the Flask application."""
    # Ensure we import app properly
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    import app as flask_app
    
    flask_app.app.config['TESTING'] = True
    flask_app.app.config['SECRET_KEY'] = 'test-secret-key'
    flask_app.app.config['WTF_CSRF_ENABLED'] = False
    
    with flask_app.app.test_client() as client:
        with flask_app.app.app_context():
            yield client


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def sample_participant_id():
    """Sample participant ID for testing."""
    return "test-participant-001"


@pytest.fixture
def sample_task_requirements():
    """Sample task requirements for testing."""
    return [
        {
            "id": 1,
            "title": "Test Task 1",
            "description": "First test task"
        },
        {
            "id": 2,
            "title": "Test Task 2", 
            "description": "Second test task"
        }
    ]


@pytest.fixture
def mock_github_service():
    """Mock GitHub service for testing."""
    service = Mock(spec=GitHubService)
    service.get_authenticated_repo_url.return_value = "https://token@github.com/org/repo.git"
    service.test_github_connectivity.return_value = True
    return service


@pytest.fixture
def mock_azure_service():
    """Mock Azure service for testing."""
    service = Mock(spec=AzureMetadataService)
    service.get_participant_id.return_value = "test-participant-001"
    service.get_study_stage.return_value = 1
    return service


@pytest.fixture
def mock_session():
    """Mock Flask session for testing."""
    return {}
