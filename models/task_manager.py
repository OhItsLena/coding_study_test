"""
Task management for the coding study Flask application.
Handles task requirements, session data, and task progression.
"""

import os
import json
import time
from typing import Dict, List, Any, Optional


class TaskManager:
    """
    Manages task requirements and session data for the coding study.
    """
    
    def __init__(self, task_requirements_file: str = "task_requirements.json"):
        """
        Initialize TaskManager with task requirements file.
        
        Args:
            task_requirements_file: Path to the JSON file containing task requirements
        """
        self.task_requirements_file = task_requirements_file
        self._task_requirements = None
    
    @property
    def task_requirements(self) -> Dict[str, List[Dict]]:
        """
        Load and cache task requirements from JSON file.
        
        Returns:
            Dictionary with stage1_tasks and stage2_tasks
        """
        if self._task_requirements is None:
            self._task_requirements = self._load_task_requirements()
        return self._task_requirements
    
    def _load_task_requirements(self) -> Dict[str, List[Dict]]:
        """
        Load task requirements from the JSON file.
        
        Returns:
            Dictionary with stage1_tasks and stage2_tasks
        """
        try:
            current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            json_path = os.path.join(current_dir, self.task_requirements_file)
            
            with open(json_path, 'r', encoding='utf-8') as file:
                data = json.load(file)
                return data
        except Exception as e:
            print(f"Error loading task requirements: {str(e)}")
            return {"stage1_tasks": [], "stage2_tasks": []}
    
    def get_tasks_for_stage(self, study_stage: int) -> List[Dict]:
        """
        Get the appropriate tasks based on the study stage.
        
        Args:
            study_stage: The study stage (1 or 2)
            
        Returns:
            List of tasks for the given stage
        """
        if study_stage == 1:
            return self.task_requirements.get('stage1_tasks', [])
        elif study_stage == 2:
            return self.task_requirements.get('stage2_tasks', [])
        else:
            return self.task_requirements.get('stage1_tasks', [])  # Default to stage 1


class SessionManager:
    """
    Manages session data specific to study stages.
    """
    
    @staticmethod
    def get_session_data(session: Dict, study_stage: int) -> Dict[str, Any]:
        """
        Get session data specific to the current study stage.
        
        Args:
            session: Flask session object
            study_stage: Current study stage (1 or 2)
            
        Returns:
            Dictionary with current_task, completed_tasks, and other stage data
        """
        stage_key = f'stage{study_stage}'
        return {
            'current_task': session.get(f'current_task_{stage_key}', 1),
            'completed_tasks': session.get(f'completed_tasks_{stage_key}', []),
            'stage_key': stage_key,
            'timer_start': session.get(f'timer_start_{stage_key}'),
            'timer_finished': session.get(f'timer_finished_{stage_key}', False)
        }
    
    @staticmethod
    def update_session_data(session: Dict, study_stage: int, 
                          current_task: Optional[int] = None,
                          completed_tasks: Optional[List[int]] = None,
                          timer_start: Optional[float] = None,
                          timer_finished: Optional[bool] = None) -> None:
        """
        Update session data specific to the current study stage.
        
        Args:
            session: Flask session object
            study_stage: Current study stage (1 or 2)
            current_task: Current task number to set
            completed_tasks: List of completed task IDs to set
            timer_start: Timer start timestamp to set
            timer_finished: Timer finished status to set
        """
        stage_key = f'stage{study_stage}'
        
        if current_task is not None:
            session[f'current_task_{stage_key}'] = current_task
        
        if completed_tasks is not None:
            session[f'completed_tasks_{stage_key}'] = completed_tasks
        
        if timer_start is not None:
            session[f'timer_start_{stage_key}'] = timer_start
        
        if timer_finished is not None:
            session[f'timer_finished_{stage_key}'] = timer_finished
    
    @staticmethod
    def calculate_timer_info(session_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate timer information based on session data.
        
        Args:
            session_data: Session data from get_session_data()
            
        Returns:
            Dictionary with elapsed time, remaining time, and status
        """
        timer_start = session_data.get('timer_start')
        
        if timer_start is None:
            return {'status': 'Not started'}
        
        elapsed = time.time() - timer_start
        remaining = max(0, 2400 - elapsed)  # 40 minutes = 2400 seconds
        
        return {
            'elapsed_seconds': elapsed,
            'elapsed_minutes': elapsed / 60,
            'remaining_seconds': remaining,
            'remaining_minutes': remaining / 60,
            'timer_start_timestamp': timer_start,
            'timer_start_readable': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(timer_start))
        }
