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
def get_coding_condition(participant_id):
    """Determine the coding condition based on participant ID."""
    return _participant_manager.get_coding_condition(participant_id)


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


# Session Tracking Functions
def should_log_route(session, route_name, study_stage):
    """Check if a route should be logged."""
    return _session_tracker.should_log_route(session, route_name, study_stage)


def mark_route_as_logged(session, route_name, study_stage):
    """Mark a route as having been logged in the session."""
    return _session_tracker.mark_route_as_logged(session, route_name, study_stage)


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