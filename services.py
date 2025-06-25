"""
Service facade for the coding study Flask application.
This module provides a simplified interface to the new object-oriented models.
"""

from models.task_manager import TaskManager, SessionManager
from models.participant_manager import ParticipantManager
from models.azure_service import AzureMetadataService
from models.github_service import GitHubService
from models.repository_manager import RepositoryManager, VSCodeManager
from models.study_logger import StudyLogger, SessionTracker
from models.async_github_service import AsyncGitHubService

# Initialize services and managers
_task_manager = TaskManager()
_participant_manager = ParticipantManager()
_azure_service = AzureMetadataService()
_github_service = GitHubService()
_repository_manager = RepositoryManager(_github_service)
_vscode_manager = VSCodeManager(_repository_manager)
_study_logger = StudyLogger(_github_service)
_session_tracker = SessionTracker()

# Initialize async GitHub service
_async_github_service = AsyncGitHubService(_github_service, _study_logger)


# Task Management Functions
def load_task_requirements():
    """Load task requirements from the JSON file."""
    return _task_manager.task_requirements


def load_tutorials():
    """Load tutorials from the JSON file."""
    import json
    import os
    
    try:
        tutorials_file = os.path.join(os.path.dirname(__file__), 'tutorials.json')
        with open(tutorials_file, 'r', encoding='utf-8') as f:
            tutorials_data = json.load(f)
        return tutorials_data.get('tutorials', [])
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error loading tutorials: {e}")
        return []


def get_tutorial_by_condition(coding_condition, tutorials=None):
    """Get the tutorial data for a specific coding condition."""
    if tutorials is None:
        tutorials = load_tutorials()
    
    for tutorial in tutorials:
        if tutorial.get('id') == coding_condition:
            return tutorial
    
    # Return None if no matching tutorial found
    return None


def get_tasks_for_stage(study_stage, task_requirements=None):
    """Get the appropriate tasks based on the study stage."""
    return _task_manager.get_tasks_for_stage(study_stage)


def get_session_data(session, study_stage):
    """Get session data specific to the current study stage."""
    return SessionManager.get_session_data(session, study_stage)


def update_session_data(session, study_stage, current_task=None, completed_tasks=None, 
                       timer_start=None, timer_finished=None):
    """Update session data specific to the current study stage."""
    return SessionManager.update_session_data(
        session, study_stage, current_task, completed_tasks, timer_start, timer_finished
    )


# Participant Management Functions
def get_coding_condition(participant_id, development_mode=False, dev_coding_condition="vibe"):
    """Determine the coding condition from Azure VM tags."""
    return _participant_manager.get_coding_condition(participant_id, development_mode, dev_coding_condition)


# Azure Service Functions
def get_study_stage(participant_id, development_mode, dev_stage=1):
    """Determine if the participant is in stage 1 or stage 2 of the study."""
    return _azure_service.get_study_stage(participant_id, development_mode, dev_stage)


def get_participant_id(development_mode, dev_participant_id):
    """Get the participant_id from Azure VM tags."""
    return _azure_service.get_participant_id(development_mode, dev_participant_id)


# GitHub Service Functions
def get_authenticated_repo_url(repo_name, github_token, github_org):
    """Construct the authenticated GitHub repository URL."""
    return _github_service.get_authenticated_repo_url(repo_name, github_token, github_org)


def test_github_connectivity(participant_id, github_token, github_org):
    """Test GitHub connectivity and authentication."""
    return _github_service.test_github_connectivity(participant_id, github_token, github_org)


# Repository Management Functions
def get_repository_path(participant_id, development_mode):
    """Get the path to the participant's repository."""
    return _repository_manager.get_repository_path(participant_id, development_mode)


def check_and_clone_repository(participant_id, development_mode, github_token, github_org):
    """Check if the GitHub repository exists and clone if needed."""
    return _repository_manager.check_and_clone_repository(
        participant_id, development_mode, github_token, github_org
    )


def setup_repository_for_stage(participant_id, study_stage, development_mode, github_token, github_org):
    """Set up the repository for a specific study stage."""
    return _repository_manager.setup_repository_for_stage(
        participant_id, study_stage, development_mode, github_token, github_org
    )


def commit_code_changes(participant_id, study_stage, commit_message, development_mode, github_token, github_org, async_mode=True):
    """Commit any changes in the participant's repository."""
    if async_mode:
        # Queue the operation for background processing
        _async_github_service.queue_commit_code_changes(
            participant_id, study_stage, commit_message, development_mode, github_token, github_org
        )
        return True  # Return immediately
    else:
        # Synchronous processing
        return _repository_manager.commit_code_changes(
            participant_id, study_stage, commit_message, development_mode, github_token, github_org
        )


