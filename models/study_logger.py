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

import json
import logging
import os
import platform
import random
import shutil
import subprocess
import time
import zipfile
import threading
from datetime import datetime
from typing import Dict, List, Any, Optional

from .github_service import GitHubService

# Get logger for this module
logger = logging.getLogger(__name__)

from .github_service import GitHubService


class WindowFocusTracker:
    """
    Tracks window focus changes to monitor participant attention patterns.
    """
    
    def __init__(self):
        """Initialize the window focus tracker."""
        self.tracking = False
        self.tracking_thread = None
        self.focus_log = []
        self.last_active_window = None
        self.participant_id = None
        self.study_stage = None
        self.development_mode = None
    
    def _get_active_window_info(self) -> Dict[str, Any]:
        """
        Get information about the currently active window.
        
        Returns:
            Dictionary with window information or None if cannot determine
        """
        try:
            system = platform.system()
            
            if system == "Darwin":  # macOS
                # Use AppleScript to get active window - improved version with error handling
                script = '''
                try
                    tell application "System Events"
                        set frontApp to name of first application process whose frontmost is true
                        try
                            set frontWindow to name of front window of first application process whose frontmost is true
                        on error
                            set frontWindow to "Active Window"
                        end try
                    end tell
                    return frontApp & "|" & frontWindow
                on error errMsg
                    return "Error|" & errMsg
                end try
                '''
                result = subprocess.run(['osascript', '-e', script], 
                                      capture_output=True, text=True, timeout=3)
                if result.returncode == 0 and result.stdout.strip():
                    output = result.stdout.strip()
                    if output.startswith("Error|"):
                        logger.debug(f"AppleScript error: {output}")
                        # Fallback to simpler method
                        return self._get_active_window_macos_fallback()
                    else:
                        parts = output.split('|', 1)
                        app_name = parts[0] if parts else 'unknown'
                        window_title = parts[1] if len(parts) > 1 else 'Active Window'
                        
                        # Clean up common macOS app names
                        if app_name == 'Electron':
                            # Try to get more specific info for Electron apps
                            window_title = self._get_electron_app_details(window_title)
                        
                        return {
                            'app_name': app_name,
                            'window_title': window_title,
                            'platform': 'macOS'
                        }
                else:
                    logger.debug(f"AppleScript failed with return code {result.returncode}: {result.stderr}")
                    # Fallback to simpler method
                    return self._get_active_window_macos_fallback()
            
            elif system == "Windows":
                # Use Windows API through PowerShell
                script = '''
                Add-Type -TypeDefinition 'using System; using System.Runtime.InteropServices; public class Win32 { [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow(); [DllImport("user32.dll")] public static extern int GetWindowText(IntPtr hWnd, System.Text.StringBuilder text, int count); [DllImport("user32.dll", SetLastError=true)] public static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint lpdwProcessId); }'; $hwnd = [Win32]::GetForegroundWindow(); $title = New-Object System.Text.StringBuilder 256; [Win32]::GetWindowText($hwnd, $title, $title.Capacity) | Out-Null; $processId = 0; [Win32]::GetWindowThreadProcessId($hwnd, [ref]$processId) | Out-Null; $process = Get-Process -Id $processId -ErrorAction SilentlyContinue; Write-Output "$($process.ProcessName)|$($title.ToString())"
                '''
                result = subprocess.run(['powershell', '-Command', script], 
                                      capture_output=True, text=True, timeout=2)
                if result.returncode == 0 and result.stdout.strip():
                    parts = result.stdout.strip().split('|', 1)
                    return {
                        'app_name': parts[0] if parts else 'unknown',
                        'window_title': parts[1] if len(parts) > 1 else 'unknown',
                        'platform': 'Windows'
                    }
            
            else:  # Linux
                # Use xdotool for Linux
                try:
                    result = subprocess.run(['xdotool', 'getactivewindow', 'getwindowname'], 
                                          capture_output=True, text=True, timeout=2)
                    if result.returncode == 0:
                        window_title = result.stdout.strip()
                        # Get process name
                        wid_result = subprocess.run(['xdotool', 'getactivewindow'], 
                                                  capture_output=True, text=True, timeout=1)
                        if wid_result.returncode == 0:
                            wid = wid_result.stdout.strip()
                            pid_result = subprocess.run(['xdotool', 'getwindowpid', wid], 
                                                      capture_output=True, text=True, timeout=1)
                            if pid_result.returncode == 0:
                                pid = pid_result.stdout.strip()
                                # Use ps command instead of psutil to avoid dependency
                                ps_result = subprocess.run(['ps', '-p', pid, '-o', 'comm='], 
                                                         capture_output=True, text=True, timeout=1)
                                if ps_result.returncode == 0:
                                    app_name = ps_result.stdout.strip()
                                    return {
                                        'app_name': app_name,
                                        'window_title': window_title,
                                        'platform': 'Linux'
                                    }
                except (subprocess.TimeoutExpired, FileNotFoundError):
                    pass
            
            # If we get here, nothing worked, try fallback for macOS
            if system == "Darwin":
                return self._get_active_window_macos_fallback()
            
            return None
            
        except Exception as e:
            logger.debug(f"Error getting active window info: {e}")
            # For macOS, try fallback on any exception
            if platform.system() == "Darwin":
                return self._get_active_window_macos_fallback()
            return None
    
    def _get_active_window_macos_fallback(self) -> Optional[Dict[str, Any]]:
        """
        Fallback method for macOS when AppleScript fails.
        Uses alternative approaches to get active window info.
        
        Returns:
            Dictionary with window information or None if cannot determine
        """
        try:
            # Try using 'lsappinfo' command which is more reliable
            result = subprocess.run(['lsappinfo', 'info', '-only', 'name', '-app', 'front'], 
                                  capture_output=True, text=True, timeout=2)
            if result.returncode == 0 and result.stdout.strip():
                # Parse output like: "front={ "AppInfoProvider"=1; name="Visual Studio Code"; }"
                output = result.stdout.strip()
                import re
                match = re.search(r'name="([^"]+)"', output)
                if match:
                    app_name = match.group(1)
                    return {
                        'app_name': app_name,
                        'window_title': 'Active Window',  # Can't get title with this method
                        'platform': 'macOS'
                    }
            
            # Another fallback: try simpler AppleScript
            simple_script = '''
            tell application "System Events"
                set frontApp to name of first application process whose frontmost is true
            end tell
            return frontApp
            '''
            result = subprocess.run(['osascript', '-e', simple_script], 
                                  capture_output=True, text=True, timeout=2)
            if result.returncode == 0 and result.stdout.strip():
                app_name = result.stdout.strip()
                return {
                    'app_name': app_name,
                    'window_title': 'Active Window',
                    'platform': 'macOS'
                }
            
            # Final fallback: use ps to find active applications
            result = subprocess.run(['ps', 'aux'], capture_output=True, text=True, timeout=2)
            if result.returncode == 0:
                # This is a very basic fallback - just return that we have some app
                return {
                    'app_name': 'Unknown Application',
                    'window_title': 'Active Window', 
                    'platform': 'macOS'
                }
                
        except Exception as e:
            logger.debug(f"macOS fallback methods failed: {e}")
        
        return None
    
    def _focus_tracking_loop(self):
        """
        Main tracking loop that runs in a separate thread.
        """
        while self.tracking:
            try:
                current_window = self._get_active_window_info()
                
                if current_window and current_window != self.last_active_window:
                    # Window focus changed
                    timestamp = datetime.now()
                    
                    focus_event = {
                        'timestamp': timestamp.isoformat(),
                        'timestamp_unix': timestamp.timestamp(),
                        'app_name': current_window.get('app_name', 'unknown'),
                        'window_title': current_window.get('window_title', 'unknown'),
                        'platform': current_window.get('platform', 'unknown'),
                        'participant_id': self.participant_id,
                        'study_stage': self.study_stage,
                        'development_mode': self.development_mode
                    }
                    
                    self.focus_log.append(focus_event)
                    self.last_active_window = current_window
                    
                    # Keep log size manageable (last 1000 events)
                    if len(self.focus_log) > 1000:
                        self.focus_log = self.focus_log[-1000:]
                
                # Check every 2 seconds (not too frequent to avoid performance impact)
                time.sleep(2)
                
            except Exception as e:
                logger.debug(f"Error in focus tracking loop: {e}")
                time.sleep(5)  # Wait longer on error
    
    def start_tracking(self, participant_id: str, study_stage: int, 
                      development_mode: bool) -> bool:
        """
        Start tracking window focus changes.
        
        Args:
            participant_id: The participant's unique identifier
            study_stage: Current study stage
            development_mode: Whether in development mode
            
        Returns:
            True if tracking started successfully
        """
        if self.tracking:
            logger.info("Window focus tracking already active")
            return True
        
        try:
            self.participant_id = participant_id
            self.study_stage = study_stage
            self.development_mode = development_mode
            self.focus_log = []
            self.last_active_window = None
            
            # Get initial window state
            initial_window = self._get_active_window_info()
            if initial_window:
                timestamp = datetime.now()
                initial_event = {
                    'timestamp': timestamp.isoformat(),
                    'timestamp_unix': timestamp.timestamp(),
                    'app_name': initial_window.get('app_name', 'unknown'),
                    'window_title': initial_window.get('window_title', 'unknown'),
                    'platform': initial_window.get('platform', 'unknown'),
                    'participant_id': participant_id,
                    'study_stage': study_stage,
                    'development_mode': development_mode,
                    'initial_focus': True
                }
                self.focus_log.append(initial_event)
                self.last_active_window = initial_window
            
            # Start tracking thread
            self.tracking = True
            self.tracking_thread = threading.Thread(target=self._focus_tracking_loop, daemon=True)
            self.tracking_thread.start()
            
            logger.info(f"Started window focus tracking for participant {participant_id}, stage {study_stage}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start window focus tracking: {e}")
            self.tracking = False
            return False
    
    def stop_tracking(self) -> List[Dict]:
        """
        Stop tracking and return collected focus events.
        
        Returns:
            List of focus events collected during tracking
        """
        if not self.tracking:
            return []
        
        self.tracking = False
        
        # Wait for thread to finish (with timeout)
        if self.tracking_thread and self.tracking_thread.is_alive():
            self.tracking_thread.join(timeout=5)
        
        focus_events = self.focus_log.copy()
        self.focus_log = []
        
        logger.info(f"Stopped window focus tracking, collected {len(focus_events)} events")
        return focus_events
    
    def is_tracking(self) -> bool:
        """
        Check if focus tracking is currently active.
        
        Returns:
            True if tracking is active
        """
        return self.tracking


