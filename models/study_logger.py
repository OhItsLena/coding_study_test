"""
Logging system for the coding study Flask application.
Handles route logging, session tracking, and study flow monitoring.
"""

import os
import json
import subprocess
import platform
import shutil
import zipfile
import signal
import time
from datetime import datetime
from typing import Dict, List, Any, Optional

from .github_service import GitHubService


class ScreenRecorder:
    """
    Handles screen recording using FFmpeg.
    """
    
    def __init__(self):
        """Initialize the screen recorder."""
        self.recording_process = None
        self.recording_file_path = None
    
    def start_recording(self, participant_id: str, study_stage: int, logs_directory: str) -> bool:
        """
        Start screen recording using FFmpeg.
        
        Args:
            participant_id: The participant's unique identifier
            study_stage: The current study stage (1 or 2)
            logs_directory: Directory where the recording should be saved
            
        Returns:
            True if recording started successfully, False otherwise
        """
        if self.recording_process is not None:
            print("Screen recording is already in progress")
            return False
        
        try:
            # Create recordings directory if it doesn't exist
            recordings_dir = os.path.join(logs_directory, "recordings")
            os.makedirs(recordings_dir, exist_ok=True)
            
            # Generate recording filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            recording_filename = f"screen_recording_{participant_id}_stage{study_stage}_{timestamp}.mp4"
            self.recording_file_path = os.path.join(recordings_dir, recording_filename)
            
            # FFmpeg command for screen recording (platform-specific)
            if platform.system() == "Darwin":  # macOS
                # Use avfoundation for macOS screen capture
                ffmpeg_cmd = [
                    "ffmpeg",
                    "-f", "avfoundation",
                    "-i", "3:",  # Primary screen (device 3), no audio
                    "-r", "15",   # Output framerate 15 fps
                    "-vcodec", "libx264",
                    "-preset", "ultrafast",
                    "-crf", "28",
                    "-pix_fmt", "yuv420p",  # Ensure compatibility
                    "-y",  # Overwrite output file
                    self.recording_file_path
                ]
            elif platform.system() == "Windows":
                # Use OBS for Windows screen capture
                obs_path = r"C:\Program Files\obs-studio\bin\64bit"
                ffmpeg_cmd = [
                    "cmd", "/c", 
                    f'cd "{obs_path}" && start "obs64.exe" --startrecording'
                ]
            else:  # Linux
                # Use x11grab for Linux screen capture
                ffmpeg_cmd = [
                    "ffmpeg",
                    "-f", "x11grab",
                    "-framerate", "15",
                    "-i", ":0.0",  # Display :0.0
                    "-vcodec", "libx264",
                    "-preset", "ultrafast",
                    "-crf", "28",
                    "-pix_fmt", "yuv420p",  # Ensure compatibility
                    "-y",  # Overwrite output file
                    self.recording_file_path
                ]
            
            # Start the recording process
            print(f"Starting screen recording: {recording_filename}")
            print(f"Command: {' '.join(ffmpeg_cmd)}")
            
            recording_kwargs = self._get_recording_subprocess_kwargs()
            self.recording_process = subprocess.Popen(ffmpeg_cmd, **recording_kwargs)
            
            # Give FFmpeg a moment to start and check if it's running
            time.sleep(2)
            
            if self.recording_process.poll() is not None:
                # Process has already terminated, check for errors
                stdout, stderr = self.recording_process.communicate()
                print(f"FFmpeg failed to start. Error: {stderr.decode()}")
                self.recording_process = None
                self.recording_file_path = None
                return False
            
            print(f"Screen recording started successfully for participant {participant_id}, stage {study_stage}")
            return True
            
        except FileNotFoundError:
            print("FFmpeg not found. Please install FFmpeg and make sure it's in your PATH.")
            self.recording_process = None
            self.recording_file_path = None
            return False
        except Exception as e:
            print(f"Failed to start screen recording: {e}")
            self.recording_process = None
            self.recording_file_path = None
            return False
    
    def stop_recording(self) -> bool:
        """
        Stop the current screen recording.
        
        Returns:
            True if recording stopped successfully, False otherwise
        """
        if self.recording_process is None:
            print("No screen recording in progress")
            return False
        
        try:
            print("Stopping screen recording...")
            
            if platform.system() == "Windows":
                # On Windows, stop OBS using PowerShell
                stop_cmd = ['powershell', '-Command', 'Get-Process obs64 | Stop-Process']
                kwargs = self._get_subprocess_kwargs()
                subprocess.run(stop_cmd, **kwargs)
            else:
                # On Unix-like systems, send SIGTERM to the process group
                os.killpg(os.getpgid(self.recording_process.pid), signal.SIGTERM)
            
            # Wait for the process to terminate
            if self.recording_process and platform.system() != "Windows":
                self.recording_process.wait(timeout=10)
            
            print(f"Screen recording stopped successfully. File saved: {self.recording_file_path}")
            
            # Reset the recording state
            self.recording_process = None
            recording_file = self.recording_file_path
            self.recording_file_path = None
            
            return True
            
        except subprocess.TimeoutExpired:
            print("Recording process did not terminate gracefully, forcing termination")
            if platform.system() == "Windows":
                # Force kill OBS processes
                force_kill_cmd = ['powershell', '-Command', 'Get-Process obs64 -ErrorAction SilentlyContinue | Stop-Process -Force']
                kwargs = self._get_subprocess_kwargs()
                subprocess.run(force_kill_cmd, **kwargs)
            else:
                if self.recording_process:
                    os.killpg(os.getpgid(self.recording_process.pid), signal.SIGKILL)
            self.recording_process = None
            self.recording_file_path = None
            return False
        except Exception as e:
            print(f"Failed to stop screen recording: {e}")
            self.recording_process = None
            self.recording_file_path = None
            return False
    
    def is_recording(self) -> bool:
        """
        Check if a recording is currently in progress.
        
        Returns:
            True if recording is active, False otherwise
        """
        if platform.system() == "Windows":
            # For Windows/OBS, check if obs64 process is running
            try:
                check_cmd = ['powershell', '-Command', 'Get-Process obs64 -ErrorAction SilentlyContinue']
                kwargs = self._get_subprocess_kwargs()
                result = subprocess.run(check_cmd, **kwargs)
                return result.returncode == 0
            except Exception:
                return False
        else:
            # For other platforms, check the process reference
            if self.recording_process is None:
                return False
            
            # Check if the process is still running
            poll_result = self.recording_process.poll()
            if poll_result is not None:
                # Process has terminated
                self.recording_process = None
                self.recording_file_path = None
                return False
            
            return True
    
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
    
    def start_session_recording(self, participant_id: str, study_stage: int, development_mode: bool) -> bool:
        """
        Start screen recording for the study session.
        
        Args:
            participant_id: The participant's unique identifier
            study_stage: The current study stage (1 or 2)
            development_mode: Whether running in development mode
            
        Returns:
            True if recording started successfully, False otherwise
        """
        logs_directory = self.get_logs_directory_path(participant_id, development_mode)
        return self.screen_recorder.start_recording(participant_id, study_stage, logs_directory)
    
    def stop_session_recording(self) -> bool:
        """
        Stop the current session recording.
        
        Returns:
            True if recording stopped successfully, False otherwise
        """
        return self.screen_recorder.stop_recording()
    
    def is_recording_active(self) -> bool:
        """
        Check if a recording is currently active.
        
        Returns:
            True if recording is active, False otherwise
        """
        return self.screen_recorder.is_recording()

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
                print(f"Created logs directory: {logs_path}")
            
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
                    print(f"Failed to initialize git repository in logs directory. Error: {result.stderr}")
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
                
                print(f"Initialized logging repository at: {logs_path}")
            
            # Ensure we're on the logging branch
            os.chdir(logs_path)
            
            # Check if logging branch exists
            kwargs = self._get_subprocess_kwargs()
            kwargs["timeout"] = 10
            result = subprocess.run([
                'git', 'branch', '--list', 'logging'
            ], **kwargs)
            
            if 'logging' not in result.stdout:
                # Create logging branch
                kwargs = self._get_subprocess_kwargs()
                kwargs["timeout"] = 10
                result = subprocess.run([
                    'git', 'checkout', '-b', 'logging'
                ], **kwargs)
                
                if result.returncode != 0:
                    print(f"Failed to create logging branch. Error: {result.stderr}")
                    return False
                
                print("Created logging branch")
            else:
                # Switch to logging branch
                kwargs = self._get_subprocess_kwargs()
                kwargs["timeout"] = 10
                result = subprocess.run([
                    'git', 'checkout', 'logging'
                ], **kwargs)
                
                if result.returncode != 0:
                    print(f"Failed to checkout logging branch. Error: {result.stderr}")
                    return False
            
            return True
            
        except Exception as e:
            print(f"Error setting up logging repository: {str(e)}")
            return False
        finally:
            try:
                os.chdir(original_cwd)
            except Exception as e:
                print(f"Warning: Failed to restore working directory: {str(e)}")
    
    def log_route_visit(self, participant_id: str, route_name: str, development_mode: bool,
                      study_stage: int, session_data: Optional[Dict] = None,
                      github_token: Optional[str] = None, github_org: Optional[str] = None) -> bool:
        """
        Log a route visit with timestamp and relevant context.
        Only logs the first visit to each route to track study flow transitions.
        
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
        try:
            # Ensure logging repository exists
            if not self.ensure_logging_repository(participant_id, development_mode, github_token, github_org):
                print(f"Failed to ensure logging repository for participant {participant_id}")
                return False
            
            logs_path = self.get_logs_directory_path(participant_id, development_mode)
            log_file_path = os.path.join(logs_path, 'session_log.json')
            original_cwd = os.getcwd()
            
            # Switch to logs directory
            os.chdir(logs_path)
            
            # Ensure we're on logging branch
            kwargs = self._get_subprocess_kwargs()
            kwargs["timeout"] = 5
            subprocess.run(['git', 'checkout', 'logging'], **kwargs)
            
            # Load existing logs or create new structure
            logs_data = {'visits': []}
            if os.path.exists(log_file_path):
                try:
                    with open(log_file_path, 'r', encoding='utf-8') as f:
                        logs_data = json.load(f)
                except (json.JSONDecodeError, FileNotFoundError):
                    print("Could not read existing log file, creating new one")
            
            # Check if this route has already been visited in this stage
            existing_visits = [visit for visit in logs_data['visits'] 
                             if visit.get('route') == route_name and visit.get('study_stage') == study_stage]
            
            if existing_visits:
                print(f"Route {route_name} already logged for stage {study_stage}, skipping")
                return True
            
            # Create log entry
            timestamp = datetime.now()
            log_entry = {
                'participant_id': participant_id,
                'route': route_name,
                'study_stage': study_stage,
                'timestamp': timestamp.isoformat(),
                'timestamp_unix': timestamp.timestamp(),
                'development_mode': development_mode
            }
            
            # Add session data if provided
            if session_data:
                log_entry['session_data'] = session_data
            
            # Add to logs
            logs_data['visits'].append(log_entry)
            
            # Write updated logs
            with open(log_file_path, 'w', encoding='utf-8') as f:
                json.dump(logs_data, f, indent=2, ensure_ascii=False)
            
            # Commit the log entry
            kwargs = self._get_subprocess_kwargs()
            kwargs["timeout"] = 5
            subprocess.run(['git', 'add', 'session_log.json'], **kwargs)
            
            commit_message = f"Log route visit: {route_name} (stage {study_stage}) at {timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
            kwargs["timeout"] = 10
            result = subprocess.run(['git', 'commit', '-m', commit_message], **kwargs)
            
            if result.returncode == 0:
                print(f"Successfully logged route visit: {route_name} for participant {participant_id}, stage {study_stage}")
                
                # Push to remote if token is available
                if github_token and github_org:
                    self.push_logs_to_remote(participant_id, development_mode, github_token, github_org)
                
                return True
            else:
                print(f"Failed to commit log entry. Error: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"Error logging route visit: {str(e)}")
            return False
        finally:
            try:
                os.chdir(original_cwd)
            except Exception as e:
                print(f"Warning: Failed to restore working directory: {str(e)}")
    
    def push_logs_to_remote(self, participant_id: str, development_mode: bool,
                          github_token: str, github_org: str) -> bool:
        """
        Push logs to remote repository on the logging branch.
        
        Args:
            participant_id: The participant's unique identifier
            development_mode: Whether running in development mode
            github_token: GitHub personal access token
            github_org: GitHub organization name
        
        Returns:
            True if successful, False otherwise
        """
        logs_path = self.get_logs_directory_path(participant_id, development_mode)
        original_cwd = os.getcwd()
        
        try:
            os.chdir(logs_path)
            
            # For now, we'll use the same repository structure but on logging branch
            # In production, you might want to set up a separate logs repository
            repo_name = f"study-{participant_id}"
            authenticated_url = self.github_service.get_authenticated_repo_url(repo_name, github_token, github_org)
            
            # Check if remote exists
            kwargs = self._get_subprocess_kwargs()
            kwargs["timeout"] = 5
            result = subprocess.run(['git', 'remote'], **kwargs)
            
            if 'origin' not in result.stdout:
                # Add remote
                kwargs["timeout"] = 10
                subprocess.run(['git', 'remote', 'add', 'origin', authenticated_url], **kwargs)
            else:
                # Update remote URL
                kwargs["timeout"] = 10
                subprocess.run(['git', 'remote', 'set-url', 'origin', authenticated_url], **kwargs)
            
            # Push logging branch
            kwargs["timeout"] = 30
            result = subprocess.run(['git', 'push', 'origin', 'logging'], **kwargs)
            
            if result.returncode == 0:
                print(f"Successfully pushed logs to remote for participant {participant_id}")
                return True
            else:
                print(f"Failed to push logs to remote. Error: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"Error pushing logs to remote: {str(e)}")
            return False
        finally:
            try:
                os.chdir(original_cwd)
            except Exception as e:
                print(f"Warning: Failed to restore original working directory: {str(e)}")
    
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
        try:
            # Ensure logging repository exists
            if not self.ensure_logging_repository(participant_id, development_mode, github_token, github_org):
                print(f"Failed to ensure logging repository for participant {participant_id}")
                return False
            
            logs_path = self.get_logs_directory_path(participant_id, development_mode)
            log_file_path = os.path.join(logs_path, 'stage_transitions.json')
            original_cwd = os.getcwd()
            
            # Switch to logs directory
            os.chdir(logs_path)
            
            # Ensure we're on logging branch
            kwargs = self._get_subprocess_kwargs()
            kwargs["timeout"] = 5
            subprocess.run(['git', 'checkout', 'logging'], **kwargs)
            
            # Load existing transitions or create new structure
            transitions_data = {'transitions': []}
            if os.path.exists(log_file_path):
                try:
                    with open(log_file_path, 'r', encoding='utf-8') as f:
                        transitions_data = json.load(f)
                except (json.JSONDecodeError, FileNotFoundError):
                    print("Could not read existing transitions file, creating new one")
            
            # Check if this transition has already been logged
            transition_key = f"stage_{from_stage}_to_{to_stage}"
            existing_transitions = [t for t in transitions_data['transitions'] 
                                  if t.get('from_stage') == from_stage and t.get('to_stage') == to_stage]
            
            if existing_transitions:
                print(f"Transition {transition_key} already logged, skipping")
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
                print(f"Successfully logged stage transition: {transition_key} for participant {participant_id}")
                
                # Push to remote if token is available
                if github_token and github_org:
                    self.push_logs_to_remote(participant_id, development_mode, github_token, github_org)
                
                return True
            else:
                print(f"Failed to commit transition entry. Error: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"Error logging stage transition: {str(e)}")
            return False
        finally:
            try:
                os.chdir(original_cwd)
            except Exception as e:
                print(f"Warning: Failed to restore working directory: {str(e)}")
    
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
            print(f"Error reading stage transition history: {str(e)}")
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
                print(f"VS Code workspace storage not found at: {vscode_storage_path}")
                return False
            
            # Ensure logging repository exists
            if not self.ensure_logging_repository(participant_id, development_mode, github_token, github_org):
                print("Failed to ensure logging repository exists")
                return False
            
            logs_path = self.get_logs_directory_path(participant_id, development_mode)
            original_cwd = os.getcwd()
            
            # Switch to logs directory
            os.chdir(logs_path)
            
            # Ensure we're on logging branch
            kwargs = self._get_subprocess_kwargs()
            kwargs["timeout"] = 5
            subprocess.run(['git', 'checkout', 'logging'], **kwargs)
            
            # Create vscode-storage directory if it doesn't exist
            vscode_logs_dir = os.path.join(logs_path, 'vscode-storage')
            if not os.path.exists(vscode_logs_dir):
                os.makedirs(vscode_logs_dir)
            
            # Create timestamped archive filename
            timestamp = datetime.now()
            archive_filename = f"workspace_storage_stage{study_stage}_{timestamp.strftime('%Y%m%d_%H%M%S')}.zip"
            archive_path = os.path.join(vscode_logs_dir, archive_filename)
            
            # Create zip archive of workspace storage
            print(f"Creating VS Code workspace storage archive: {archive_filename}")
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
                            print(f"Skipping file due to permission error: {file_path} - {e}")
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
                print(f"Successfully saved VS Code workspace storage for stage {study_stage}")
                return True
            else:
                print(f"Failed to commit VS Code workspace storage: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"Error saving VS Code workspace storage: {str(e)}")
            return False
        finally:
            try:
                os.chdir(original_cwd)
            except Exception as e:
                print(f"Error returning to original directory: {str(e)}")


class SessionTracker:
    """
    Manages session-based tracking to prevent duplicate logging.
    """
    
    @staticmethod
    def should_log_route(session: Dict, route_name: str, study_stage: int) -> bool:
        """
        Check if a route should be logged (i.e., if this is the first visit).
        Uses session data to track which routes have been visited.
        
        Args:
            session: Flask session object
            route_name: Name of the route
            study_stage: Current study stage
        
        Returns:
            True if route should be logged, False if already logged
        """
        session_key = f'logged_routes_stage{study_stage}'
        logged_routes = session.get(session_key, [])
        
        route_key = f"{route_name}_stage{study_stage}"
        return route_key not in logged_routes
    
    @staticmethod
    def mark_route_as_logged(session: Dict, route_name: str, study_stage: int) -> None:
        """
        Mark a route as having been logged in the session.
        
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
