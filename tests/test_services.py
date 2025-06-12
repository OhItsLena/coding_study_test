"""
Tests for the services module facade.
"""
import pytest
from unittest.mock import patch, Mock

import services


class TestServicesTaskManagement:
    """Test cases for task management functions in services."""
    
    @patch('services._task_manager')
    def test_load_task_requirements(self, mock_task_manager):
        """Test loading task requirements."""
        mock_task_manager.task_requirements = [{'id': 1, 'title': 'Test Task'}]
        
        result = services.load_task_requirements()
        assert result == [{'id': 1, 'title': 'Test Task'}]
    
    @patch('services._task_manager')
    def test_get_tasks_for_stage(self, mock_task_manager):
        """Test getting tasks for a specific stage."""
        expected_tasks = [{'id': 1, 'title': 'Stage 1 Task'}]
        mock_task_manager.get_tasks_for_stage.return_value = expected_tasks
        
        result = services.get_tasks_for_stage(1)
        assert result == expected_tasks
        mock_task_manager.get_tasks_for_stage.assert_called_once_with(1)
    
    @patch('services.SessionManager')
    def test_get_session_data(self, mock_session_manager):
        """Test getting session data."""
        expected_data = {'current_task': 1, 'completed_tasks': []}
        mock_session_manager.get_session_data.return_value = expected_data
        
        session = {'test': 'data'}
        result = services.get_session_data(session, 1)
        
        assert result == expected_data
        mock_session_manager.get_session_data.assert_called_once_with(session, 1)
    
    @patch('services.SessionManager')
    def test_update_session_data(self, mock_session_manager):
        """Test updating session data."""
        session = {'test': 'data'}
        
        services.update_session_data(
            session, 1, current_task=2, completed_tasks=[1], 
            timer_start=1234567890, timer_finished=False
        )
        
        mock_session_manager.update_session_data.assert_called_once_with(
            session, 1, 2, [1], 1234567890, False
        )


class TestServicesParticipantManagement:
    """Test cases for participant management functions in services."""
    
    @patch('services._participant_manager')
    def test_get_coding_condition(self, mock_participant_manager):
        """Test getting coding condition."""
        mock_participant_manager.get_coding_condition.return_value = 'ai-assisted'
        
        result = services.get_coding_condition('test-participant-001')
        assert result == 'ai-assisted'
        mock_participant_manager.get_coding_condition.assert_called_once_with('test-participant-001')


class TestServicesAzureService:
    """Test cases for Azure service functions in services."""
    
    @patch('services._azure_service')
    def test_get_study_stage(self, mock_azure_service):
        """Test getting study stage."""
        mock_azure_service.get_study_stage.return_value = 2
        
        result = services.get_study_stage('test-participant', False, 1)
        assert result == 2
        mock_azure_service.get_study_stage.assert_called_once_with('test-participant', False, 1)
    
    @patch('services._azure_service')
    def test_get_participant_id(self, mock_azure_service):
        """Test getting participant ID."""
        mock_azure_service.get_participant_id.return_value = 'prod-participant-123'
        
        result = services.get_participant_id(False, 'dev-fallback')
        assert result == 'prod-participant-123'
        mock_azure_service.get_participant_id.assert_called_once_with(False, 'dev-fallback')


class TestServicesGitHubService:
    """Test cases for GitHub service functions in services."""
    
    @patch('services._github_service')
    def test_get_authenticated_repo_url(self, mock_github_service):
        """Test getting authenticated repository URL."""
        expected_url = 'https://token@github.com/org/repo.git'
        mock_github_service.get_authenticated_repo_url.return_value = expected_url
        
        result = services.get_authenticated_repo_url('repo', 'token', 'org')
        assert result == expected_url
        mock_github_service.get_authenticated_repo_url.assert_called_once_with('repo', 'token', 'org')
    
    @patch('services._github_service')
    def test_test_github_connectivity(self, mock_github_service):
        """Test GitHub connectivity testing."""
        mock_github_service.test_github_connectivity.return_value = True
        
        result = services.test_github_connectivity('participant', 'token', 'org')
        assert result is True
        mock_github_service.test_github_connectivity.assert_called_once_with('participant', 'token', 'org')


