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
import shutil
import zipfile
import signal
import time
from datetime import datetime
from typing import Dict, List, Any, Optional

from .github_service import GitHubService


class ScreenRecorder:
    """
    Handles screen recording using OBS Studio.
    """
    
    def __init__(self):
        """Initialize the screen recorder."""
        self.recording_process = None
        self.recording_file_path = None
    
    def _get_obs_executable_path(self) -> str:
        """
        Get the platform-specific OBS Studio executable path.
        
        Returns:
            Path to OBS Studio executable
        """
        system = platform.system()
        
        if system == "Windows":
            # Common OBS installation paths on Windows
            paths = [
                r"C:\Program Files\obs-studio\bin\64bit\obs64.exe",
                r"C:\Program Files (x86)\obs-studio\bin\32bit\obs32.exe",
                r"C:\Program Files (x86)\obs-studio\bin\64bit\obs64.exe"
            ]
            for path in paths:
                if os.path.exists(path):
                    return path
            # Try to find OBS in PATH
            return "obs64.exe"
        
        elif system == "Darwin":  # macOS
            # OBS Studio app bundle path on macOS
            obs_app_path = "/Applications/OBS.app/Contents/MacOS/OBS"
            if os.path.exists(obs_app_path):
                return obs_app_path
            # Try to find OBS in PATH
            return "obs"
        
        else:  # Linux
            # OBS executable on Linux
            return "obs"
    def start_recording(self, participant_id: str, study_stage: int, logs_directory: str) -> bool:
        """
        Start screen recording using OBS Studio with default configuration.
        
        Args:
            participant_id: The participant's unique identifier
            study_stage: The current study stage (1 or 2)
            logs_directory: Directory where the recording should be saved
            
        Returns:
            True if recording started successfully, False otherwise
        """
        # Check if OBS is already running before attempting to start
        if self.is_recording():
            print("Screen recording is already in progress - OBS is running")
            return True  # Return True since recording is already active
        
        # Also check for any existing OBS processes more thoroughly
        system = platform.system()
        if system == "Darwin":  # macOS
            try:
                # Kill any existing OBS processes to ensure clean start
                cleanup_cmd = ['pkill', '-f', '/Applications/OBS.app/Contents/MacOS/OBS']
                subprocess.run(cleanup_cmd, capture_output=True, text=True)
                print("Cleaned up any existing OBS processes")
                time.sleep(1)  # Give processes time to terminate
            except Exception as e:
                print(f"Error during OBS cleanup: {e}")
        
        try:
            # Create recordings directory if it doesn't exist
            recordings_dir = os.path.join(logs_directory, "recordings")
            os.makedirs(recordings_dir, exist_ok=True)
            
            # Generate recording filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            recording_filename = f"screen_recording_{participant_id}_stage{study_stage}_{timestamp}.mp4"
            self.recording_file_path = os.path.join(recordings_dir, recording_filename)
            
            # Get OBS executable path
            obs_executable = self._get_obs_executable_path()
            print(f"Using OBS executable: {obs_executable}")
            
            # OBS command for screen recording using default configuration
            system = platform.system()
            
            if system == "Windows":
                # Windows: Use OBS with minimal command line arguments
                obs_cmd = [
                    obs_executable,
                    "--startrecording",
                    "--minimize-to-tray"
                ]
            elif system == "Darwin":  # macOS
                # macOS: Use OBS with minimal command line arguments
                obs_cmd = [
                    obs_executable,
                    "--startrecording",
                    "--minimize"
                ]
            else:  # Linux
                # Linux: Use OBS with minimal command line arguments
                obs_cmd = [
                    obs_executable,
                    "--startrecording",
                    "--minimize-to-tray"
                ]
            
            # Start the recording process
            print(f"Starting OBS screen recording: {recording_filename}")
            print(f"Command: {' '.join(obs_cmd)}")
            
            recording_kwargs = self._get_recording_subprocess_kwargs()
            
            # Set working directory to OBS installation directory on Windows to fix locale issue
            if system == "Windows":
                obs_dir = os.path.dirname(obs_executable)
                if os.path.exists(obs_dir):
                    recording_kwargs['cwd'] = obs_dir
                    print(f"Setting OBS working directory to: {obs_dir}")
            
            self.recording_process = subprocess.Popen(obs_cmd, **recording_kwargs)
            print(f"OBS process started with PID: {self.recording_process.pid}")
            
            # Give OBS more time to start and stabilize
            print("Waiting for OBS to start...")
            time.sleep(3)
            
            # Check if OBS is now running with multiple attempts
            recording_active = False
            max_attempts = 3
            for attempt in range(max_attempts):
                recording_active = self.is_recording()
                print(f"OBS recording status check (attempt {attempt + 1}): {recording_active}")
                if recording_active:
                    break
                if attempt < max_attempts - 1:
                    print(f"OBS not detected yet, waiting 2 more seconds...")
                    time.sleep(2)
            
            if not recording_active:
                print("OBS failed to start recording - checking process status")
                if self.recording_process:
                    poll_result = self.recording_process.poll()
                    print(f"OBS process poll result: {poll_result}")
                    if poll_result is not None:
                        try:
                            stdout, stderr = self.recording_process.communicate(timeout=1)
                            print(f"OBS stdout: {stdout.decode()[:200] if stdout else 'None'}")
                            print(f"OBS stderr: {stderr.decode()[:200] if stderr else 'None'}")
                        except subprocess.TimeoutExpired:
                            print("OBS process still running but communication timed out")
                        except Exception as e:
                            print(f"Error communicating with OBS process: {e}")
                
                self.recording_process = None
                self.recording_file_path = None
                return False
            else:
                # OBS is running, but it may not be using our specified file path
                print(f"⚠️  OBS is recording but may be using its own default output location")
                print(f"   Expected file: {self.recording_file_path}")
                print(f"   OBS may save to: ~/Movies/ with its own naming convention")
            
            print(f"✅ OBS screen recording started successfully for participant {participant_id}, stage {study_stage}")
            return True
            
        except FileNotFoundError:
            print("❌ OBS Studio not found. Please install OBS Studio and make sure it's accessible.")
            self.recording_process = None
            self.recording_file_path = None
            return False
        except Exception as e:
            print(f"❌ Failed to start OBS screen recording: {e}")
            self.recording_process = None
            self.recording_file_path = None
            return False
    
    def stop_recording(self) -> bool:
        """
        Stop the current OBS screen recording.
        
        Returns:
            True if recording stopped successfully, False otherwise
        """
        if not self.is_recording():
            print("No OBS screen recording in progress")
            return False
        
        try:
            print("Stopping OBS screen recording...")
            
            system = platform.system()
            # Simple subprocess kwargs for process control
            kwargs = {
                'capture_output': True,
                'text': True
            }
            if platform.system() == "Windows":
                kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
                kwargs['shell'] = True
            
            if system == "Windows":
                # On Windows, try to stop recording first using OBS command line, then quit
                obs_executable = self._get_obs_executable_path()
                obs_dir = os.path.dirname(obs_executable)
                
                # If OBS is still running, force close it
                check_cmd = ['powershell', '-Command', 'Get-Process obs64 -ErrorAction SilentlyContinue']
                check_result = subprocess.run(check_cmd, **kwargs)
                if check_result.returncode == 0:
                    print("OBS still running, force closing...")
                    force_stop_cmd = ['powershell', '-Command', 
                                    'Get-Process obs64 -ErrorAction SilentlyContinue | Stop-Process -Force']
                    subprocess.run(force_stop_cmd, **kwargs)
                    
            elif system == "Darwin":  # macOS
                # On macOS, use osascript to quit OBS gracefully or pkill as fallback
                try:
                    # Try graceful quit first
                    quit_cmd = ['osascript', '-e', 'tell application "OBS" to quit']
                    result = subprocess.run(quit_cmd, **kwargs, timeout=5)
                    if result.returncode != 0:
                        # Fallback to pkill with specific pattern
                        subprocess.run(['pkill', '-f', '/Applications/OBS.app/Contents/MacOS/OBS'], **kwargs)
                except subprocess.TimeoutExpired:
                    # Force kill if needed
                    subprocess.run(['pkill', '-9', '-f', '/Applications/OBS.app/Contents/MacOS/OBS'], **kwargs)
                    
            else:  # Linux
                # On Linux, try graceful shutdown then pkill
                try:
                    # Try sending TERM signal first
                    subprocess.run(['pkill', '-TERM', 'obs'], **kwargs)
                    time.sleep(2)
                    # Check if still running and force kill if needed
                    check_result = subprocess.run(['pgrep', 'obs'], **kwargs)
                    if check_result.returncode == 0:
                        subprocess.run(['pkill', '-9', 'obs'], **kwargs)
                except Exception:
                    pass
            
            # Wait a moment for OBS to fully stop
            time.sleep(2)
            
            print(f"OBS screen recording stopped successfully. File saved: {self.recording_file_path}")
            
            # Reset the recording state
            self.recording_process = None
            recording_file = self.recording_file_path
            self.recording_file_path = None
            
            return True
            
        except Exception as e:
            print(f"Failed to stop OBS screen recording: {e}")
            self.recording_process = None
            self.recording_file_path = None
            return False
    
    def is_recording(self) -> bool:
        """
        Check if OBS is currently recording.
        
        Returns:
            True if OBS recording is active, False otherwise
        """
        try:
            system = platform.system()
            # Simple subprocess kwargs for process checking
            kwargs = {
                'capture_output': True,
                'text': True
            }
            
            if system == "Windows":
                # For Windows, check if obs64 process is running
                check_cmd = ['powershell', '-Command', 'Get-Process obs64 -ErrorAction SilentlyContinue']
                if platform.system() == "Windows":
                    kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
                    kwargs['shell'] = True
                result = subprocess.run(check_cmd, **kwargs)
                is_running = result.returncode == 0
                
            elif system == "Darwin":  # macOS
                # For macOS, check specifically for the main OBS application process
                # Use more specific pattern to avoid matching obs-ffmpeg-mux
                check_cmd = ['pgrep', '-f', '/Applications/OBS.app/Contents/MacOS/OBS']
                result = subprocess.run(check_cmd, **kwargs)
                is_running = result.returncode == 0
                
                # Additional check: Look for obs-ffmpeg-mux which indicates active recording
                if is_running:
                    mux_check_cmd = ['pgrep', '-f', 'obs-ffmpeg-mux']
                    mux_result = subprocess.run(mux_check_cmd, **kwargs)
                    has_mux = mux_result.returncode == 0
                    print(f"OBS main process running: {is_running}, obs-ffmpeg-mux active: {has_mux}")
                    # Return true if either main process is running (OBS is open)
                    # The mux process indicates active recording but may not always be present
                    return is_running
                
            else:  # Linux
                # For Linux, check if obs process is running
                check_cmd = ['pgrep', 'obs']
                result = subprocess.run(check_cmd, **kwargs)
                is_running = result.returncode == 0
                
            return is_running
                
        except Exception as e:
            print(f"Error checking OBS recording status: {e}")
            return False
    
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
