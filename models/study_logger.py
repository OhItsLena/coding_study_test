"""
Logging system for the coding study Flask application.
Handles route logging, session tracking, and study flow monitoring.
"""

import os
import json
import subprocess
from datetime import datetime
from typing import Dict, List, Any, Optional

from .github_service import GitHubService


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
                
                result = subprocess.run([
                    'git', 'init'
                ], capture_output=True, text=True, timeout=10)
                
                if result.returncode != 0:
                    print(f"Failed to initialize git repository in logs directory. Error: {result.stderr}")
                    return False
                
                # Set up git config (basic config for logging)
                subprocess.run(['git', 'config', 'user.name', f'{participant_id}'], capture_output=True, text=True, timeout=5)
                subprocess.run(['git', 'config', 'user.email', f'{participant_id}@study.local'], capture_output=True, text=True, timeout=5)
                
                # Create initial README
                readme_content = f"# Study Logs for Participant {participant_id}\n\nThis repository contains anonymized logs for study analysis.\n"
                readme_path = os.path.join(logs_path, 'README.md')
                with open(readme_path, 'w', encoding='utf-8') as f:
                    f.write(readme_content)
                
                # Initial commit
                subprocess.run(['git', 'add', 'README.md'], capture_output=True, text=True, timeout=5)
                subprocess.run(['git', 'commit', '-m', 'Initial commit for logging repository'], capture_output=True, text=True, timeout=5)
                
                print(f"Initialized logging repository at: {logs_path}")
            
            # Ensure we're on the logging branch
            os.chdir(logs_path)
            
            # Check if logging branch exists
            result = subprocess.run([
                'git', 'branch', '--list', 'logging'
            ], capture_output=True, text=True, timeout=10)
            
            if 'logging' not in result.stdout:
                # Create logging branch
                result = subprocess.run([
                    'git', 'checkout', '-b', 'logging'
                ], capture_output=True, text=True, timeout=10)
                
                if result.returncode != 0:
                    print(f"Failed to create logging branch. Error: {result.stderr}")
                    return False
                
                print("Created logging branch")
            else:
                # Switch to logging branch
                result = subprocess.run([
                    'git', 'checkout', 'logging'
                ], capture_output=True, text=True, timeout=10)
                
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
            subprocess.run(['git', 'checkout', 'logging'], capture_output=True, text=True, timeout=5)
            
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
            subprocess.run(['git', 'add', 'session_log.json'], capture_output=True, text=True, timeout=5)
            
            commit_message = f"Log route visit: {route_name} (stage {study_stage}) at {timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
            result = subprocess.run(['git', 'commit', '-m', commit_message], capture_output=True, text=True, timeout=10)
            
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
            result = subprocess.run(['git', 'remote'], capture_output=True, text=True, timeout=5)
            
            if 'origin' not in result.stdout:
                # Add remote
                subprocess.run(['git', 'remote', 'add', 'origin', authenticated_url], capture_output=True, text=True, timeout=10)
            else:
                # Update remote URL
                subprocess.run(['git', 'remote', 'set-url', 'origin', authenticated_url], capture_output=True, text=True, timeout=10)
            
            # Push logging branch
            result = subprocess.run(['git', 'push', 'origin', 'logging'], capture_output=True, text=True, timeout=30)
            
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
            subprocess.run(['git', 'checkout', 'logging'], capture_output=True, text=True, timeout=5)
            
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
            subprocess.run(['git', 'add', 'stage_transitions.json'], capture_output=True, text=True, timeout=5)
            
            commit_message = f"Mark stage transition: {transition_key} at {timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
            result = subprocess.run(['git', 'commit', '-m', commit_message], capture_output=True, text=True, timeout=10)
            
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