class TestServicesRepositoryManagement:
    """Test cases for repository management functions in services."""
    
    @patch('services._repository_manager')
    def test_get_repository_path(self, mock_repository_manager):
        """Test getting repository path."""
        expected_path = '/home/test/workspace/study-participant'
        mock_repository_manager.get_repository_path.return_value = expected_path
        
        result = services.get_repository_path('participant', False)
        assert result == expected_path
        mock_repository_manager.get_repository_path.assert_called_once_with('participant', False)
    
    @patch('services._repository_manager')
    def test_check_and_clone_repository(self, mock_repository_manager):
        """Test checking and cloning repository."""
        mock_repository_manager.check_and_clone_repository.return_value = True
        
        result = services.check_and_clone_repository('participant', True, 'token', 'org')
        assert result is True
        mock_repository_manager.check_and_clone_repository.assert_called_once_with(
            'participant', True, 'token', 'org'
        )
    
    @patch('services._repository_manager')
    def test_commit_code_changes(self, mock_repository_manager):
        """Test committing code changes."""
        mock_repository_manager.commit_code_changes.return_value = True
        
        # Test synchronous mode
        result = services.commit_code_changes(
            'participant', 1, 'Test commit', True, 'token', 'org', async_mode=False
        )
        assert result is True
        mock_repository_manager.commit_code_changes.assert_called_once_with(
            'participant', 1, 'Test commit', True, 'token', 'org'
        )
    
    def test_commit_code_changes_async(self):
        """Test committing code changes in async mode."""
        # Test async mode - should return True immediately
        result = services.commit_code_changes(
            'participant', 1, 'Test commit', True, 'token', 'org', async_mode=True
        )
        assert result is True  # Returns immediately in async mode


class TestServicesLogging:
    """Test cases for logging functions in services."""
    
    @patch('services._study_logger')
    def test_get_logs_directory_path(self, mock_study_logger):
        """Test getting logs directory path."""
        expected_path = '/logs/test-participant'
        mock_study_logger.get_logs_directory_path.return_value = expected_path
        
        result = services.get_logs_directory_path('test-participant', True)
        assert result == expected_path
        mock_study_logger.get_logs_directory_path.assert_called_once_with('test-participant', True)
    
    @patch('services._study_logger')
    def test_log_route_visit(self, mock_study_logger):
        """Test logging route visit."""
        mock_study_logger.log_route_visit.return_value = True
        
        # Test synchronous mode
        result = services.log_route_visit(
            'participant', 'home', True, 1, 
            {'first_visit': True}, 'token', 'org', async_mode=False
        )
        assert result is True
        mock_study_logger.log_route_visit.assert_called_once_with(
            'participant', 'home', True, 1, {'first_visit': True}, 'token', 'org'
        )
    
    def test_log_route_visit_async(self):
        """Test logging route visit in async mode."""
        # Test async mode - should return True immediately
        result = services.log_route_visit(
            'participant', 'home', True, 1, 
            {'first_visit': True}, 'token', 'org', async_mode=True
        )
        assert result is True  # Returns immediately in async mode
    
    @patch('services._study_logger')
    def test_mark_stage_transition(self, mock_study_logger):
        """Test marking stage transition."""
        mock_study_logger.mark_stage_transition.return_value = True
        
        # Test synchronous mode
        result = services.mark_stage_transition(
            'participant', 1, 2, True, 'token', 'org', async_mode=False
        )
        assert result is True
        mock_study_logger.mark_stage_transition.assert_called_once_with(
            'participant', 1, 2, True, 'token', 'org'
        )
    
    def test_mark_stage_transition_async(self):
        """Test marking stage transition in async mode."""
        # Test async mode - should return True immediately
        result = services.mark_stage_transition(
            'participant', 1, 2, True, 'token', 'org', async_mode=True
        )
        assert result is True  # Returns immediately in async mode


class TestServicesSessionTracking:
    """Test cases for session tracking functions in services."""
    
    @patch('services._session_tracker')
    def test_should_log_route(self, mock_session_tracker):
        """Test checking if route should be logged."""
        mock_session_tracker.should_log_route.return_value = True
        
        session = {'test': 'data'}
        result = services.should_log_route(session, 'home', 1)
        
        assert result is True
        mock_session_tracker.should_log_route.assert_called_once_with(session, 'home', 1)
    
    @patch('services._session_tracker')
    def test_mark_route_as_logged(self, mock_session_tracker):
        """Test marking route as logged."""
        session = {'test': 'data'}
        
        services.mark_route_as_logged(session, 'home', 1)
        mock_session_tracker.mark_route_as_logged.assert_called_once_with(session, 'home', 1)
