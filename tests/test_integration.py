"""
Integration tests for the coding study application.
These tests verify that different components work together correctly.
"""
import pytest
from unittest.mock import patch, Mock
import tempfile
import os
import json


class TestStudyFlowIntegration:
    """Integration tests for the complete study flow."""
    
    def test_participant_study_flow_stage_1(self, client):
        """Test complete participant flow for stage 1."""
        participant_id = "test-participant-001"
        
        with patch('app.get_participant_id', return_value=participant_id):
            with patch('app.get_study_stage', return_value=1):
                with patch('app.get_coding_condition', return_value='ai-assisted'):
                    with patch('app.should_log_route', return_value=True):
                        with patch('app.log_route_visit', return_value=True):
                            with patch('app.mark_route_as_logged'):
                                with patch.dict('os.environ', {
                                    'SURVEY_URL': 'https://example.com/survey',
                                    'UX_SURVEY_URL': 'https://example.com/ux-survey'
                                }):
                                    
                                    # 1. Visit home page
                                    response = client.get('/')
                                    assert response.status_code == 200
                                    assert participant_id.encode() in response.data
                                    
                                    # 2. Visit background questionnaire
                                    response = client.get('/background-questionnaire')
                                    assert response.status_code == 200
                                    assert b'https://example.com/survey' in response.data
                                    
                                    # 3. Visit tutorial
                                    response = client.get('/tutorial')
                                    assert response.status_code == 200
                                    assert b'Coding Tutorial' in response.data
    
    def test_participant_study_flow_stage_2(self, client):
        """Test participant flow for stage 2 (returning participant)."""
        participant_id = "test-participant-002"
        
        with patch('app.get_participant_id', return_value=participant_id):
            with patch('app.get_study_stage', return_value=2):
                with patch('app.get_coding_condition', return_value='human-only'):
                    with patch('app.should_log_route', return_value=True):
                        with patch('app.log_route_visit', return_value=True):
                            with patch('app.mark_route_as_logged'):
                                with patch('app.mark_stage_transition', return_value=True):
                                    
                                    # 1. Visit home page - should redirect to welcome back
                                    response = client.get('/')
                                    assert response.status_code == 302
                                    assert '/welcome-back' in response.location
                                    
                                    # 2. Visit tutorial - should redirect to welcome back
                                    response = client.get('/tutorial')
                                    assert response.status_code == 302
                                    assert '/welcome-back' in response.location
                                    
                                    # 3. Visit welcome back page
                                    response = client.get('/welcome-back')
                                    assert response.status_code == 200
                                    assert b'Welcome Back' in response.data
    
    def test_task_completion_flow(self, client):
        """Test task completion workflow."""
        with patch('app.get_participant_id', return_value='test-participant'):
            with patch('app.get_study_stage', return_value=1):
                with patch('app.get_coding_condition', return_value='ai-assisted'):
                    with patch('app.setup_repository_for_stage', return_value=True):
                        with patch('app.get_session_data', return_value={
                            'current_task': 1,
                            'completed_tasks': [],
                            'timer_start': None,
                            'timer_finished': False
                        }):
                            with patch('app.should_log_route', return_value=False):
                                with patch('app.get_tasks_for_stage', return_value=[
                                    {'id': 1, 'title': 'Test Task 1'},
                                    {'id': 2, 'title': 'Test Task 2'}
                                ]):
                                    with patch('app.update_session_data') as mock_update:
                                        with patch('app.log_route_visit', return_value=True):
                                            with patch('app.commit_code_changes', return_value=True):
                                                
                                                # 1. Visit task page
                                                response = client.get('/task')
                                                assert response.status_code == 200
                                                
                                                # 2. Complete task 1
                                                response = client.post('/complete-task', data={'task_id': '1'})
                                                assert response.status_code == 302
                                                
                                                # Verify session was updated
                                                mock_update.assert_called()
    
    def test_session_management_across_stages(self, client):
        """Test that session data is properly managed across different stages."""
        with patch('app.get_participant_id', return_value='test-participant'):
            
            # Test stage 1 session
            with patch('app.get_study_stage', return_value=1):
                with patch('app.get_session_data', return_value={
                    'current_task': 2,
                    'completed_tasks': [1],
                    'timer_start': 1234567890,
                    'timer_finished': False
                }) as mock_get_session:
                    
                    response = client.get('/get-timer-status')
                    assert response.status_code == 200
                    
                    # Verify session data was requested for stage 1
                    mock_get_session.assert_called()
            
            # Test stage 2 session (different data)
            with patch('app.get_study_stage', return_value=2):
                with patch('app.get_session_data', return_value={
                    'current_task': 1,
                    'completed_tasks': [],
                    'timer_start': None,
                    'timer_finished': False
                }) as mock_get_session_2:
                    
                    response = client.get('/get-timer-status')
                    assert response.status_code == 200
                    
                    # Verify session data was requested for stage 2
                    mock_get_session_2.assert_called()


class TestLoggingIntegration:
    """Integration tests for logging functionality."""
    
    def test_route_logging_integration(self, temp_dir):
        """Test that route logging works with session tracking."""
        from models.study_logger import StudyLogger, SessionTracker
        from models.github_service import GitHubService
        
        # Create mock GitHub service
        github_service = Mock(spec=GitHubService)
        logger = StudyLogger(github_service)
        
        # Test session tracking
        session = {}
        
        # First visit should need logging
        assert SessionTracker.should_log_route(session, 'home', 1) is True
        
        # Mark as logged
        SessionTracker.mark_route_as_logged(session, 'home', 1)
        
        # Second visit should not need logging
        assert SessionTracker.should_log_route(session, 'home', 1) is False
        
        # Different stage should still need logging
        assert SessionTracker.should_log_route(session, 'home', 2) is True
    
    def test_task_manager_integration(self):
        """Test task manager integration with session management."""
        from models.task_manager import TaskManager, SessionManager
        
        # Mock task data in correct format
        mock_tasks = {
            'stage1_tasks': [
                {'id': 1, 'title': 'Task 1'},
                {'id': 2, 'title': 'Task 2'}
            ],
            'stage2_tasks': [
                {'id': 3, 'title': 'Task 3'}
            ]
        }
        
        with patch('builtins.open'), patch('os.path.exists', return_value=True):
            with patch('json.load', return_value=mock_tasks):
                task_manager = TaskManager()
                
                # Test stage 1 tasks
                stage1_tasks = task_manager.get_tasks_for_stage(1)
                assert len(stage1_tasks) == 2
                
                # Test stage 2 tasks
                stage2_tasks = task_manager.get_tasks_for_stage(2)
                assert len(stage2_tasks) == 1
        
        # Test session management
        session = {}
        
        # Set up stage 1 session
        SessionManager.update_session_data(session, 1, current_task=2, completed_tasks=[1])
        stage1_data = SessionManager.get_session_data(session, 1)
        
        assert stage1_data['current_task'] == 2
        assert stage1_data['completed_tasks'] == [1]
        
        # Set up stage 2 session (should be independent)
        SessionManager.update_session_data(session, 2, current_task=1, completed_tasks=[])
        stage2_data = SessionManager.get_session_data(session, 2)
        
        assert stage2_data['current_task'] == 1
        assert stage2_data['completed_tasks'] == []
        
        # Stage 1 data should be unchanged
        stage1_data_check = SessionManager.get_session_data(session, 1)
        assert stage1_data_check['current_task'] == 2
        assert stage1_data_check['completed_tasks'] == [1]
