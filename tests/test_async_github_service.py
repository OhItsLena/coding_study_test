"""
Tests for the async GitHub service.
"""
import pytest
import time
import threading
from unittest.mock import Mock, patch
from models.async_github_service import AsyncGitHubService, GitHubOperation


class TestAsyncGitHubService:
    """Test cases for AsyncGitHubService class."""
    
    @pytest.fixture
    def mock_github_service(self):
        """Mock GitHub service for testing."""
        service = Mock()
        service.test_github_connectivity.return_value = True
        service.get_authenticated_repo_url.return_value = "https://token@github.com/org/repo.git"
        return service
    
    @pytest.fixture
    def mock_study_logger(self):
        """Mock study logger for testing."""
        logger = Mock()
        logger.log_route_visit.return_value = True
        logger.mark_stage_transition.return_value = True
        return logger
    
    @pytest.fixture
    def async_service(self, mock_github_service, mock_study_logger):
        """Create async service for testing."""
        service = AsyncGitHubService(mock_github_service, mock_study_logger)
        yield service
        service.stop_worker()
    
    def test_initialization(self, async_service):
        """Test that async service initializes correctly."""
        assert async_service.worker_thread is not None
        assert async_service.worker_thread.is_alive()
        assert async_service.operation_queue.qsize() == 0
        assert async_service.stats['total_operations'] == 0
    
    def test_queue_log_route_visit(self, async_service):
        """Test queuing a route visit logging operation."""
        # Stop worker to prevent immediate processing
        async_service.stop_worker()
        
        async_service.queue_log_route_visit(
            participant_id="test-participant",
            route_name="home",
            development_mode=True,
            study_stage=1,
            session_data={'test': 'data'},
            github_token="token",
            github_org="org"
        )
        
        assert async_service.get_queue_size() == 1
    
    def test_queue_commit_code_changes(self, async_service):
        """Test queuing a code commit operation."""
        # Stop worker to prevent immediate processing
        async_service.stop_worker()
        
        async_service.queue_commit_code_changes(
            participant_id="test-participant",
            study_stage=1,
            commit_message="Test commit",
            development_mode=True,
            github_token="token",
            github_org="org"
        )
        
        assert async_service.get_queue_size() == 1
    
    def test_queue_test_connectivity(self, async_service):
        """Test queuing a connectivity test."""
        # Stop worker to prevent immediate processing
        async_service.stop_worker()
        
        async_service.queue_test_connectivity(
            participant_id="test-participant",
            github_token="token",
            github_org="org"
        )
        
        assert async_service.get_queue_size() == 1
    
    def test_queue_mark_stage_transition(self, async_service):
        """Test queuing a stage transition."""
        # Stop worker to prevent immediate processing
        async_service.stop_worker()
        
        async_service.queue_mark_stage_transition(
            participant_id="test-participant",
            from_stage=1,
            to_stage=2,
            development_mode=True,
            github_token="token",
            github_org="org"
        )
        
        assert async_service.get_queue_size() == 1
    
    def test_operation_processing(self, async_service, mock_study_logger):
        """Test that operations are processed by the worker."""
        # Queue an operation
        async_service.queue_log_route_visit(
            participant_id="test-participant",
            route_name="home",
            development_mode=True,
            study_stage=1,
            github_token="token",
            github_org="org"
        )
        
        # Wait for processing
        async_service.wait_for_completion()
        
        # Check that the operation was processed
        assert async_service.get_queue_size() == 0
        assert async_service.stats['total_operations'] > 0
        mock_study_logger.log_route_visit.assert_called_once()
    
    def test_worker_restart(self, async_service):
        """Test stopping and restarting the worker."""
        original_thread = async_service.worker_thread
        
        # Stop the worker
        async_service.stop_worker()
        time.sleep(0.1)  # Give time for thread to stop
        assert not original_thread.is_alive()
        
        # Start a new worker
        async_service.start_worker()
        time.sleep(0.1)  # Give time for thread to start
        assert async_service.worker_thread is not None
        assert async_service.worker_thread.is_alive()
        assert async_service.worker_thread != original_thread
    
    def test_stats_collection(self, async_service):
        """Test that statistics are collected correctly."""
        initial_stats = async_service.get_stats()
        assert 'total_operations' in initial_stats
        assert 'successful_operations' in initial_stats
        assert 'failed_operations' in initial_stats
        assert 'queue_size' in initial_stats
        assert 'worker_alive' in initial_stats
        
        # Stop worker and queue an operation to test queue size
        async_service.stop_worker()
        async_service.queue_test_connectivity("test-participant", "token", "org")
        
        stats_with_queue = async_service.get_stats()
        assert stats_with_queue['queue_size'] == 1
    
    def test_retry_mechanism(self, async_service, mock_study_logger):
        """Test that failed operations are retried."""
        # Make the mock fail the first few times
        mock_study_logger.log_route_visit.side_effect = [Exception("Network error"), Exception("Network error"), True]
        
        # Queue an operation
        async_service.queue_log_route_visit(
            participant_id="test-participant",
            route_name="home",
            development_mode=True,
            study_stage=1,
            github_token="token",
            github_org="org"
        )
        
        # Wait for processing with retries
        async_service.wait_for_completion()
        
        # Should have been called 3 times (initial + 2 retries)
        assert mock_study_logger.log_route_visit.call_count == 3
        assert async_service.stats['successful_operations'] == 1


class TestGitHubOperation:
    """Test cases for GitHubOperation class."""
    
    def test_operation_creation(self):
        """Test creating a GitHub operation."""
        operation = GitHubOperation(
            operation_type="log_route_visit",
            participant_id="test-participant",
            route_name="home",
            study_stage=1
        )
        
        assert operation.operation_type == "log_route_visit"
        assert operation.participant_id == "test-participant"
        assert operation.kwargs['route_name'] == "home"
        assert operation.kwargs['study_stage'] == 1
        assert operation.retry_count == 0
        assert operation.max_retries == 3
        assert operation.timestamp is not None
