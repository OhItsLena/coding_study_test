import os
import json
import subprocess
import platform
import shutil
import time
import logging

import time
import threading
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional

try:
    import pyperclip
except ImportError:
    pyperclip = None

# Get logger for this module
logger = logging.getLogger(__name__)

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
            
            # Check if OBS is now running with multiple attempts
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

                # Remove OBS safe_mode file to prevent safe mode prompt
                try:
                    appdata = os.environ.get('APPDATA')
                    if appdata:
                        safe_mode_path = os.path.join(appdata, 'obs-studio', 'safe_mode')
                        if os.path.exists(safe_mode_path):
                            os.remove(safe_mode_path)
                            logger.info(f"Removed OBS safe_mode file: {safe_mode_path}")
                except Exception as e:
                    logger.warning(f"Failed to remove OBS safe_mode file: {e}")

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

            # Reset the recording state but preserve file path for Azure upload
            self.recording_process = None
            # Keep the file path available for Azure upload - update it if file was moved
            if moved_file_path:
                self.recording_file_path = moved_file_path
            # Don't reset recording_file_path to None here - let Azure upload handle cleanup
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
            # Clear the stored file path after successful upload
            self.recording_file_path = None
            # Optionally remove local file after successful upload
            # Uncomment the following lines if you want to delete local files after upload:
            # try:
            #     os.remove(file_to_upload)
            #     logger.info(f"🗑️  Local recording file removed: {file_to_upload}")
            # except Exception as e:
            #     logger.warning(f" Could not remove local file: {e}")
        else:
            logger.error(f"Failed to upload recording for participant {participant_id}, stage {study_stage}")
        
        return success
    

