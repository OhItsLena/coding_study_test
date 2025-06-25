"""
Tests for Flask application routes and functionality.
"""
import pytest
from unittest.mock import patch, Mock
import sys
import os

# Add project root to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app


class TestFlaskRoutes:
    """Test cases for Flask application routes."""
    
    def test_home_route_stage_1(self, client):
        """Test home route for stage 1 participant."""
        with patch('app.get_participant_id', return_value='test-participant'):
            with patch('app.get_study_stage', return_value=1):
                with patch('app.should_log_route', return_value=True):
                    with patch('app.log_route_visit', return_value=True):
                        with patch('app.mark_route_as_logged'):
                            response = client.get('/')
                            
                            assert response.status_code == 200
                            assert b'test-participant' in response.data
    
    def test_home_route_stage_2_redirect(self, client):
        """Test home route redirects stage 2 participants to welcome back."""
        with patch('app.get_participant_id', return_value='test-participant'):
            with patch('app.get_study_stage', return_value=2):
                response = client.get('/')
                
                assert response.status_code == 302
                assert '/welcome-back' in response.location
    
    def test_clear_session_route(self, client):
        """Test session clearing functionality."""
        # Set some session data first
        with client.session_transaction() as sess:
            sess['test_key'] = 'test_value'
        
        response = client.get('/clear-session')
        assert response.status_code == 200
        
        # Check session was cleared
        with client.session_transaction() as sess:
            assert 'test_key' not in sess
    
    def test_debug_session_route_development(self, client):
        """Test debug session route in development mode."""
        with patch('app.DEVELOPMENT_MODE', True):
            with patch('app.get_participant_id', return_value='test-participant'):
                with patch('app.get_study_stage', return_value=1):
                    with patch('app.get_session_data', return_value={
                        'current_task': 1,
                        'completed_tasks': [],
                        'timer_start': None,
                        'timer_finished': False
                    }):
                        with patch('app.get_tasks_for_stage', return_value=[]):
                            response = client.get('/debug-session')
                            
                            assert response.status_code == 200
                            assert b'Development Session Debug' in response.data
    
    def test_debug_session_route_production_forbidden(self, client):
        """Test debug session route is forbidden in production."""
        with patch('app.DEVELOPMENT_MODE', False):
            response = client.get('/debug-session')
            assert response.status_code == 403
    
    def test_background_questionnaire_route(self, client):
        """Test background questionnaire route."""
        with patch('app.get_participant_id', return_value='test-participant'):
            with patch('app.get_study_stage', return_value=1):
                with patch('app.check_automatic_rerouting', return_value=None):
                    with patch('app.should_log_route', return_value=True):
                        with patch('app.log_route_visit', return_value=True):
                            with patch('app.mark_route_as_logged'):
                                with patch.dict('os.environ', {'SURVEY_URL': 'https://example.com/survey'}):
                                    with client.session_transaction() as sess:
                                        sess['consent_given'] = True
                                    response = client.get('/background-questionnaire')
                                    
                                    assert response.status_code == 200
                                    assert b'https://example.com/survey' in response.data
    
    def test_tutorial_route_stage_1(self, client):
        """Test tutorial route for stage 1."""
        with patch('app.get_participant_id', return_value='test-participant'):
            with patch('app.get_study_stage', return_value=1):
                with patch('app.should_log_route', return_value=True):
                    with patch('app.log_route_visit', return_value=True):
                        with patch('app.mark_route_as_logged'):
                            with patch('app.get_coding_condition', return_value='ai-assisted'):
                                response = client.get('/tutorial')
                                
                                assert response.status_code == 200
                                assert b'Coding Tutorial' in response.data
                                assert b'test-participant' in response.data
    
    def test_tutorial_route_stage_2_redirect(self, client):
        """Test tutorial route redirects stage 2 participants."""
        with patch('app.get_participant_id', return_value='test-participant'):
            with patch('app.get_study_stage', return_value=2):
                response = client.get('/tutorial')
                
                assert response.status_code == 302
                assert '/welcome-back' in response.location
    
    def test_welcome_back_route(self, client):
        """Test welcome back route."""
        with patch('app.get_participant_id', return_value='test-participant'):
            with patch('app.get_study_stage', return_value=2):
                with patch('app.get_coding_condition', return_value='vibe'):
                    with patch('app.should_log_route', return_value=True):
                        with patch('app.log_route_visit', return_value=True):
                            with patch('app.mark_route_as_logged'):
                                with patch('app.mark_stage_transition', return_value=True):
                                    response = client.get('/welcome-back')
                                    
                                    assert response.status_code == 200
                                    assert b'Welcome Back' in response.data
                                    assert b'test-participant' in response.data
                                    assert b'Study Session 2' in response.data
    
    def test_task_route_basic(self, client):
        """Test basic task route functionality."""
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
                                    {'id': 1, 'title': 'Test Task', 'description': 'Test'}
                                ]):
                                    response = client.get('/task')
                                    
                                    assert response.status_code == 200
                                    assert b'Test Task' in response.data
    
    def test_complete_task_post(self, client):
        """Test task completion POST request."""
        with patch('app.get_participant_id', return_value='test-participant'):
            with patch('app.get_study_stage', return_value=1):
                with patch('app.get_session_data', return_value={
                    'current_task': 1,
                    'completed_tasks': [],
                    'timer_start': 1234567890,
                    'timer_finished': False
                }):
                    with patch('app.get_tasks_for_stage', return_value=[
                        {'id': 1, 'title': 'Test Task'}
                    ]):
                        with patch('app.update_session_data'):
                            with patch('app.log_route_visit', return_value=True):
                                with patch('app.commit_code_changes', return_value=True):
                                    response = client.post('/complete-task', data={'task_id': '1'})
                                    
                                    assert response.status_code == 302  # Redirect to task page
    
    def test_ux_questionnaire_route(self, client):
        """Test UX questionnaire route."""
        with patch('app.get_participant_id', return_value='test-participant'):
            with patch('app.get_study_stage', return_value=1):
                with patch('app.should_log_route', return_value=True):
                    with patch('app.get_session_data', return_value={
                        'current_task': 1,
                        'completed_tasks': [],
                        'timer_start': None,
                        'timer_finished': False
                    }):
                        with patch('app.log_route_visit', return_value=True):
                            with patch('app.mark_route_as_logged'):
                                with patch('app.commit_code_changes', return_value=True):
                                    with patch.dict('os.environ', {'UX_SURVEY_URL': 'https://example.com/ux-survey'}):
                                        response = client.get('/ux-questionnaire')
                                        
                                        assert response.status_code == 200
                                        assert b'https://example.com/ux-survey' in response.data
    
    def test_timer_status_route(self, client):
        """Test timer status API endpoint."""
        with patch('app.get_participant_id', return_value='test-participant'):
            with patch('app.get_study_stage', return_value=1):
                with patch('app.get_session_data', return_value={
                    'current_task': 1,
                    'completed_tasks': [1],
                    'timer_start': 1234567890,
                    'timer_finished': False
                }):
                    with patch('time.time', return_value=1234567900):  # 10 seconds later
                        response = client.get('/get-timer-status')
                        
                        assert response.status_code == 200
                        json_data = response.get_json()
                        assert 'remaining_time' in json_data
                        assert 'timer_finished' in json_data 
                        assert 'timer_started' in json_data
                        assert json_data['timer_started'] is True
                        assert json_data['remaining_time'] == 2390  # 2400 - 10

    def test_goodbye_route(self, client):
        """Test goodbye page route."""
        with patch('app.get_participant_id', return_value='test-participant'):
            with patch('app.get_study_stage', return_value=1):
                with patch('app.get_coding_condition', return_value='vibe'):
                    with patch('app.should_log_route', return_value=True):
                        with patch('app.get_session_data', return_value={
                            'current_task': 1,
                            'completed_tasks': [1, 2, 3],
                            'timer_start': None,
                            'timer_finished': True
                        }):
                            with patch('app.log_route_visit', return_value=True):
                                with patch('app.mark_route_as_logged'):
                                    response = client.get('/goodbye')
                                    
                                    assert response.status_code == 200
                                    assert b'Study Session Complete' in response.data
                                    assert b'test-participant' in response.data
                                    assert b'Stage 1 Complete' in response.data
                                    assert b'vibe' in response.data

    def test_goodbye_route_stage2(self, client):
        """Test goodbye page route for stage 2."""
        with patch('app.get_participant_id', return_value='test-participant'):
            with patch('app.get_study_stage', return_value=2):
                with patch('app.get_coding_condition', return_value='traditional'):
                    with patch('app.should_log_route', return_value=True):
                        with patch('app.get_session_data', return_value={
                            'current_task': 1,
                            'completed_tasks': [1, 2, 3],
                            'timer_start': None,
                            'timer_finished': True
                        }):
                            with patch('app.log_route_visit', return_value=True):
                                with patch('app.mark_route_as_logged'):
                                    response = client.get('/goodbye')
                                    
                                    assert response.status_code == 200
                                    assert b'Study Session Complete' in response.data
                                    assert b'test-participant' in response.data
                                    assert b'Stage 2 Complete' in response.data
                                    assert b'traditional' in response.data