def push_code_changes(participant_id, study_stage, development_mode, github_token, github_org):
    """Push committed changes to the remote repository."""
    return _repository_manager.push_code_changes(
        participant_id, study_stage, development_mode, github_token, github_org
    )


def ensure_git_config(repo_path, participant_id):
    """Ensure git config is set up for commits in the repository."""
    return _repository_manager.ensure_git_config(repo_path, participant_id)


def ensure_stage_branch(repo_path, study_stage):
    """Ensure the correct branch exists and is checked out for the given study stage."""
    return _repository_manager.ensure_stage_branch(repo_path, study_stage)


# VS Code Management Functions
def open_vscode_with_repository(participant_id, development_mode, study_stage=None):
    """Open VS Code with the participant's cloned repository."""
    return _vscode_manager.open_vscode_with_repository(participant_id, development_mode, study_stage)


# Tutorial Management Functions
def setup_tutorial_branch(participant_id, development_mode, github_token, github_org):
    """Set up tutorial branch and open VS Code with tutorial workspace."""
    return _repository_manager.setup_tutorial_branch(participant_id, development_mode, github_token, github_org)


def push_tutorial_code(participant_id, development_mode, github_token, github_org, async_mode=True):
    """Push tutorial code to the tutorial branch when leaving tutorial."""
    if async_mode:
        # Queue the operation for background processing
        _async_github_service.queue_push_tutorial_code(
            participant_id, development_mode, github_token, github_org
        )
        return True  # Return immediately
    else:
        # Synchronous processing
        return _repository_manager.push_tutorial_code(
            participant_id, development_mode, github_token, github_org
        )


def open_vscode_with_tutorial(participant_id, development_mode):
    """Open VS Code with the tutorial branch workspace."""
    return _vscode_manager.open_vscode_with_tutorial(participant_id, development_mode)


# Logging Functions
def get_logs_directory_path(participant_id, development_mode):
    """Get the path to the logs directory."""
    return _study_logger.get_logs_directory_path(participant_id, development_mode)


def ensure_logging_repository(participant_id, development_mode, github_token, github_org):
    """Ensure the logging repository exists and is set up."""
    return _study_logger.ensure_logging_repository(
        participant_id, development_mode, github_token, github_org
    )


def log_route_visit(participant_id, route_name, development_mode, study_stage, 
                   session_data=None, github_token=None, github_org=None, async_mode=True):
    """Log a route visit with timestamp and relevant context."""
    if async_mode:
        # Queue the operation for background processing
        _async_github_service.queue_log_route_visit(
            participant_id, route_name, development_mode, study_stage,
            session_data, github_token, github_org
        )
        return True  # Return immediately
    else:
        # Synchronous processing
        return _study_logger.log_route_visit(
            participant_id, route_name, development_mode, study_stage, 
            session_data, github_token, github_org
        )


def push_logs_to_remote(participant_id, development_mode, github_token, github_org):
    """Push logs to remote repository on the logging branch."""
    return _study_logger.push_logs_to_remote(participant_id, development_mode, github_token, github_org)


def mark_stage_transition(participant_id, from_stage, to_stage, development_mode, 
                         github_token=None, github_org=None, async_mode=True):
    """Mark a stage transition in the logs for explicit tracking."""
    if async_mode:
        # Queue the operation for background processing
        _async_github_service.queue_mark_stage_transition(
            participant_id, from_stage, to_stage, development_mode, github_token, github_org
        )
        return True  # Return immediately
    else:
        # Synchronous processing
        return _study_logger.mark_stage_transition(
            participant_id, from_stage, to_stage, development_mode, github_token, github_org
        )


def get_stage_transition_history(participant_id, development_mode):
    """Get the stage transition history for a participant."""
    return _study_logger.get_stage_transition_history(participant_id, development_mode)


def save_vscode_workspace_storage(participant_id, study_stage, development_mode, 
                                github_token=None, github_org=None):
    """Save VS Code workspace storage for a participant at the end of a coding stage."""
    return _study_logger.save_vscode_workspace_storage(
        participant_id, study_stage, development_mode, github_token, github_org
    )


def save_vscode_workspace_storage_async(participant_id, study_stage, development_mode, 
                                      github_token=None, github_org=None):
    """Save VS Code workspace storage asynchronously."""
    _async_github_service.queue_save_vscode_workspace_storage(
        participant_id, study_stage, development_mode, github_token, github_org
    )
    return True  # Return immediately


def get_vscode_workspace_storage_path():
    """Get the platform-specific VS Code workspace storage path."""
    return _study_logger.get_vscode_workspace_storage_path()