class FocusTracker:
    """
    Cross-platform window focus tracker for study participants.
    Logs application/window focus changes to a JSON file.
    """
    def __init__(self, logs_directory: str, study_stage: int, poll_interval: float = 1.0):
        self.logs_directory = logs_directory
        self.study_stage = study_stage
        self.poll_interval = poll_interval
        self.focus_log_path = os.path.join(logs_directory, f"focus_log_stage{study_stage}.json")
        self._stop_event = threading.Event()
        self._thread = None
        self._last_focus = None

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._track_focus_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2)

    def _track_focus_loop(self):
        while not self._stop_event.is_set():
            focus_info = self._get_active_window_info()
            # Only log if changed compared to last value
            if focus_info is not None:
                if not self._last_focus or not self._focus_equal(focus_info, self._last_focus):
                    self._log_focus_event(focus_info)
                    self._last_focus = focus_info
            time.sleep(self.poll_interval)

    def _focus_equal(self, a: dict, b: dict) -> bool:
        # Compare application and window_title for equality
        return a.get("application") == b.get("application") and a.get("window_title") == b.get("window_title")

    def _get_active_window_info(self) -> Optional[Dict[str, str]]:
        system = platform.system()
        try:
            if system == "Darwin":
                # macOS: Use osascript to get frontmost app and window title
                script = 'tell application "System Events"\nset frontApp to name of first application process whose frontmost is true\nend tell\nreturn frontApp'
                app_proc = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
                app_name = app_proc.stdout.strip() if app_proc.returncode == 0 else None
                # Window title (optional, may require accessibility permissions)
                title_script = 'tell application "System Events"\nset frontApp to first application process whose frontmost is true\ntry\nset window_name to name of front window of frontApp\non error\nset window_name to ""\nend try\nend tell\nreturn window_name'
                title_proc = subprocess.run(["osascript", "-e", title_script], capture_output=True, text=True)
                window_title = title_proc.stdout.strip() if title_proc.returncode == 0 else ""
                if app_name:
                    return {"application": app_name, "window_title": window_title}
            elif system == "Windows":
                try:
                    import win32gui
                    import win32process
                    import psutil
                    hwnd = win32gui.GetForegroundWindow()
                    window_title = win32gui.GetWindowText(hwnd)
                    _, pid = win32process.GetWindowThreadProcessId(hwnd)
                    proc = psutil.Process(pid)
                    app_name = proc.name()
                    return {"application": app_name, "window_title": window_title}
                except ImportError:
                    return None
            elif system == "Linux":
                # Linux: Use xdotool (must be installed)
                try:
                    win_id = subprocess.check_output(["xdotool", "getactivewindow"], text=True).strip()
                    window_title = subprocess.check_output(["xdotool", "getwindowname", win_id], text=True).strip()
                    # Try to get process name (optional, may require xprop)
                    app_name = ""
                    try:
                        wm_class = subprocess.check_output(["xprop", "-id", win_id, "WM_CLASS"], text=True)
                        if 'WM_CLASS' in wm_class:
                            app_name = wm_class.split('=')[-1].strip().strip('"')
                    except Exception:
                        pass
                    return {"application": app_name, "window_title": window_title}
                except Exception:
                    return None
        except Exception:
            return None
        return None

    def _log_focus_event(self, focus_info: Dict[str, str]):
        event = {
            "timestamp": datetime.now().isoformat(),
            "application": focus_info.get("application", ""),
            "window_title": focus_info.get("window_title", "")
        }
        try:
            if not os.path.exists(self.logs_directory):
                os.makedirs(self.logs_directory, exist_ok=True)
            if os.path.exists(self.focus_log_path):
                with open(self.focus_log_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            else:
                data = {"focus_events": []}
            data["focus_events"].append(event)
            with open(self.focus_log_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"Failed to log focus event: {e}")


class ClipboardTracker:
    """
    Cross-platform clipboard content tracker for study participants.
    Logs clipboard content changes to a JSON file.
    """
    def __init__(self, logs_directory: str, study_stage: int, poll_interval: float = 1.0):
        self.logs_directory = logs_directory
        self.study_stage = study_stage
        self.poll_interval = poll_interval
        self.clipboard_log_path = os.path.join(logs_directory, f"clipboard_log_stage{study_stage}.json")
        self._stop_event = threading.Event()
        self._thread = None
        self._last_clipboard_content = None

    def start(self):
        """Start the clipboard monitoring thread."""
        if self._thread and self._thread.is_alive():
            return
        
        if pyperclip is None:
            logger.warning("pyperclip package not available. Clipboard tracking disabled.")
            return
            
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._track_clipboard_loop, daemon=True)
        self._thread.start()
        logger.info(f"Started clipboard tracking for stage {self.study_stage}")

    def stop(self):
        """Stop the clipboard monitoring thread."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2)
        logger.info(f"Stopped clipboard tracking for stage {self.study_stage}")

    def _track_clipboard_loop(self):
        """Main loop for tracking clipboard changes."""
        try:
            while not self._stop_event.is_set():
                try:
                    # Get current clipboard content
                    current_content = self._get_clipboard_content()
                    
                    # Only log if content changed
                    if current_content is not None and current_content != self._last_clipboard_content:
                        self._log_clipboard_event(current_content)
                        self._last_clipboard_content = current_content
                        
                except Exception as e:
                    logger.warning(f"Error reading clipboard: {e}")
                
                time.sleep(self.poll_interval)
                
        except Exception as e:
            logger.error(f"Error in clipboard tracking loop: {e}")

    def _get_clipboard_content(self) -> Optional[str]:
        """Get current clipboard content."""
        try:
            if pyperclip:
                # Try to get text content from clipboard
                content = pyperclip.paste()
                if content and content.strip():
                    return content
        except Exception as e:
            logger.debug(f"Could not read clipboard content: {e}")
        return None

    def _log_clipboard_event(self, content: str):
        """Log a clipboard change event to the JSON file."""
        event = {
            "timestamp": datetime.now().isoformat(),
            "content": content,
            "content_length": len(content)
        }
        
        try:
            # Ensure logs directory exists
            if not os.path.exists(self.logs_directory):
                os.makedirs(self.logs_directory, exist_ok=True)
            
            # Load existing data or create new structure
            if os.path.exists(self.clipboard_log_path):
                with open(self.clipboard_log_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            else:
                data = {"clipboard_events": []}
            
            # Add new event
            data["clipboard_events"].append(event)
            
            # Write back to file
            with open(self.clipboard_log_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
            logger.debug(f"Logged clipboard event: {len(content)} characters")
            
        except Exception as e:
            logger.warning(f"Failed to log clipboard event: {e}")
