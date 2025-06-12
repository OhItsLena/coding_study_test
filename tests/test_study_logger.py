"""
Tests for study logger functionality.
"""
import pytest
from unittest.mock import patch, Mock, mock_open
import os
import tempfile
import json

from models.study_logger import StudyLogger, SessionTracker
from models.github_service import GitHubService


class TestStudyLogger:
    """Test cases for StudyLogger class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_github_service = Mock(spec=GitHubService)
        self.logger = StudyLogger(self.mock_github_service)
    
    def test_get_logs_directory_path_development(self):
        """Test getting logs directory path in development mode."""
        path = self.logger.get_logs_directory_path("test-participant", True)
        expected = os.path.join(os.getcwd(), "logs-test-participant")
        assert path == expected
    
    def test_get_logs_directory_path_production(self):
        """Test getting logs directory path in production mode."""
        path = self.logger.get_logs_directory_path("test-participant", False)
        expected = os.path.expanduser("~/workspace/logs-test-participant")
        assert path == expected
    
    @patch('models.study_logger.os.makedirs')
    @patch('models.study_logger.os.path.exists')
    @patch('models.study_logger.subprocess.run')
    def test_ensure_logging_repository_new_repo(self, mock_run, mock_exists, mock_makedirs):
        """Test ensuring logging repository when it doesn't exist."""
        # Mock that logs directory doesn't exist but .git directory also doesn't exist
        def exists_side_effect(path):
            if 'logs-test-participant' in path and '.git' not in path:
                return False  # logs directory doesn't exist
            elif '.git' in path:
                return False  # .git directory doesn't exist
            return True
            
        mock_exists.side_effect = exists_side_effect
        
        # Mock successful git commands
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
        
        with patch('builtins.open', mock_open()):
            with patch('models.study_logger.os.chdir'):
                result = self.logger.ensure_logging_repository(
                    "test-participant", True, "test-token", "test-org"
                )
        
        assert result is True
        mock_makedirs.assert_called_once()  # Should be called since directory doesn't exist
    
    @patch('models.study_logger.os.path.exists')
    @patch('models.study_logger.subprocess.run')  
    def test_ensure_logging_repository_existing_repo(self, mock_run, mock_exists):
        """Test ensuring logging repository when it already exists."""
        # Mock directory and .git exist
        mock_exists.return_value = True
        
        # Mock successful git commands
        mock_run.return_value = Mock(returncode=0, stdout="logging", stderr="")
        
        with patch('models.study_logger.os.chdir'):
            result = self.logger.ensure_logging_repository(
                "test-participant", True, "test-token", "test-org"
            )
        
        assert result is True
    
    @patch('models.study_logger.os.path.exists')
    @patch('models.study_logger.subprocess.run')
    def test_log_route_visit_first_time(self, mock_run, mock_exists):
        """Test logging route visit for the first time."""
        # Mock existing logs directory
        mock_exists.return_value = True
        
        # Mock successful git commands  
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
        
        # Mock file operations
        with patch('builtins.open', mock_open(read_data='{"visits": []}')):
            with patch('models.study_logger.os.chdir'):
                with patch.object(self.logger, 'ensure_logging_repository', return_value=True):
                    result = self.logger.log_route_visit(
                        "test-participant", "home", True, 1,
                        {"first_visit": True}, "test-token", "test-org"
                    )
        
        assert result is True
    
    @patch('models.study_logger.os.path.exists')  
    def test_log_route_visit_duplicate(self, mock_exists):
        """Test logging route visit when already logged."""
        # Mock existing logs with this route already logged
        existing_logs = {
            "visits": [
                {
                    "route": "home",
                    "study_stage": 1,
                    "participant_id": "test-participant"
                }
            ]
        }
        
        mock_exists.return_value = True
        
        with patch('builtins.open', mock_open(read_data=json.dumps(existing_logs))):
            with patch('models.study_logger.os.chdir'):
                with patch.object(self.logger, 'ensure_logging_repository', return_value=True):
                    result = self.logger.log_route_visit(
                        "test-participant", "home", True, 1
                    )
        
        assert result is True  # Should return True but skip actual logging
    
    def test_get_stage_transition_history_no_file(self):
        """Test getting stage transition history when file doesn't exist."""
        with patch('models.study_logger.os.path.exists', return_value=False):
            history = self.logger.get_stage_transition_history("test-participant", True)
            assert history == []
    
    def test_get_stage_transition_history_with_data(self):
        """Test getting stage transition history with existing data."""
        transition_data = {
            "transitions": [
                {
                    "from_stage": 1,
                    "to_stage": 2,
                    "timestamp": "2024-01-01T12:00:00"
                }
            ]
        }
        
        with patch('models.study_logger.os.path.exists', return_value=True):
            with patch('builtins.open', mock_open(read_data=json.dumps(transition_data))):
                history = self.logger.get_stage_transition_history("test-participant", True)
                
                assert len(history) == 1
                assert history[0]['from_stage'] == 1
                assert history[0]['to_stage'] == 2


class TestSessionTracker:
    """Test cases for SessionTracker class."""
    
    def test_should_log_route_first_time(self):
        """Test should_log_route for first time visit."""
        session = {}
        result = SessionTracker.should_log_route(session, "home", 1)
        assert result is True
    
    def test_should_log_route_already_logged(self):
        """Test should_log_route when route already logged."""
        session = {
            'logged_routes_stage1': ['home_stage1']
        }
        result = SessionTracker.should_log_route(session, "home", 1)
        assert result is False
    
    def test_mark_route_as_logged(self):
        """Test marking route as logged."""
        session = {}
        SessionTracker.mark_route_as_logged(session, "home", 1)
        
        assert 'logged_routes_stage1' in session
        assert 'home_stage1' in session['logged_routes_stage1']
    
    def test_mark_route_as_logged_existing_list(self):
        """Test marking route as logged with existing logged routes."""
        session = {
            'logged_routes_stage1': ['tutorial_stage1']
        }
        SessionTracker.mark_route_as_logged(session, "home", 1)
        
        assert len(session['logged_routes_stage1']) == 2
        assert 'tutorial_stage1' in session['logged_routes_stage1']
        assert 'home_stage1' in session['logged_routes_stage1']
    
    def test_stage_separation(self):
        """Test that different stages have separate tracking."""
        session = {}
        
        # Log route for stage 1
        SessionTracker.mark_route_as_logged(session, "home", 1)
        
        # Same route for stage 2 should still need logging
        result = SessionTracker.should_log_route(session, "home", 2)
        assert result is True
        
        # Mark for stage 2
        SessionTracker.mark_route_as_logged(session, "home", 2)
        
        # Now both should be marked
        assert SessionTracker.should_log_route(session, "home", 1) is False
        assert SessionTracker.should_log_route(session, "home", 2) is False
