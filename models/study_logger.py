"""
Logging system for the coding study Flask application.
Handles route logging, session tracking, and study flow monitoring.

Screen Recording Implementation:
- Uses OBS Studio for cross-platform screen recording (Windows, macOS, Linux)
- Assumes OBS is already configured with default scenes and profiles
- Supports graceful start/stop of recording sessions using existing configuration
- Automatically detects OBS installation paths on different platforms
- Falls back to process management if standard paths aren't found

Requirements:
- OBS Studio must be installed and configured on the system
- Default scene and profile should be set up for recording
- For Windows: Typically installed in "C:\\Program Files\\obs-studio\\"
- For macOS: Typically installed as "/Applications/OBS.app"  
- For Linux: Available as "obs" command in PATH
"""

import os
import json
import subprocess
import platform
import zipfile
import logging
import random
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from .github_service import GitHubService
from .global_git_lock import get_participant_git_lock
from .screen_recorder import ScreenRecorder, FocusTracker

# Get logger for this module
logger = logging.getLogger(__name__)

class StudyLogger:
    """
    Handles logging of study flow, route visits, and participant actions.
    """
    
    def __init__(self, github_service: GitHubService):
        """
        Initialize StudyLogger with GitHub service.
        
        Args:
            github_service: GitHubService instance for GitHub operations
        """
        self.github_service = github_service
        self.screen_recorder = ScreenRecorder()
        # Generate unique session ID for this app run
        self.session_id = self._generate_session_id()
        self.focus_tracker = None

    def start_focus_tracking(self, participant_id: str, study_stage: int, development_mode: bool):
        """
        Start background window focus tracking for the participant.
        """
        logs_directory = self.get_logs_directory_path(participant_id, development_mode)
        if not self.focus_tracker:
            self.focus_tracker = FocusTracker(logs_directory, study_stage)
        self.focus_tracker.start()

    def stop_focus_tracking(self):
        """
        Stop background window focus tracking.
        """
        if self.focus_tracker:
            self.focus_tracker.stop()
            self.focus_tracker = None
    
    def _generate_session_id(self) -> str:
        """
        Generate a unique session ID for this app run.
        
        Returns:
            Unique session identifier string
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        # Add some randomness to handle multiple starts within the same second
        random_suffix = f"{random.randint(1000, 9999)}"
        return f"{timestamp}_{random_suffix}"
    
    def get_logging_branch_name(self) -> str:
        """
        Get the logging branch name (always 'logging').
        
        Returns:
            Standard logging branch name
        """
        return "logging"
    
    def get_session_log_filename(self) -> str:
        """
        Get the session log filename (consistent across all sessions).
        
        Returns:
            Standard session log filename
        """
        return "session_log.json"
    
    def start_session_recording(self, participant_id: str, study_stage: int, development_mode: bool) -> bool:
        """
        Start screen recording and focus tracking for the study session.
        
        Args:
            participant_id: The participant's unique identifier
            study_stage: The current study stage (1 or 2)
            development_mode: Whether running in development mode
        Returns:
            True if recording started successfully, False otherwise
        """
        # Skip screen recording and focus tracking in development mode
        if development_mode:
            logger.info("Screen recording and focus tracking disabled in development mode")
            return True
        logs_directory = self.get_logs_directory_path(participant_id, development_mode)
        # Start focus tracking
        self.start_focus_tracking(participant_id, study_stage, development_mode)
        # Start screen recording
        return self.screen_recorder.start_recording(participant_id, study_stage, logs_directory)
    
    def stop_session_recording(self) -> bool:
        """
        Stop the current session recording and focus tracking.
        
        Returns:
            True if recording stopped successfully, False otherwise
        """
        self.stop_focus_tracking()
        return self.screen_recorder.stop_recording()
    
    def is_recording_active(self) -> bool:
        """
        Check if a recording is currently active.
        
        Returns:
            True if recording is active, False otherwise
        """
        return self.screen_recorder.is_recording()

    def upload_session_recording_to_azure(self, participant_id: str, study_stage: int) -> bool:
        """
        Upload the current session recording to Azure Blob Storage.
        This should be called after stopping a recording session.
        
        Args:
            participant_id: The participant's unique identifier
            study_stage: The current study stage
            
        Returns:
            True if upload was successful, False otherwise
        """
        return self.screen_recorder.upload_recording_to_azure(participant_id, study_stage)
    
    def _get_recording_subprocess_kwargs(self) -> Dict[str, Any]:
        """
        Get subprocess keyword arguments for recording processes.
        
        Returns:
            Dictionary of keyword arguments for subprocess.Popen()
        """
        kwargs = {
            'stdout': subprocess.PIPE,
            'stderr': subprocess.PIPE
        }
        
        # Platform-specific settings
        if platform.system() == "Windows":
            kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
            kwargs['shell'] = True
        else:
            kwargs['preexec_fn'] = os.setsid
        
        return kwargs
    
    def _get_subprocess_kwargs(self) -> Dict[str, Any]:
        """
        Get subprocess keyword arguments with platform-specific settings.
        On Windows, prevents terminal windows from flickering by setting CREATE_NO_WINDOW flag.
        
        Returns:
            Dictionary of keyword arguments for subprocess.run()
        """
        kwargs = {
            'capture_output': True,
            'text': True
        }
        
        # On Windows, prevent terminal window from showing
        if platform.system() == "Windows":
            kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
            kwargs['shell'] = True  # Use shell=True to handle Windows paths correctly
        
        return kwargs
    
    def get_logs_directory_path(self, participant_id: str, development_mode: bool) -> str:
        """
        Get the path to the logs directory (separate from the main coding repository).
        
        Args:
            participant_id: The participant's unique identifier
            development_mode: Whether running in development mode
        
        Returns:
            The absolute path to the logs directory
        """
        if development_mode:
            current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            workspace_path = current_dir
            logs_dir_name = f"logs-{participant_id}"
            logs_path = os.path.join(workspace_path, logs_dir_name)
        else:
            home_dir = os.path.expanduser("~")
            workspace_path = os.path.join(home_dir, "workspace")
            logs_dir_name = f"logs-{participant_id}"
            logs_path = os.path.join(workspace_path, logs_dir_name)
        
        return os.path.normpath(logs_path)
    
    def ensure_logging_repository(self, participant_id: str, development_mode: bool,
                                github_token: Optional[str], github_org: str) -> bool:
        """
        Ensure the logging repository exists and is set up with a logging branch.
        Creates a separate repository/directory for logs to keep them hidden from participants.
        Handles remote synchronization to avoid conflicts.
        
        Args:
            participant_id: The participant's unique identifier
            development_mode: Whether running in development mode
            github_token: GitHub personal access token (optional)
            github_org: GitHub organization name
        
        Returns:
            True if successful, False otherwise
        """
        logs_path = self.get_logs_directory_path(participant_id, development_mode)
        original_cwd = os.getcwd()
        
        try:
            # Create logs directory if it doesn't exist
            if not os.path.exists(logs_path):
                os.makedirs(logs_path)
                logger.info(f"Created logs directory: {logs_path}")
            
            # Check if it's already a git repository
            git_dir = os.path.join(logs_path, '.git')
            if not os.path.exists(git_dir):
                # Initialize as git repository
                os.chdir(logs_path)
                
                kwargs = self._get_subprocess_kwargs()
                kwargs["timeout"] = 10
                result = subprocess.run([
                    'git', 'init'
                ], **kwargs)
                
                if result.returncode != 0:
                    logger.warning(f"Failed to initialize git repository in logs directory. Error: {result.stderr}")
                    return False
                
                # Set up git config (basic config for logging)
                kwargs = self._get_subprocess_kwargs()
                kwargs["timeout"] = 5
                subprocess.run(['git', 'config', 'user.name', f'{participant_id}'], **kwargs)
                subprocess.run(['git', 'config', 'user.email', f'{participant_id}@study.local'], **kwargs)
                
                # Create initial README
                readme_content = f"# Study Logs for Participant {participant_id}\n\nThis repository contains anonymized logs for study analysis.\n"
                readme_path = os.path.join(logs_path, 'README.md')
                with open(readme_path, 'w', encoding='utf-8') as f:
                    f.write(readme_content)
                
                # Initial commit
                kwargs = self._get_subprocess_kwargs()
                kwargs["timeout"] = 5
                subprocess.run(['git', 'add', 'README.md'], **kwargs)
                subprocess.run(['git', 'commit', '-m', 'Initial commit for logging repository'], **kwargs)
                
                logger.info(f"Initialized logging repository at: {logs_path}")
            
            # Ensure we're in the logs directory
            os.chdir(logs_path)
            
            # Set up remote if we have authentication and it doesn't exist
            if github_token:
                self._setup_logging_remote(participant_id, github_token, github_org)
            
            # Ensure logging branch with remote synchronization
            return self._ensure_logging_branch_with_sync()
            
        except Exception as e:
            logger.info(f"Error ensuring logging repository: {str(e)}")
            return False
        finally:
            try:
                os.chdir(original_cwd)
            except Exception as e:
                logger.warning(f"Failed to restore original working directory: {str(e)}")
    
    def _setup_logging_remote(self, participant_id: str, github_token: str, github_org: str) -> bool:
        """
        Set up the remote for the logging repository.
        
        Args:
            participant_id: The participant's unique identifier
            github_token: GitHub personal access token
            github_org: GitHub organization name
        
        Returns:
            True if successful, False otherwise
        """
        try:
            repo_name = f"study-{participant_id}"
            authenticated_url = self.github_service.get_authenticated_repo_url(repo_name, github_token, github_org)
            
            # Check if remote exists
            kwargs = self._get_subprocess_kwargs()
            kwargs["timeout"] = 5
            result = subprocess.run(['git', 'remote'], **kwargs)
            
            if 'origin' not in result.stdout:
                # Add remote
                kwargs["timeout"] = 10
                result = subprocess.run(['git', 'remote', 'add', 'origin', authenticated_url], **kwargs)
                if result.returncode != 0:
                    logger.warning(f"Failed to add remote: {result.stderr}")
                    return False
            else:
                # Update remote URL
                kwargs["timeout"] = 10
                result = subprocess.run(['git', 'remote', 'set-url', 'origin', authenticated_url], **kwargs)
                if result.returncode != 0:
                    logger.warning(f"Failed to set remote URL: {result.stderr}")
                    return False
                    
            return True
            
        except Exception as e:
            logger.info(f"Error setting up logging remote: {str(e)}")
            return False
    
    def _ensure_logging_branch_with_sync(self) -> bool:
        """
        Ensure logging branch exists and is synced with remote.
        Uses a single 'logging' branch for all sessions.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            branch_name = self.get_logging_branch_name()  # Always 'logging'
            
            # First, try to fetch from remote to get latest refs
            kwargs = self._get_subprocess_kwargs()
            kwargs["timeout"] = 15
            result = subprocess.run(['git', 'fetch', 'origin'], **kwargs)
            if result.returncode != 0:
                logger.warning(f"Failed to fetch from remote (may not exist yet): {result.stderr}")
            
            # Check if logging branch exists locally
            kwargs = self._get_subprocess_kwargs()
            kwargs["timeout"] = 10
            result = subprocess.run(['git', 'branch', '--list', branch_name], **kwargs)
            local_branch_exists = branch_name in result.stdout
            
            # Check if logging branch exists remotely
            kwargs = self._get_subprocess_kwargs()
            kwargs["timeout"] = 10
            result = subprocess.run(['git', 'branch', '-r', '--list', f'origin/{branch_name}'], **kwargs)
            remote_branch_exists = f'origin/{branch_name}' in result.stdout
            
            if local_branch_exists and remote_branch_exists:
                # Both exist - checkout local and pull updates
                logger.info(f"Branch {branch_name} exists both locally and remotely - syncing")
                kwargs = self._get_subprocess_kwargs()
                kwargs["timeout"] = 10
                result = subprocess.run(['git', 'checkout', branch_name], **kwargs)
                
                if result.returncode != 0:
                    logger.warning(f"Failed to checkout branch {branch_name}: {result.stderr}")
                    return False
                
                # Pull updates to get existing session data
                kwargs = self._get_subprocess_kwargs()
                kwargs["timeout"] = 20
                result = subprocess.run(['git', 'pull', 'origin', branch_name, '--allow-unrelated-histories'], **kwargs)
                
                if result.returncode != 0:
                    logger.warning(f"Failed to pull branch {branch_name} updates: {result.stderr}")
                else:
                    logger.info(f"Successfully synchronized branch {branch_name} with remote")
                    
            elif local_branch_exists:
                # Only local exists - just switch to it
                logger.info(f"Switching to existing local branch {branch_name}")
                kwargs = self._get_subprocess_kwargs()
                kwargs["timeout"] = 10
                result = subprocess.run(['git', 'checkout', branch_name], **kwargs)
                
                if result.returncode != 0:
                    logger.warning(f"Failed to checkout branch {branch_name}: {result.stderr}")
                    return False
                    
            elif remote_branch_exists:
                # Only remote exists - create local tracking branch
                logger.info(f"Creating local branch {branch_name} tracking remote origin/{branch_name}")
                kwargs = self._get_subprocess_kwargs()
                kwargs["timeout"] = 15
                result = subprocess.run([
                    'git', 'checkout', '-b', branch_name, f'origin/{branch_name}'
                ], **kwargs)
                
                if result.returncode != 0:
                    logger.warning(f"Failed to create tracking branch {branch_name}: {result.stderr}")
                    return False
                    
            else:
                # Neither exists - create new branch from main/master
                logger.info(f"Creating new branch {branch_name}")
                
                # First ensure we're on main/master
                kwargs = self._get_subprocess_kwargs()
                kwargs["timeout"] = 10
                result = subprocess.run(['git', 'checkout', 'main'], **kwargs)
                if result.returncode != 0:
                    # Try master if main doesn't exist
                    result = subprocess.run(['git', 'checkout', 'master'], **kwargs)
                    if result.returncode != 0:
                        logger.warning(f"Failed to checkout main/master branch: {result.stderr}")
                        return False
                
                # Create new branch
                kwargs = self._get_subprocess_kwargs()
                kwargs["timeout"] = 10
                result = subprocess.run(['git', 'checkout', '-b', branch_name], **kwargs)
                
                if result.returncode != 0:
                    logger.warning(f"Failed to create branch {branch_name}: {result.stderr}")
                    return False
            
            logger.info(f"Successfully ensured branch {branch_name} is active")
            return True
            
        except Exception as e:
            logger.info(f"Error ensuring logging branch: {str(e)}")
            return False
    
    def log_route_visit(self, participant_id: str, route_name: str, development_mode: bool,
                      study_stage: int, session_data: Optional[Dict] = None,
                      github_token: Optional[str] = None, github_org: Optional[str] = None) -> bool:
        """
        Log a route visit with timestamp and relevant context.
        Uses session-specific log file to avoid conflicts with previous runs.
        
        Args:
            participant_id: The participant's ID
            route_name: Name of the route (e.g., 'home', 'tutorial', 'task', etc.)
            development_mode: Whether in development mode
            study_stage: Current study stage (1 or 2)
            session_data: Optional session data to include in log
            github_token: Optional GitHub token for pushing logs
            github_org: Optional GitHub organization
        
        Returns:
            True if logging was successful, False otherwise
        """
        lock = get_participant_git_lock(participant_id)
        with lock:
            try:
                # Ensure logging repository exists
                if not self.ensure_logging_repository(participant_id, development_mode, github_token, github_org):
                    logger.warning(f"Failed to ensure logging repository for participant {participant_id}")
                    return False
                
                logs_path = self.get_logs_directory_path(participant_id, development_mode)
                # Use session-specific log file
                log_file_path = os.path.join(logs_path, self.get_session_log_filename())
                original_cwd = os.getcwd()
                
                # Switch to logs directory
                os.chdir(logs_path)
                
                # Ensure we're on the logging branch
                kwargs = self._get_subprocess_kwargs()
                kwargs["timeout"] = 5
                subprocess.run(['git', 'checkout', self.get_logging_branch_name()], **kwargs)
                
                # Load existing logs from remote or create new structure
                logs_data = {
                    'sessions': []
                }
                
                if os.path.exists(log_file_path):
                    try:
                        with open(log_file_path, 'r', encoding='utf-8') as f:
                            logs_data = json.load(f)
                            # Ensure sessions key exists for compatibility
                            if 'sessions' not in logs_data:
                                logs_data['sessions'] = []
                    except (json.JSONDecodeError, FileNotFoundError):
                        logger.info("Could not read existing session log file, creating new one")
                
                # Find or create session data for this session_id
                current_session = None
                for session in logs_data['sessions']:
                    if session.get('session_id') == self.session_id:
                        current_session = session
                        break
                
                if current_session is None:
                    # Create new session entry
                    current_session = {
                        'session_id': self.session_id,
                        'session_start_time': datetime.now().isoformat(),
                        'visits': []
                    }
                    logs_data['sessions'].append(current_session)
                
                # Check if this route has already been visited in this session for this stage
                existing_visits = [visit for visit in current_session['visits'] 
                                 if visit.get('route') == route_name and visit.get('study_stage') == study_stage]
                
                if existing_visits:
                    logger.info(f"Route {route_name} already logged in this session for stage {study_stage}, skipping")
                    return True
                
                # Create log entry
                timestamp = datetime.now()
                log_entry = {
                    'participant_id': participant_id,
                    'route': route_name,
                    'study_stage': study_stage,
                    'timestamp': timestamp.isoformat(),
                    'timestamp_unix': timestamp.timestamp(),
                    'development_mode': development_mode,
                    'session_id': self.session_id
                }
                
                # Add session data if provided
                if session_data:
                    log_entry['session_data'] = session_data
                
                # Add to current session's visits
                current_session['visits'].append(log_entry)
                
                # Write updated logs
                with open(log_file_path, 'w', encoding='utf-8') as f:
                    json.dump(logs_data, f, indent=2, ensure_ascii=False)
                
                # Commit and push all files in the logs directory (including focus_log.json)
                kwargs = self._get_subprocess_kwargs()
                kwargs["timeout"] = 10
                subprocess.run(['git', 'add', '.'], **kwargs)

                commit_message = f"Log route visit: {route_name} (stage {study_stage}) at {timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
                result = subprocess.run(['git', 'commit', '-m', commit_message], **kwargs)

                if result.returncode == 0:
                    logger.info(f"Successfully logged route visit: {route_name} for participant {participant_id}, stage {study_stage}")
                    # Push to remote if token is available
                    if github_token and github_org:
                        self.push_logs_to_remote(participant_id, development_mode, github_token, github_org)
                    return True
                else:
                    logger.warning(f"Failed to commit log entry. Error: {result.stderr}")
                    return False
                    
            except Exception as e:
                logger.info(f"Error logging route visit: {str(e)}")
                return False
            finally:
                try:
                    os.chdir(original_cwd)
                except Exception as e:
                    logger.warning(f"Failed to restore working directory: {str(e)}")
    
    def push_logs_to_remote(self, participant_id: str, development_mode: bool,
                          github_token: str, github_org: str) -> bool:
        """
        Push logs to remote repository on the logging branch.
        Uses enhanced retry logic and conflict resolution.
        
        Args:
            participant_id: The participant's unique identifier
            development_mode: Whether running in development mode
            github_token: GitHub personal access token
            github_org: GitHub organization name
        
        Returns:
            True if successful, False otherwise
        """
        lock = get_participant_git_lock(participant_id)
        with lock:
            logs_path = self.get_logs_directory_path(participant_id, development_mode)
            original_cwd = os.getcwd()
            try:
                os.chdir(logs_path)
                # Ensure logging repository and branch are properly set up with sync
                if not self.ensure_logging_repository(participant_id, development_mode, github_token, github_org):
                    logger.warning(f"Failed to ensure logging repository for push")
                    return False
                # Use enhanced push with retry logic for logging
                return self._push_logs_with_retry(participant_id, github_token, github_org)
            except Exception as e:
                logger.info(f"Error pushing logs to remote: {str(e)}")
                return False
            finally:
                try:
                    os.chdir(original_cwd)
                except Exception as e:
                    logger.warning(f"Failed to restore original working directory: {str(e)}")
    
    def _push_logs_with_retry(self, participant_id: str, github_token: str, 
                             github_org: str, max_retries: int = 3) -> bool:
        """
        Push logs with retry logic and conflict resolution.
        
        Args:
            participant_id: The participant's unique identifier
            github_token: GitHub personal access token
            github_org: GitHub organization name
            max_retries: Maximum number of retry attempts
        
        Returns:
            True if successful, False otherwise
        """
        for attempt in range(max_retries):
            try:
                # Set up the authenticated remote URL
                repo_name = f"study-{participant_id}"
                authenticated_url = self.github_service.get_authenticated_repo_url(repo_name, github_token, github_org)
                
                # Update the origin URL to use authentication
                kwargs = self._get_subprocess_kwargs()
                kwargs["timeout"] = 10
                result = subprocess.run(['git', 'remote', 'set-url', 'origin', authenticated_url], **kwargs)
                
                if result.returncode != 0:
                    logger.warning(f"Failed to set authenticated remote URL: {result.stderr}")
                
                # Attempt to push our unique logging branch
                branch_name = self.get_logging_branch_name()
                kwargs = self._get_subprocess_kwargs()
                kwargs["timeout"] = 30
                result = subprocess.run(['git', 'push', 'origin', branch_name], **kwargs)
                
                if result.returncode == 0:
                    logger.info(f"Successfully pushed logs to remote for participant {participant_id}")
                    return True
                else:
                    error_msg = result.stderr.lower()
                    if 'rejected' in error_msg or 'non-fast-forward' in error_msg:
                        logger.info(f"Log push rejected (attempt {attempt + 1}/{max_retries}). Trying to sync with remote...")
                        
                        # Try to sync with remote logging branch
                        if self._sync_logging_with_remote():
                            logger.info("Successfully synced logging with remote. Retrying push...")
                            continue
                        else:
                            logger.info("Failed to sync logging with remote branch")
                            if attempt == max_retries - 1:
                                return False
                    else:
                        logger.info(f"Log push failed with error: {result.stderr}")
                        if attempt == max_retries - 1:
                            return False
                        
            except subprocess.TimeoutExpired:
                logger.info(f"Log push operation timed out (attempt {attempt + 1}/{max_retries})")
                if attempt == max_retries - 1:
                    return False
            except Exception as e:
                logger.info(f"Error during log push attempt {attempt + 1}: {str(e)}")
                if attempt == max_retries - 1:
                    return False
        
        return False
    
    def _sync_logging_with_remote(self) -> bool:
        """
        Sync local logging branch with remote logging branch.
        Uses unique branch names so conflicts should be rare.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            branch_name = self.get_logging_branch_name()
            
            # Fetch latest changes
            kwargs = self._get_subprocess_kwargs()
            kwargs['timeout'] = 15
            result = subprocess.run(['git', 'fetch', 'origin'], **kwargs)
            
            if result.returncode != 0:
                logger.warning(f"Failed to fetch from remote: {result.stderr}")
                return False
            
            # Try to pull and merge
            kwargs = self._get_subprocess_kwargs()
            kwargs['timeout'] = 20
            result = subprocess.run(['git', 'pull', 'origin', branch_name, '--allow-unrelated-histories'], **kwargs)
            
            if result.returncode == 0:
                logger.info(f"Successfully merged remote changes for branch {branch_name}")
                return True
            else:
                logger.warning(f"Failed to merge remote changes for branch {branch_name}: {result.stderr}")
                return False
                    
        except Exception as e:
            logger.info(f"Error syncing logging with remote: {str(e)}")
            return False
    
    def mark_stage_transition(self, participant_id: str, from_stage: int, to_stage: int,
                            development_mode: bool, github_token: Optional[str] = None,
                            github_org: Optional[str] = None) -> bool:
        """
        Mark a stage transition in the logs for explicit tracking.
        This is called when a participant completes stage 1 and moves to stage 2.
        
        Args:
            participant_id: The participant's ID
            from_stage: The stage being transitioned from
            to_stage: The stage being transitioned to
            development_mode: Whether in development mode
            github_token: Optional GitHub token for pushing logs
            github_org: Optional GitHub organization
        
        Returns:
            True if successful, False otherwise
        """
        lock = get_participant_git_lock(participant_id)
        with lock:
            try:
                # Ensure logging repository exists
                if not self.ensure_logging_repository(participant_id, development_mode, github_token, github_org):
                    logger.warning(f"Failed to ensure logging repository for participant {participant_id}")
                    return False
                
                logs_path = self.get_logs_directory_path(participant_id, development_mode)
                log_file_path = os.path.join(logs_path, 'stage_transitions.json')
                original_cwd = os.getcwd()
                
                # Switch to logs directory
                os.chdir(logs_path)
                
                # Ensure we're on the logging branch
                kwargs = self._get_subprocess_kwargs()
                kwargs["timeout"] = 5
                subprocess.run(['git', 'checkout', self.get_logging_branch_name()], **kwargs)
                
                # Load existing transitions or create new structure
                transitions_data = {'transitions': []}
                if os.path.exists(log_file_path):
                    try:
                        with open(log_file_path, 'r', encoding='utf-8') as f:
                            transitions_data = json.load(f)
                    except (json.JSONDecodeError, FileNotFoundError):
                        logger.info("Could not read existing transitions file, creating new one")
                
                # Check if this transition has already been logged
                transition_key = f"stage_{from_stage}_to_{to_stage}"
                existing_transitions = [t for t in transitions_data['transitions'] 
                                      if t.get('from_stage') == from_stage and t.get('to_stage') == to_stage]
                
                if existing_transitions:
                    logger.info(f"Transition {transition_key} already logged, skipping")
                    return True
                
                # Create transition log entry
                timestamp = datetime.now()
                transition_entry = {
                    'participant_id': participant_id,
                    'from_stage': from_stage,
                    'to_stage': to_stage,
                    'transition_key': transition_key,
                    'timestamp': timestamp.isoformat(),
                    'timestamp_unix': timestamp.timestamp(),
                    'development_mode': development_mode
                }
                
                # Add to transitions
                transitions_data['transitions'].append(transition_entry)
                
                # Write updated transitions
                with open(log_file_path, 'w', encoding='utf-8') as f:
                    json.dump(transitions_data, f, indent=2, ensure_ascii=False)
                
                # Commit the transition entry
                kwargs = self._get_subprocess_kwargs()
                kwargs["timeout"] = 5
                subprocess.run(['git', 'add', 'stage_transitions.json'], **kwargs)
                
                commit_message = f"Mark stage transition: {transition_key} at {timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
                kwargs["timeout"] = 10
                result = subprocess.run(['git', 'commit', '-m', commit_message], **kwargs)
                
                if result.returncode == 0:
                    logger.info(f"Successfully logged stage transition: {transition_key} for participant {participant_id}")
                    
                    # Push to remote if token is available
                    if github_token and github_org:
                        self.push_logs_to_remote(participant_id, development_mode, github_token, github_org)
                    
                    return True
                else:
                    logger.warning(f"Failed to commit transition entry. Error: {result.stderr}")
                    return False
                    
            except Exception as e:
                logger.info(f"Error logging stage transition: {str(e)}")
                return False
            finally:
                try:
                    os.chdir(original_cwd)
                except Exception as e:
                    logger.warning(f"Failed to restore working directory: {str(e)}")
    
    def get_stage_transition_history(self, participant_id: str, development_mode: bool) -> List[Dict]:
        """
        Get the stage transition history for a participant.
        
        Args:
            participant_id: The participant's unique identifier
            development_mode: Whether running in development mode
        
        Returns:
            List of transition entries, or empty list if none found
        """
        try:
            logs_path = self.get_logs_directory_path(participant_id, development_mode)
            log_file_path = os.path.join(logs_path, 'stage_transitions.json')
            
            if not os.path.exists(log_file_path):
                return []
            
            with open(log_file_path, 'r', encoding='utf-8') as f:
                transitions_data = json.load(f)
            
            return transitions_data.get('transitions', [])
            
        except Exception as e:
            logger.info(f"Error reading stage transition history: {str(e)}")
            return []
    
    def get_vscode_workspace_storage_path(self) -> Optional[str]:
        """
        Get the platform-specific VS Code workspace storage path.
        
        Returns:
            The absolute path to VS Code workspace storage directory, or None if not found
        """
        system = platform.system()
        
        if system == "Windows":
            # Windows: %APPDATA%\Code\User\workspaceStorage
            appdata = os.environ.get('APPDATA')
            if appdata:
                return os.path.join(appdata, 'Code', 'User', 'workspaceStorage')
        
        elif system == "Darwin":  # macOS
            # macOS: ~/Library/Application Support/Code/User/workspaceStorage
            home = os.path.expanduser("~")
            return os.path.join(home, 'Library', 'Application Support', 'Code', 'User', 'workspaceStorage')
        
        elif system == "Linux":
            # Linux: ~/.config/Code/User/workspaceStorage
            home = os.path.expanduser("~")
            return os.path.join(home, '.config', 'Code', 'User', 'workspaceStorage')
        
        return None
    
    def save_vscode_workspace_storage(self, participant_id: str, study_stage: int, 
                                    development_mode: bool, github_token: Optional[str] = None,
                                    github_org: Optional[str] = None) -> bool:
        """
        Save VS Code workspace storage for a participant at the end of a coding stage.
        Creates a compressed archive of the workspace storage and commits it to the logging repository.
        
        Args:
            participant_id: The participant's unique identifier
            study_stage: The study stage (1 or 2)
            development_mode: Whether running in development mode
            github_token: Optional GitHub token for pushing logs
            github_org: Optional GitHub organization
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get VS Code workspace storage path
            vscode_storage_path = self.get_vscode_workspace_storage_path()
            if not vscode_storage_path or not os.path.exists(vscode_storage_path):
                logger.info(f"VS Code workspace storage not found at: {vscode_storage_path}")
                return False
            
            # Ensure logging repository exists
            if not self.ensure_logging_repository(participant_id, development_mode, github_token, github_org):
                logger.info("Failed to ensure logging repository exists")
                return False
            
            logs_path = self.get_logs_directory_path(participant_id, development_mode)
            original_cwd = os.getcwd()
            
            # Switch to logs directory
            os.chdir(logs_path)
            
            # Ensure we're on the logging branch
            kwargs = self._get_subprocess_kwargs()
            kwargs["timeout"] = 5
            subprocess.run(['git', 'checkout', self.get_logging_branch_name()], **kwargs)
            
            # Create vscode-storage directory if it doesn't exist
            vscode_logs_dir = os.path.join(logs_path, 'vscode-storage')
            if not os.path.exists(vscode_logs_dir):
                os.makedirs(vscode_logs_dir)
            
            # Create timestamped archive filename
            timestamp = datetime.now()
            archive_filename = f"workspace_storage_stage{study_stage}_{timestamp.strftime('%Y%m%d_%H%M%S')}.zip"
            archive_path = os.path.join(vscode_logs_dir, archive_filename)
            
            # Create zip archive of workspace storage
            logger.info(f"Creating VS Code workspace storage archive: {archive_filename}")
            with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(vscode_storage_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        # Get relative path from workspace storage directory
                        arcname = os.path.relpath(file_path, vscode_storage_path)
                        try:
                            zipf.write(file_path, arcname)
                        except (OSError, PermissionError) as e:
                            # Skip files that can't be read (e.g., locked files)
                            logger.info(f"Skipping file due to permission error: {file_path} - {e}")
                            continue
            
            # Add files to git
            kwargs = self._get_subprocess_kwargs()
            kwargs["timeout"] = 10
            subprocess.run(['git', 'add', 'vscode-storage/'], **kwargs)
            
            # Commit the VS Code workspace storage
            commit_message = f"Save VS Code workspace storage for stage {study_stage} at {timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
            kwargs["timeout"] = 15
            result = subprocess.run(['git', 'commit', '-m', commit_message], **kwargs)
            
            if result.returncode == 0:
                logger.info(f"Successfully saved VS Code workspace storage for stage {study_stage}")
                return True
            else:
                logger.warning(f"Failed to commit VS Code workspace storage: {result.stderr}")
                return False
                
        except Exception as e:
            logger.info(f"Error saving VS Code workspace storage: {str(e)}")
            return False
        finally:
            try:
                os.chdir(original_cwd)
            except Exception as e:
                logger.info(f"Error returning to original directory: {str(e)}")

    def get_session_log_history(self, participant_id: str, development_mode: bool, study_stage: int) -> List[Dict]:
        """
        Get the session log history for a participant and stage from the current session.
        
        Args:
            participant_id: The participant's unique identifier
            development_mode: Whether running in development mode
            study_stage: The study stage to get logs for
        
        Returns:
            List of route visit entries for the specified stage from current session, sorted by timestamp
        """
        try:
            logs_path = self.get_logs_directory_path(participant_id, development_mode)
            log_file_path = os.path.join(logs_path, self.get_session_log_filename())
            
            if not os.path.exists(log_file_path):
                return []
            
            with open(log_file_path, 'r', encoding='utf-8') as f:
                logs_data = json.load(f)
            
            # Collect visits from all sessions for the specified stage
            all_stage_visits = []
            for session in logs_data.get('sessions', []):
                stage_visits = [visit for visit in session.get('visits', []) 
                            if visit.get('study_stage') == study_stage]
                all_stage_visits.extend(stage_visits)

            # Sort by timestamp (using timestamp_unix for reliable sorting)
            all_stage_visits.sort(key=lambda x: x.get('timestamp_unix', 0))

            return all_stage_visits
            
        except Exception as e:
            logger.info(f"Error reading session log history: {str(e)}")
            return []
        
    def get_all_session_logs(self, participant_id: str, development_mode: bool) -> List[Dict]:
        """
        Get all session logs for a participant from the single logging branch.
        
        Args:
            participant_id: The participant's unique identifier
            development_mode: Whether running in development mode
        
        Returns:
            List of all session log data, sorted by session start time
        """
        try:
            logs_path = self.get_logs_directory_path(participant_id, development_mode)
            
            if not os.path.exists(logs_path):
                return []
            
            original_cwd = os.getcwd()
            
            try:
                os.chdir(logs_path)
                
                # Ensure we're on the logging branch
                kwargs = self._get_subprocess_kwargs()
                kwargs["timeout"] = 10
                result = subprocess.run(['git', 'checkout', self.get_logging_branch_name()], **kwargs)
                
                if result.returncode != 0:
                    logger.warning(f"Failed to checkout logging branch: {result.stderr}")
                    return []
                
                # Read session log from the logging branch
                log_file_path = os.path.join(logs_path, 'session_log.json')
                if os.path.exists(log_file_path):
                    with open(log_file_path, 'r', encoding='utf-8') as f:
                        logs_data = json.load(f)
                        # Return all sessions from the consolidated log
                        return logs_data.get('sessions', [])
                
                return []
                
            finally:
                os.chdir(original_cwd)
            
        except Exception as e:
            logger.info(f"Error reading all session logs: {str(e)}")
            return []

class SessionTracker:
    """
    Manages session-based tracking to prevent duplicate logging within a single app run.
    """
    
    @staticmethod
    def should_log_route(session: Dict, route_name: str, study_stage: int) -> bool:
        """
        Check if a route should be logged in the current Flask session.
        This only tracks routes within the current app run/Flask session.
        
        Args:
            session: Flask session object
            route_name: Name of the route
            study_stage: Current study stage
        
        Returns:
            True if route should be logged, False if already logged in this Flask session
        """
        session_key = f'logged_routes_stage{study_stage}'
        logged_routes = session.get(session_key, [])
        
        route_key = f"{route_name}_stage{study_stage}"
        return route_key not in logged_routes
    
    @staticmethod
    def mark_route_as_logged(session: Dict, route_name: str, study_stage: int) -> None:
        """
        Mark a route as having been logged in the current Flask session.
        
        Args:
            session: Flask session object
            route_name: Name of the route
            study_stage: Current study stage
        """
        session_key = f'logged_routes_stage{study_stage}'
        logged_routes = session.get(session_key, [])
        
        route_key = f"{route_name}_stage{study_stage}"
        if route_key not in logged_routes:
            logged_routes.append(route_key)
            session[session_key] = logged_routes
