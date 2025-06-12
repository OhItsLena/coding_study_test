"""
Tests for task management functionality.
"""
import pytest
from unittest.mock import patch, mock_open
import json

from models.task_manager import TaskManager, SessionManager


class TestTaskManager:
    """Test cases for TaskManager class."""
    
    def test_load_task_requirements_success(self):
        """Test successful loading of task requirements."""
        mock_data = {
            "stage1_tasks": [
                {"id": 1, "title": "Test Task 1", "description": "First task"}
            ],
            "stage2_tasks": [
                {"id": 2, "title": "Test Task 2", "description": "Second task"}
            ]
        }
        
        with patch('builtins.open', mock_open(read_data=json.dumps(mock_data))):
            manager = TaskManager()
            assert len(manager.task_requirements['stage1_tasks']) == 1
            assert len(manager.task_requirements['stage2_tasks']) == 1
            assert manager.task_requirements['stage1_tasks'][0]['title'] == "Test Task 1"
    
    def test_load_task_requirements_file_not_found(self):
        """Test handling when task requirements file doesn't exist."""
        with patch('builtins.open', side_effect=FileNotFoundError):
            manager = TaskManager()
            assert manager.task_requirements == {"stage1_tasks": [], "stage2_tasks": []}
    
    def test_get_tasks_for_stage_1(self):
        """Test getting tasks for stage 1."""
        mock_data = {
            "stage1_tasks": [
                {"id": 1, "title": "Task 1"},
                {"id": 2, "title": "Task 2"}
            ],
            "stage2_tasks": [
                {"id": 3, "title": "Task 3"}
            ]
        }
        
        with patch('builtins.open', mock_open(read_data=json.dumps(mock_data))):
            manager = TaskManager()
            stage1_tasks = manager.get_tasks_for_stage(1)
            assert len(stage1_tasks) == 2
            assert stage1_tasks[0]['title'] == "Task 1"
    
    def test_get_tasks_for_stage_2(self):
        """Test getting tasks for stage 2."""
        mock_data = {
            "stage1_tasks": [
                {"id": 1, "title": "Task 1"}
            ],
            "stage2_tasks": [
                {"id": 2, "title": "Task 2"},
                {"id": 3, "title": "Task 3"}
            ]
        }
        
        with patch('builtins.open', mock_open(read_data=json.dumps(mock_data))):
            manager = TaskManager()
            stage2_tasks = manager.get_tasks_for_stage(2)
            assert len(stage2_tasks) == 2
            assert stage2_tasks[0]['title'] == "Task 2"


class TestSessionManager:
    """Test cases for SessionManager class."""
    
    def test_get_session_data_default(self, mock_session):
        """Test getting default session data."""
        data = SessionManager.get_session_data(mock_session, 1)
        
        assert data['current_task'] == 1
        assert data['completed_tasks'] == []
        assert data['timer_start'] is None
        assert data['timer_finished'] is False
        assert data['stage_key'] == 'stage1'
    
    def test_get_session_data_existing(self):
        """Test getting existing session data."""
        session = {
            'current_task_stage1': 3,
            'completed_tasks_stage1': [1, 2],
            'timer_start_stage1': 1234567890,
            'timer_finished_stage1': True
        }
        
        data = SessionManager.get_session_data(session, 1)
        
        assert data['current_task'] == 3
        assert data['completed_tasks'] == [1, 2]
        assert data['timer_start'] == 1234567890
        assert data['timer_finished'] is True
    
    def test_update_session_data(self, mock_session):
        """Test updating session data."""
        SessionManager.update_session_data(
            mock_session, 1, 
            current_task=2,
            completed_tasks=[1],
            timer_start=1234567890,
            timer_finished=False
        )
        
        assert mock_session['current_task_stage1'] == 2
        assert mock_session['completed_tasks_stage1'] == [1]
        assert mock_session['timer_start_stage1'] == 1234567890
        assert mock_session['timer_finished_stage1'] is False
    
    def test_session_data_stage_separation(self):
        """Test that stage 1 and stage 2 session data are kept separate."""
        session = {}
        
        # Set stage 1 data
        SessionManager.update_session_data(session, 1, current_task=2, completed_tasks=[1])
        # Set stage 2 data  
        SessionManager.update_session_data(session, 2, current_task=1, completed_tasks=[])
        
        stage1_data = SessionManager.get_session_data(session, 1)
        stage2_data = SessionManager.get_session_data(session, 2)
        
        assert stage1_data['current_task'] == 2
        assert stage1_data['completed_tasks'] == [1]
        assert stage2_data['current_task'] == 1
        assert stage2_data['completed_tasks'] == []
    
    def test_calculate_timer_info_not_started(self):
        """Test timer info calculation when timer not started."""
        session_data = {'timer_start': None}
        
        timer_info = SessionManager.calculate_timer_info(session_data)
        assert timer_info['status'] == 'Not started'
    
    @patch('time.time')
    def test_calculate_timer_info_running(self, mock_time):
        """Test timer info calculation when timer is running."""
        # Mock current time to be 10 seconds after start
        mock_time.return_value = 1234567900
        
        session_data = {'timer_start': 1234567890}  # Started 10 seconds ago
        
        timer_info = SessionManager.calculate_timer_info(session_data)
        
        assert timer_info['elapsed_seconds'] == 10
        assert timer_info['remaining_seconds'] == 2390  # 2400 - 10
        assert timer_info['elapsed_minutes'] == pytest.approx(10/60, rel=1e-3)