# Session Tracking Functions
def should_log_route(session, route_name, study_stage):
    """Check if a route should be logged."""
    return _session_tracker.should_log_route(session, route_name, study_stage)


def mark_route_as_logged(session, route_name, study_stage):
    """Mark a route as having been logged in the session."""
    return _session_tracker.mark_route_as_logged(session, route_name, study_stage)


# Screen Recording Functions
def start_session_recording(participant_id, study_stage, development_mode):
    """Start screen recording for the study session."""
    return _study_logger.start_session_recording(participant_id, study_stage, development_mode)


def stop_session_recording():
    """Stop the current session recording."""
    return _study_logger.stop_session_recording()


def is_recording_active():
    """Check if a recording is currently active."""
    return _study_logger.is_recording_active()


# Async GitHub Service Management Functions
def get_async_github_stats():
    """Get statistics about the async GitHub operation queue."""
    return _async_github_service.get_stats()


def get_async_github_queue_size():
    """Get the current size of the async GitHub operation queue."""
    return _async_github_service.get_queue_size()


def wait_for_async_github_completion(timeout=None):
    """Wait for all queued GitHub operations to complete."""
    return _async_github_service.wait_for_completion(timeout)


def stop_async_github_service():
    """Stop the async GitHub service worker thread."""
    return _async_github_service.stop_worker()


def restart_async_github_service():
    """Restart the async GitHub service worker thread."""
    _async_github_service.stop_worker()
    _async_github_service.start_worker()


def test_github_connectivity_async(participant_id, github_token, github_org):
    """Test GitHub connectivity asynchronously."""
    _async_github_service.queue_test_connectivity(participant_id, github_token, github_org)
    return True  # Return immediately


def get_session_log_history(participant_id, development_mode, study_stage):
    """Get the session log history for a participant and stage."""
    return _study_logger.get_session_log_history(participant_id, development_mode, study_stage)


def determine_correct_route(participant_id, development_mode, study_stage, current_route=None):
    """
    Determine the correct route for a participant based on their session log history.
    Enforces linear study flow without allowing backwards navigation.
    
    Stage 1 Flow: home -> consent -> background_questionnaire -> tutorial -> task -> ux_questionnaire -> goodbye
    Stage 2 Flow: welcome_back -> task -> ux_questionnaire -> goodbye
    
    Args:
        participant_id: The participant's unique identifier
        development_mode: Whether running in development mode
        study_stage: The current study stage (1 or 2)
        current_route: The route being accessed (optional, for more specific rules)
    
    Returns:
        The route name the user should be redirected to, or None if no redirect needed
    """
    try:
        # Get session log history for the current stage
        session_visits = get_session_log_history(participant_id, development_mode, study_stage)
        
        if not session_visits:
            # No visits logged yet - allow normal flow
            return None
        
        # Extract route names from visits in chronological order
        visited_routes = [visit.get('route') for visit in session_visits if visit.get('route')]
        
        # Define the study flow for each stage
        if study_stage == 1:
            flow = ['home', 'consent', 'background_questionnaire', 'tutorial', 'task', 'ux_questionnaire', 'goodbye']
        else:  # stage 2
            flow = ['welcome_back', 'task', 'ux_questionnaire', 'goodbye']
        
        # Find the furthest step completed in the flow
        furthest_step_index = -1
        for i, step in enumerate(flow):
            if step in visited_routes:
                furthest_step_index = i
        
        # If no steps completed yet, allow normal flow
        if furthest_step_index == -1:
            return None
        
        # Get the current route's position in the flow
        try:
            current_route_index = flow.index(current_route) if current_route in flow else -1
        except ValueError:
            current_route_index = -1
        
        # If trying to access a step before the furthest completed step, redirect to furthest step
        if current_route_index != -1 and current_route_index <= furthest_step_index:
            # Allow access to the current furthest step or the next step
            if current_route_index == furthest_step_index:
                # User is on their current step - allow
                return None
            elif current_route_index == furthest_step_index + 1:
                # User is trying to go to the next step - allow
                return None
            else:
                # User is trying to go backwards - redirect to furthest step
                return flow[furthest_step_index]
        
        # If trying to access a step too far ahead, redirect to the next logical step
        if current_route_index > furthest_step_index + 1:
            if furthest_step_index + 1 < len(flow):
                return flow[furthest_step_index + 1]
            else:
                # Already at the end of the flow
                return flow[furthest_step_index]
        
        # For routes not in the flow, redirect to the furthest completed step
        if current_route not in flow:
            return flow[furthest_step_index]
        
        # No redirect needed
        return None
        
    except Exception as e:
        print(f"Error determining correct route: {str(e)}")
        return None