class ScreenRecorder:
    """
    Handles screen recording using OBS Studio.
    """
    
    def __init__(self):
        """Initialize the screen recorder."""
        self.recording_process = None
        self.recording_file_path = None
        self.recording_start_time = None
    
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
    
    def _get_obs_default_recording_paths(self) -> List[str]:
        """
        Get the platform-specific default OBS recording directories.
        
        Returns:
            List of possible default recording paths for OBS
        """
        system = platform.system()
        home_dir = os.path.expanduser("~")
        
        if system == "Windows":
            # Common default recording paths on Windows
            return [
                os.path.join(home_dir, "Videos"),
                os.path.join(home_dir, "Documents"),
                os.path.join(home_dir, "Desktop")
            ]
        
        elif system == "Darwin":  # macOS
            # Default recording paths on macOS
            return [
                os.path.join(home_dir, "Movies"),
                os.path.join(home_dir, "Desktop"),
                os.path.join(home_dir, "Documents")
            ]
        
        else:  # Linux
            # Default recording paths on Linux
            return [
                os.path.join(home_dir, "Videos"),
                os.path.join(home_dir, "Desktop"),
                os.path.join(home_dir, "Documents")
            ]
    
    def _find_latest_recording_file(self, participant_id: str, study_stage: int, recording_start_time: float) -> Optional[str]:
        """
        Find the latest recording file created by OBS in its default locations.
        
        Args:
            participant_id: The participant's unique identifier
            study_stage: The current study stage
            recording_start_time: Unix timestamp when recording started
            
        Returns:
            Path to the latest recording file, or None if not found
        """
        try:
            default_paths = self._get_obs_default_recording_paths()
            latest_file = None
            latest_time = recording_start_time  # Only consider files created after recording started
            
            # Common video file extensions used by OBS
            video_extensions = ['.mp4', '.mkv', '.flv', '.mov', '.avi']
            
            for directory in default_paths:
                if not os.path.exists(directory):
                    continue
                    
                for filename in os.listdir(directory):
                    file_path = os.path.join(directory, filename)
                    
                    # Skip directories and non-video files
                    if not os.path.isfile(file_path):
                        continue
                    
                    # Check if it's a video file
                    if not any(filename.lower().endswith(ext) for ext in video_extensions):
                        continue
                    
                    try:
                        # Get file modification time
                        file_mtime = os.path.getmtime(file_path)
                        
                        # Only consider files created/modified after recording started
                        if file_mtime > latest_time:
                            latest_file = file_path
                            latest_time = file_mtime
                            
                    except (OSError, PermissionError):
                        # Skip files we can't access
                        continue
            
            if latest_file:
                logger.info(f"Found latest recording file: {latest_file}")
            else:
                logger.info(f"No recording file found in default locations created after {datetime.fromtimestamp(recording_start_time)}")
            
            return latest_file
            
        except Exception as e:
            logger.info(f"Error finding latest recording file: {e}")
            return None
    
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
            logger.info("Screen recording is already in progress - OBS is running")
            return True  # Return True since recording is already active
        
        # Also check for any existing OBS processes more thoroughly
        system = platform.system()
        if system == "Darwin":  # macOS
            try:
                # Kill any existing OBS processes to ensure clean start
                cleanup_cmd = ['pkill', '-f', '/Applications/OBS.app/Contents/MacOS/OBS']
                subprocess.run(cleanup_cmd, capture_output=True, text=True)
                logger.info("Cleaned up any existing OBS processes")
                time.sleep(1)  # Give processes time to terminate
            except Exception as e:
                logger.info(f"Error during OBS cleanup: {e}")
        
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
            logger.info(f"Using OBS executable: {obs_executable}")
            
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
            
            # Record the start time for file tracking
            self.recording_start_time = time.time()
            
            # Start the recording process
            logger.info(f"Starting OBS screen recording: {recording_filename}")
            logger.info(f"Command: {' '.join(obs_cmd)}")
            
            recording_kwargs = self._get_recording_subprocess_kwargs()
            
            # Set working directory to OBS installation directory on Windows to fix locale issue
            if system == "Windows":
                obs_dir = os.path.dirname(obs_executable)
                if os.path.exists(obs_dir):
                    recording_kwargs['cwd'] = obs_dir
                    logger.info(f"Setting OBS working directory to: {obs_dir}")
            
            self.recording_process = subprocess.Popen(obs_cmd, **recording_kwargs)
            logger.info(f"OBS process started with PID: {self.recording_process.pid}")
            
            # Give OBS more time to start and stabilize
            logger.info("Waiting for OBS to start...")
            time.sleep(3)
            
            # Check if OBS is now recording with multiple attempts
            recording_active = False
            max_attempts = 3
            for attempt in range(max_attempts):
                recording_active = self.is_recording()
                logger.info(f"OBS recording status check (attempt {attempt + 1}): {recording_active}")
                if recording_active:
                    break
                if attempt < max_attempts - 1:
                    logger.info(f"OBS not detected yet, waiting 2 more seconds...")
                    time.sleep(2)
            
            if not recording_active:
                logger.info("OBS failed to start recording - checking process status")
                if self.recording_process:
                    poll_result = self.recording_process.poll()
                    logger.info(f"OBS process poll result: {poll_result}")
                    if poll_result is not None:
                        try:
                            stdout, stderr = self.recording_process.communicate(timeout=1)
                            logger.info(f"OBS stdout: {stdout.decode()[:200] if stdout else 'None'}")
                            logger.info(f"OBS stderr: {stderr.decode()[:200] if stderr else 'None'}")
                        except subprocess.TimeoutExpired:
                            logger.info("OBS process still running but communication timed out")
                        except Exception as e:
                            logger.info(f"Error communicating with OBS process: {e}")
                
                self.recording_process = None
                self.recording_file_path = None
                self.recording_start_time = None
                return False
            else:
                # OBS is running, but it may not be using our specified file path
                logger.warning(f" OBS is recording but may be using its own default output location")
                logger.info(f"   Expected file: {self.recording_file_path}")
                logger.info(f"   OBS may save to: ~/Movies/ with its own naming convention")
            
            logger.info(f"OBS screen recording started successfully for participant {participant_id}, stage {study_stage}")
            return True
            
        except FileNotFoundError:
            logger.info("❌ OBS Studio not found. Please install OBS Studio and make sure it's accessible.")
            self.recording_process = None
            self.recording_file_path = None
            self.recording_start_time = None
            return False
        except Exception as e:
            logger.error(f"Failed to start OBS screen recording: {e}")
            self.recording_process = None
            self.recording_file_path = None
            self.recording_start_time = None
            return False
    
    def stop_recording(self) -> bool:
        """
        Stop the current OBS screen recording.
        
        Returns:
            True if recording stopped successfully, False otherwise
        """
        if not self.is_recording():
            logger.info("No OBS screen recording in progress")
            return False
        
        try:
            logger.info("Stopping OBS screen recording...")
            
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
                    logger.info("OBS still running, force closing...")
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
            
            # Wait a moment for OBS to fully stop and save the file
            logger.info("Waiting for OBS to finish saving the recording file...")
            time.sleep(5)  # Give OBS more time to save the file
            
            # Try to find and move the recording file from default location
            moved_file_path = None
            if self.recording_start_time:
                # Extract participant_id and study_stage from the expected file path
                if self.recording_file_path:
                    expected_filename = os.path.basename(self.recording_file_path)
                    # Parse participant_id and stage from filename like: screen_recording_PARTICIPANT_stageN_TIMESTAMP.mp4
                    try:
                        parts = expected_filename.replace('screen_recording_', '').replace('.mp4', '').split('_')
                        if len(parts) >= 3:
                            participant_id = parts[0]
                            stage_part = [p for p in parts if p.startswith('stage')][0]
                            study_stage = int(stage_part.replace('stage', ''))
                            
                            # Find the latest recording file in default locations
                            source_file = self._find_latest_recording_file(participant_id, study_stage, self.recording_start_time)
                            
                            if source_file and os.path.exists(source_file):
                                try:
                                    # Ensure the destination directory exists
                                    dest_dir = os.path.dirname(self.recording_file_path)
                                    os.makedirs(dest_dir, exist_ok=True)
                                    
                                    # Move the file from default location to our recordings directory
                                    logger.info(f"Moving recording file from {source_file} to {self.recording_file_path}")
                                    shutil.move(source_file, self.recording_file_path)
                                    moved_file_path = self.recording_file_path
                                    logger.info(f"Successfully moved recording file to: {self.recording_file_path}")
                                    
                                except (OSError, PermissionError, shutil.Error) as e:
                                    logger.warning(f" Failed to move recording file: {e}")
                                    logger.info(f"   Recording remains at: {source_file}")
                                    moved_file_path = source_file
                            else:
                                logger.warning(f" Could not find recording file in default OBS locations")
                                logger.info(f"   Expected to find file created after: {datetime.fromtimestamp(self.recording_start_time)}")
                    except (ValueError, IndexError, AttributeError) as e:
                        logger.warning(f" Could not parse recording filename for file moving: {e}")
            
            final_file_location = moved_file_path or "default OBS location"
            logger.info(f"OBS screen recording stopped successfully. File location: {final_file_location}")
            
            # Reset the recording state
            self.recording_process = None
            recording_file = self.recording_file_path
            self.recording_file_path = None
            self.recording_start_time = None
            
            return True
            
        except Exception as e:
            logger.warning(f"Failed to stop OBS screen recording: {e}")
            self.recording_process = None
            self.recording_file_path = None
            self.recording_start_time = None
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
                    logger.info(f"OBS main process running: {is_running}, obs-ffmpeg-mux active: {has_mux}")
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
            logger.info(f"Error checking OBS recording status: {e}")
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
    
    def upload_to_azure_blob(self, file_path: str, blob_container: str = "recordings", 
                           storage_account: str = "codingstudybackup") -> bool:
        """
        Upload a recording file to Azure Blob Storage using azcopy.
        
        Args:
            file_path: Local path to the file to upload
            blob_container: Azure Blob Storage container name (default: "recordings")
            storage_account: Azure Storage account name (default: "codingstudybackup")
            
        Returns:
            True if upload was successful, False otherwise
        """
        if not file_path or not os.path.exists(file_path):
            logger.error(f"File not found for Azure upload: {file_path}")
            return False
        
        try:
            # Get the filename for the blob
            filename = os.path.basename(file_path)
            blob_url = f"https://{storage_account}.blob.core.windows.net/{blob_container}/{filename}"
            
            logger.info(f"Uploading {filename} to Azure Blob Storage...")
            
            # Get subprocess kwargs for cross-platform compatibility
            kwargs = self._get_recording_subprocess_kwargs()
            kwargs['timeout'] = 300  # 5 minute timeout for large files
            
            # Step 1: Login to Azure using managed identity
            logger.info("Authenticating with Azure using managed identity...")
            login_cmd = ['azcopy', 'login', '--identity']
            
            login_result = subprocess.run(login_cmd, **kwargs)
            if login_result.returncode != 0:
                logger.error(f"Azure login failed: {login_result.stderr}")
                return False
            
            logger.info("✅ Successfully authenticated with Azure")
            
            # Step 2: Upload the file
            logger.info(f"Copying file to blob: {blob_url}")
            copy_cmd = ['azcopy', 'copy', file_path, blob_url]
            
            copy_result = subprocess.run(copy_cmd, **kwargs)
            if copy_result.returncode != 0:
                logger.error(f"Azure upload failed: {copy_result.stderr}")
                return False
            
            logger.info(f"Successfully uploaded {filename} to Azure Blob Storage")
            logger.info(f"   Blob URL: {blob_url}")
            
            return True
            
        except subprocess.TimeoutExpired:
            logger.error(f"Azure upload timed out for file: {filename}")
            return False
        except FileNotFoundError:
            logger.info("❌ azcopy command not found. Please install Azure CLI and azcopy.")
            return False
        except Exception as e:
            logger.error(f"Error uploading to Azure Blob Storage: {e}")
            return False
    
    def upload_recording_to_azure(self, participant_id: str, study_stage: int) -> bool:
        """
        Upload the current recording file to Azure Blob Storage and optionally remove local file.
        
        Args:
            participant_id: The participant's unique identifier
            study_stage: The current study stage
            
        Returns:
            True if upload was successful, False otherwise
        """
        if not self.recording_file_path:
            logger.info("❌ No recording file path available for Azure upload")
            return False
        
        # Check if the file exists (it might have been moved by stop_recording)
        file_to_upload = None
        if os.path.exists(self.recording_file_path):
            file_to_upload = self.recording_file_path
        else:
            # Try to find the file in default OBS locations
            if self.recording_start_time:
                found_file = self._find_latest_recording_file(participant_id, study_stage, self.recording_start_time)
                if found_file and os.path.exists(found_file):
                    file_to_upload = found_file
                    logger.info(f"Found recording file at: {found_file}")
        
        if not file_to_upload:
            logger.info("❌ Recording file not found for Azure upload")
            return False
        
        # Upload to Azure
        success = self.upload_to_azure_blob(file_to_upload)
        
        if success:
            logger.info(f"Recording for participant {participant_id}, stage {study_stage} uploaded to Azure")
            # Optionally remove local file after successful upload
            # Uncomment the following lines if you want to delete local files after upload:
            # try:
            #     os.remove(file_to_upload)
            #     logger.info(f"🗑️  Local recording file removed: {file_to_upload}")
            # except Exception as e:
            #     logger.warning(f" Could not remove local file: {e}")
        
        return success
        

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
        self.window_focus_tracker = WindowFocusTracker()
        # Generate unique session ID for this app run
        self.session_id = self._generate_session_id()
    
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
        Start screen recording for the study session.
        
        Args:
            participant_id: The participant's unique identifier
            study_stage: The current study stage (1 or 2)
            development_mode: Whether running in development mode
            
        Returns:
            True if recording started successfully, False otherwise
        """
        # Skip screen recording in development mode
        if development_mode:
            logger.info("Screen recording disabled in development mode")
            return True
            
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
    
    def start_focus_tracking(self, participant_id: str, study_stage: int, 
                           development_mode: bool) -> bool:
        """
        Start tracking window focus changes for the study session.
        
        Args:
            participant_id: The participant's unique identifier
            study_stage: The current study stage
            development_mode: Whether running in development mode
            
        Returns:
            True if tracking started successfully
        """
        # Skip focus tracking in development mode to avoid interference
        if development_mode:
            logger.info("Window focus tracking disabled in development mode")
            return True
            
        return self.window_focus_tracker.start_tracking(participant_id, study_stage, development_mode)
    
    def stop_focus_tracking_and_save(self, participant_id: str, study_stage: int, 
                                   development_mode: bool, github_token: Optional[str] = None,
                                   github_org: Optional[str] = None) -> bool:
        """
        Stop focus tracking and save the collected events to logs.
        
        Args:
            participant_id: The participant's unique identifier
            study_stage: The study stage that just completed
            development_mode: Whether running in development mode
            github_token: Optional GitHub token for pushing logs
            github_org: Optional GitHub organization
            
        Returns:
            True if successful
        """
        if development_mode:
            logger.info("Window focus tracking was disabled in development mode")
            return True
        
        # Stop tracking and get events
        focus_events = self.window_focus_tracker.stop_tracking()
        
        if not focus_events:
            logger.info("No focus events to save")
            return True
        
        return self._save_focus_events(participant_id, study_stage, development_mode, 
                                     focus_events, github_token, github_org)
    
    def is_focus_tracking_active(self) -> bool:
        """
        Check if focus tracking is currently active.
        
        Returns:
            True if tracking is active
        """
        return self.window_focus_tracker.is_tracking()
    
    def _save_focus_events(self, participant_id: str, study_stage: int, 
                          development_mode: bool, focus_events: List[Dict],
                          github_token: Optional[str] = None, 
                          github_org: Optional[str] = None) -> bool:
        """
        Save focus events to the logging repository.
        
        Args:
            participant_id: The participant's unique identifier
            study_stage: The study stage
            development_mode: Whether running in development mode
            focus_events: List of focus events to save
            github_token: Optional GitHub token for pushing logs
            github_org: Optional GitHub organization
            
        Returns:
            True if successful
        """
        try:
            # Ensure logging repository exists
            if not self.ensure_logging_repository(participant_id, development_mode, github_token, github_org):
                logger.warning("Failed to ensure logging repository exists")
                return False
            
            logs_path = self.get_logs_directory_path(participant_id, development_mode)
            log_file_path = os.path.join(logs_path, f'window_focus_stage{study_stage}.json')
            original_cwd = os.getcwd()
            
            try:
                os.chdir(logs_path)
                
                # Ensure we're on the logging branch
                kwargs = self._get_subprocess_kwargs()
                kwargs["timeout"] = 5
                subprocess.run(['git', 'checkout', self.get_logging_branch_name()], **kwargs)
                
                # Create focus events data structure
                focus_data = {
                    'participant_id': participant_id,
                    'study_stage': study_stage,
                    'session_id': self.session_id,
                    'total_events': len(focus_events),
                    'tracking_started': focus_events[0]['timestamp'] if focus_events else None,
                    'tracking_ended': focus_events[-1]['timestamp'] if focus_events else None,
                    'events': focus_events
                }
                
                # Write focus events to file
                with open(log_file_path, 'w', encoding='utf-8') as f:
                    json.dump(focus_data, f, indent=2, ensure_ascii=False)
                
                # Commit the focus events
                filename = f'window_focus_stage{study_stage}.json'
                kwargs = self._get_subprocess_kwargs()
                kwargs["timeout"] = 5
                subprocess.run(['git', 'add', filename], **kwargs)
                
                commit_message = f"Save window focus events for stage {study_stage} ({len(focus_events)} events)"
                kwargs["timeout"] = 10
                result = subprocess.run(['git', 'commit', '-m', commit_message], **kwargs)
                
                if result.returncode == 0:
                    logger.info(f"Successfully saved {len(focus_events)} focus events for stage {study_stage}")
                    
                    # Push to remote if token is available
                    if github_token and github_org:
                        self.push_logs_to_remote(participant_id, development_mode, github_token, github_org)
                    
                    return True
                else:
                    logger.warning(f"Failed to commit focus events: {result.stderr}")
                    return False
                    
            finally:
                os.chdir(original_cwd)
                
        except Exception as e:
            logger.error(f"Error saving focus events: {e}")
            return False
    
    def _get_electron_app_details(self, window_title: str) -> str:
        """
        Get more specific details for Electron-based applications.
        
        Args:
            window_title: The current window title
            
        Returns:
            Enhanced window title with app context
        """
        # For Electron apps, the window title is often more descriptive than the app name
        # This is a placeholder that could be enhanced to detect specific Electron apps
        if window_title and window_title != "Active Window":
            return window_title
        return "Electron App Window"


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
