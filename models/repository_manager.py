"""
Repository management for the coding study Flask application.
Handles Git operations, repository setup, VS Code integration, and file operations.
"""

import os
import shutil
import subprocess
import platform
from datetime import datetime
from typing import Optional, Dict, Any

from .github_service import GitHubService


class RepositoryManager:
    """
    Manages Git repositories for study participants.
    """
    
    def __init__(self, github_service: GitHubService):
        """
        Initialize RepositoryManager with GitHub service.
        
        Args:
            github_service: GitHubService instance for GitHub operations
        """
        self.github_service = github_service
    
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
        
        return kwargs
    
    def get_repository_path(self, participant_id: str, development_mode: bool) -> str:
        """
        Get the path to the participant's repository.
        
        Args:
            participant_id: The participant's unique identifier
            development_mode: Whether running in development mode
        
        Returns:
            The absolute path to the repository
        """
        if development_mode:
            current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            workspace_path = current_dir
            repo_name = f"study-{participant_id}"
            repo_path = os.path.join(workspace_path, repo_name)
        else:
            home_dir = os.path.expanduser("~")
            workspace_path = os.path.join(home_dir, "workspace")
            repo_name = f"study-{participant_id}"
            repo_path = os.path.join(workspace_path, repo_name)
        
        return os.path.normpath(repo_path)
    
    def check_and_clone_repository(self, participant_id: str, development_mode: bool, 
                                 github_token: Optional[str], github_org: str) -> bool:
        """
        Check if the GitHub repository for the participant exists in the workspace directory.
        If not, clone it to that location.
        
        Args:
            participant_id: The participant's unique identifier
            development_mode: Whether running in development mode
            github_token: GitHub personal access token (optional)
            github_org: GitHub organization name
        
        Returns:
            True if successful, False otherwise
        """
        if development_mode:
            # In development mode, use current directory
            current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            workspace_path = current_dir
            repo_name = f"study-{participant_id}"
            repo_path = os.path.join(workspace_path, repo_name)
            print(f"Development mode: Using local directory for repository: {repo_path}")
        else:
            # Use user's home directory with a workspace folder
            home_dir = os.path.expanduser("~")
            workspace_path = os.path.join(home_dir, "workspace")
            repo_name = f"study-{participant_id}"
            repo_path = os.path.join(workspace_path, repo_name)
        
        # Get authenticated repository URL
        repo_url = self.github_service.get_authenticated_repo_url(repo_name, github_token, github_org)
        
        # Normalize paths for Windows
        workspace_path = os.path.normpath(workspace_path)
        repo_path = os.path.normpath(repo_path)
        
        try:
            # Create workspace directory if it doesn't exist (only needed in production mode)
            if not development_mode and not os.path.exists(workspace_path):
                os.makedirs(workspace_path)
                print(f"Created workspace directory: {workspace_path}")
            
            # Check if repository already exists
            if os.path.exists(repo_path) and os.path.isdir(repo_path):
                # Check if it's a valid git repository
                git_dir = os.path.join(repo_path, '.git')
                if os.path.exists(git_dir):
                    print(f"Repository already exists at: {repo_path}")
                    return True
                else:
                    print(f"Directory exists but is not a git repository: {repo_path}")
                    # Remove the directory if it's not a git repo
                    shutil.rmtree(repo_path)
            
            # Clone the repository
            print(f"Cloning repository from {repo_url} to {repo_path}")
            kwargs = self._get_subprocess_kwargs()
            kwargs['timeout'] = 60
            result = subprocess.run([
                'git', 'clone', repo_url, repo_path
            ], **kwargs)
            
            if result.returncode == 0:
                print(f"Successfully cloned repository to: {repo_path}")
                return True
            else:
                print(f"Failed to clone repository. Error: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            print("Git clone operation timed out")
            return False
        except Exception as e:
            print(f"Error checking/cloning repository: {str(e)}")
            return False
    
    def ensure_git_config(self, repo_path: str, participant_id: str) -> bool:
        """
        Ensure git config is set up for commits in the repository.
        
        Args:
            repo_path: Path to the repository
            participant_id: The participant's unique identifier
        
        Returns:
            True if successful, False otherwise
        """
        try:
            original_cwd = os.getcwd()
            os.chdir(repo_path)
            
            # Check if user.name is set
            kwargs = self._get_subprocess_kwargs()
            kwargs['timeout'] = 5
            result = subprocess.run([
                'git', 'config', 'user.name'
            ], **kwargs)
            
            if result.returncode != 0 or not result.stdout.strip():
                # Set user name
                kwargs = self._get_subprocess_kwargs()
                kwargs['timeout'] = 5
                subprocess.run([
                    'git', 'config', 'user.name', f'{participant_id}'
                ], **kwargs)
                print(f"Set git user.name for participant {participant_id}")
            
            # Check if user.email is set
            kwargs = self._get_subprocess_kwargs()
            kwargs['timeout'] = 5
            result = subprocess.run([
                'git', 'config', 'user.email'
            ], **kwargs)
            
            if result.returncode != 0 or not result.stdout.strip():
                # Set user email
                kwargs = self._get_subprocess_kwargs()
                kwargs['timeout'] = 5
                subprocess.run([
                    'git', 'config', 'user.email', f'{participant_id}@study.local'
                ], **kwargs)
                print(f"Set git user.email for participant {participant_id}")
                
            return True
            
        except Exception as e:
            print(f"Warning: Failed to set git config: {str(e)}")
            return False
        finally:
            try:
                os.chdir(original_cwd)
            except Exception as e:
                print(f"Warning: Failed to restore working directory: {str(e)}")
    
    def ensure_stage_branch(self, repo_path: str, study_stage: int) -> bool:
        """
        Ensure the correct branch exists and is checked out for the given study stage.
        Creates stage-1 or stage-2 branch and switches to it.
        
        Args:
            repo_path: Path to the repository
            study_stage: The study stage (1 or 2)
        
        Returns:
            True if successful, False otherwise
        """
        try:
            original_cwd = os.getcwd()
            os.chdir(repo_path)
            
            branch_name = f"stage-{study_stage}"
            
            # Check if the branch already exists locally
            kwargs = self._get_subprocess_kwargs()
            kwargs['timeout'] = 10
            result = subprocess.run([
                'git', 'branch', '--list', branch_name
            ], **kwargs)
            
            branch_exists_locally = branch_name in result.stdout
            
            if branch_exists_locally:
                # Branch exists locally - just switch to it
                print(f"Switching to existing local branch: {branch_name}")
                kwargs = self._get_subprocess_kwargs()
                kwargs['timeout'] = 10
                result = subprocess.run([
                    'git', 'checkout', branch_name
                ], **kwargs)
                
                if result.returncode != 0:
                    print(f"Failed to checkout local branch {branch_name}. Error: {result.stderr}")
                    return False
            else:
                # Branch doesn't exist - create it
                print(f"Creating new branch: {branch_name}")
                kwargs = self._get_subprocess_kwargs()
                kwargs['timeout'] = 10
                result = subprocess.run([
                    'git', 'checkout', '-b', branch_name
                ], **kwargs)
                
                if result.returncode != 0:
                    print(f"Failed to create branch {branch_name}. Error: {result.stderr}")
                    return False
            
            print(f"Successfully ensured branch {branch_name} is active for stage {study_stage}")
            return True
            
        except Exception as e:
            print(f"Error ensuring stage branch: {str(e)}")
            return False
        finally:
            try:
                os.chdir(original_cwd)
            except Exception as e:
                print(f"Warning: Failed to restore working directory: {str(e)}")
    
    def setup_repository_for_stage(self, participant_id: str, study_stage: int, 
                                 development_mode: bool, github_token: Optional[str], 
                                 github_org: str) -> bool:
        """
        Set up the repository for a specific study stage by ensuring the correct branch is active.
        This should be called when a participant starts working on a specific stage.
        
        Args:
            participant_id: The participant's unique identifier
            study_stage: The study stage (1 or 2)
            development_mode: Whether running in development mode
            github_token: GitHub personal access token (optional)
            github_org: GitHub organization name
        
        Returns:
            True if successful, False otherwise
        """
        repo_path = self.get_repository_path(participant_id, development_mode)
        
        if not os.path.exists(repo_path):
            print(f"Repository does not exist at: {repo_path}")
            return False
        
        # Ensure git config is set up
        self.ensure_git_config(repo_path, participant_id)
        
        # Ensure the correct stage branch is active
        if not self.ensure_stage_branch(repo_path, study_stage):
            print(f"Failed to set up branch for stage {study_stage}")
            return False
        
        print(f"Repository successfully set up for stage {study_stage}")
        return True
    
    def commit_code_changes(self, participant_id: str, study_stage: int, commit_message: str,
                          development_mode: bool, github_token: Optional[str], 
                          github_org: str) -> bool:
        """
        Commit any changes in the participant's repository with a descriptive message.
        Ensures the correct stage branch is being used and pushes to that branch.
        
        Args:
            participant_id: The participant's unique identifier
            study_stage: The study stage (1 or 2)
            commit_message: Message for the commit
            development_mode: Whether running in development mode
            github_token: GitHub personal access token (optional)
            github_org: GitHub organization name
        
        Returns:
            True if successful, False otherwise
        """
        repo_path = self.get_repository_path(participant_id, development_mode)
        original_cwd = os.getcwd()  # Save current working directory
        
        try:
            # Check if repository exists
            if not os.path.exists(repo_path):
                print(f"Repository does not exist at: {repo_path}")
                return False
            
            # Check if it's a valid git repository
            git_dir = os.path.join(repo_path, '.git')
            if not os.path.exists(git_dir):
                print(f"Not a valid git repository: {repo_path}")
                return False
            
            # Ensure git config is set up
            self.ensure_git_config(repo_path, participant_id)
            
            # Change to repository directory
            os.chdir(repo_path)
            
            # Ensure we're on the correct stage branch
            if not self.ensure_stage_branch(repo_path, study_stage):
                print(f"Failed to ensure stage branch for stage {study_stage}")
                return False
            
            # Add all changes
            kwargs = self._get_subprocess_kwargs()
            kwargs['timeout'] = 10
            result = subprocess.run([
                'git', 'add', '.'
            ], **kwargs)
            
            if result.returncode != 0:
                print(f"Failed to add changes. Error: {result.stderr}")
                return False
            
            # Create timestamp for commit
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            full_commit_message = f"[Stage {study_stage}] {commit_message} - {timestamp}"
            
            # Commit changes
            kwargs = self._get_subprocess_kwargs()
            kwargs['timeout'] = 10
            result = subprocess.run([
                'git', 'commit', '-m', full_commit_message
            ], **kwargs)
            
            if result.returncode != 0:
                print(f"Failed to commit changes. Error: {result.stderr}")
                return False
            
            print(f"Successfully committed changes: {full_commit_message}")
            
            # Push changes to remote repository if we have authentication
            if github_token:
                # Set up the authenticated remote URL
                repo_name = f"study-{participant_id}"
                authenticated_url = self.github_service.get_authenticated_repo_url(repo_name, github_token, github_org)
                
                # Update the origin URL to use authentication
                result = subprocess.run([
                    'git', 'remote', 'set-url', 'origin', authenticated_url
                ], **self._get_subprocess_kwargs(), timeout=10)
                
                if result.returncode != 0:
                    print(f"Warning: Failed to set authenticated remote URL. Error: {result.stderr}")
                
                # Push changes to the stage-specific branch
                branch_name = f"stage-{study_stage}"
                result = subprocess.run([
                    'git', 'push', 'origin', branch_name
                ], **self._get_subprocess_kwargs(), timeout=30)
                
                if result.returncode == 0:
                    print(f"Successfully pushed changes to remote repository branch: {branch_name}")
                else:
                    print(f"Warning: Failed to push changes to remote repository branch {branch_name}. Error: {result.stderr}")
            else:
                print("No GitHub token provided - changes committed locally only")
            
            return True
            
        except subprocess.TimeoutExpired:
            print("Git operation timed out")
            return False
        except Exception as e:
            print(f"Error committing code changes: {str(e)}")
            return False
        finally:
            # Always restore the original working directory
            try:
                os.chdir(original_cwd)
            except Exception as e:
                print(f"Warning: Failed to restore original working directory: {str(e)}")
    
    def push_code_changes(self, participant_id: str, study_stage: int, development_mode: bool,
                        github_token: Optional[str], github_org: str) -> bool:
        """
        Push committed changes to the remote repository on the correct stage branch.
        
        Args:
            participant_id: The participant's unique identifier
            study_stage: The study stage (1 or 2)
            development_mode: Whether running in development mode
            github_token: GitHub personal access token (optional)
            github_org: GitHub organization name
        
        Returns:
            True if successful, False otherwise
        """
        repo_path = self.get_repository_path(participant_id, development_mode)
        original_cwd = os.getcwd()  # Save current working directory
        
        try:
            # Check if repository exists
            if not os.path.exists(repo_path):
                print(f"Repository does not exist at: {repo_path}")
                return False
            
            # Check if it's a valid git repository
            git_dir = os.path.join(repo_path, '.git')
            if not os.path.exists(git_dir):
                print(f"Not a valid git repository: {repo_path}")
                return False
            
            # Change to repository directory
            os.chdir(repo_path)
            
            # Ensure we're on the correct stage branch
            if not self.ensure_stage_branch(repo_path, study_stage):
                print(f"Failed to ensure stage branch for stage {study_stage}")
                return False
            
            # Set up the authenticated remote URL if we have a token
            if github_token:
                repo_name = f"study-{participant_id}"
                authenticated_url = self.github_service.get_authenticated_repo_url(repo_name, github_token, github_org)
                
                # Update the origin URL to use authentication
                result = subprocess.run([
                    'git', 'remote', 'set-url', 'origin', authenticated_url
                ], **self._get_subprocess_kwargs(), timeout=10)
                
                if result.returncode != 0:
                    print(f"Warning: Failed to set authenticated remote URL. Error: {result.stderr}")
            
            # Push changes to the stage-specific branch
            branch_name = f"stage-{study_stage}"
            result = subprocess.run([
                'git', 'push', 'origin', branch_name
            ], **self._get_subprocess_kwargs(), timeout=30)
            
            if result.returncode == 0:
                print(f"Successfully pushed changes to remote repository branch: {branch_name} for participant {participant_id}")
                return True
            else:
                print(f"Failed to push changes to remote repository branch {branch_name}. Error: {result.stderr}")
                return False
            
        except subprocess.TimeoutExpired:
            print("Git push operation timed out")
            return False
        except Exception as e:
            print(f"Error pushing code changes: {str(e)}")
            return False
        finally:
            # Always restore the original working directory
            try:
                os.chdir(original_cwd)
            except Exception as e:
                print(f"Warning: Failed to restore original working directory: {str(e)}")


class VSCodeManager:
    """
    Manages VS Code integration for opening repositories.
    """
    
    def __init__(self, repository_manager: RepositoryManager):
        """
        Initialize VSCodeManager with repository manager.
        
        Args:
            repository_manager: RepositoryManager instance for repository operations
        """
        self.repository_manager = repository_manager
    
    def open_vscode_with_repository(self, participant_id: str, development_mode: bool,
                                  study_stage: Optional[int] = None) -> bool:
        """
        Open VS Code with the participant's cloned repository.
        If study_stage is provided, ensures the correct branch is active before opening.
        
        Args:
            participant_id: The participant's unique identifier
            development_mode: Whether running in development mode
            study_stage: Study stage to ensure correct branch (optional)
        
        Returns:
            True if successful, False otherwise
        """
        # Get the repository path
        repo_path = self.repository_manager.get_repository_path(participant_id, development_mode)
        
        # Normalize path
        repo_path = os.path.normpath(repo_path)
        
        try:
            # Check if repository exists
            if not os.path.exists(repo_path):
                print(f"Repository does not exist at: {repo_path}")
                return False
            
            # If study_stage is provided, ensure the correct branch is active
            if study_stage is not None:
                if not self.repository_manager.ensure_stage_branch(repo_path, study_stage):
                    print(f"Warning: Failed to ensure correct branch for stage {study_stage}")
            
            # Try to open VS Code with the repository
            print(f"Opening VS Code with repository: {repo_path}")
            
            # Use 'code' command to open VS Code with the repository folder
            kwargs = self._get_subprocess_kwargs()
            kwargs['timeout'] = 10
            result = subprocess.run([
                'code', repo_path
            ], **kwargs)
            
            if result.returncode == 0:
                print(f"Successfully opened VS Code with repository: {repo_path}")
                return True
            else:
                print(f"Failed to open VS Code. Error: {result.stderr}")
                # Try alternative method for macOS
                try:
                    kwargs = self._get_subprocess_kwargs()
                    kwargs['timeout'] = 10
                    result = subprocess.run([
                        'open', '-a', 'Visual Studio Code', repo_path
                    ], **kwargs)
                    
                    if result.returncode == 0:
                        print(f"Successfully opened VS Code using 'open' command: {repo_path}")
                        return True
                    else:
                        print(f"Failed to open VS Code with 'open' command. Error: {result.stderr}")
                        return False
                except Exception as e:
                    print(f"Error trying 'open' command: {str(e)}")
                    return False
                
        except subprocess.TimeoutExpired:
            print("VS Code open operation timed out")
            return False
        except FileNotFoundError:
            print("VS Code ('code' command) not found in PATH. Please ensure VS Code is installed and the 'code' command is available.")
            return False
        except Exception as e:
            print(f"Error opening VS Code: {str(e)}")
            return False
