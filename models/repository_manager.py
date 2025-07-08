"""
Repository management for the coding study Flask application.
Handles Git operations, repository setup, VS Code integration, and file operations.
"""

import os
import shutil
import subprocess
import platform
import threading
import logging
from datetime import datetime
from typing import Optional, Dict, Any

from .github_service import GitHubService

# Get logger for this module
logger = logging.getLogger(__name__)


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
        # Repository locks to prevent concurrent access to the same repository
        self._repo_locks = {}
        self._locks_mutex = threading.Lock()
    
    def _get_repo_lock(self, repo_path: str) -> threading.RLock:
        """
        Get or create a reentrant lock for a specific repository path.
        
        Args:
            repo_path: Path to the repository
            
        Returns:
            Threading reentrant lock for the repository
        """
        with self._locks_mutex:
            if repo_path not in self._repo_locks:
                self._repo_locks[repo_path] = threading.RLock()
            return self._repo_locks[repo_path]
    
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
    
    def get_repository_path(self, participant_id: str, development_mode: bool, repo_type: str = "study") -> str:
        """
        Get the path to the participant's repository.
        
        Args:
            participant_id: The participant's unique identifier
            development_mode: Whether running in development mode
            repo_type: Type of repository ("study" or "tutorial")
        
        Returns:
            The absolute path to the repository
        """
        if development_mode:
            current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            workspace_path = current_dir
        else:
            home_dir = os.path.expanduser("~")
            workspace_path = os.path.join(home_dir, "workspace")
        
        if repo_type == "tutorial":
            repo_name = f"tutorial-{participant_id}"
        else:  # study
            repo_name = f"study-{participant_id}"
        
        repo_path = os.path.join(workspace_path, repo_name)
        return os.path.normpath(repo_path)
    
    def check_and_clone_repository(self, participant_id: str, development_mode: bool, 
                                 github_token: Optional[str], github_org: str, repo_type: str = "study") -> bool:
        """
        Check if the GitHub repository for the participant exists in the workspace directory.
        If not, clone it to that location.
        
        Args:
            participant_id: The participant's unique identifier
            development_mode: Whether running in development mode
            github_token: GitHub personal access token (optional)
            github_org: GitHub organization name
            repo_type: Type of repository ("study" or "tutorial")
        
        Returns:
            True if successful, False otherwise
        """
        repo_path = self.get_repository_path(participant_id, development_mode, repo_type)
        repo_name = f"study-{participant_id}"
        
        # Get authenticated repository URL
        repo_url = self.github_service.get_authenticated_repo_url(repo_name, github_token, github_org)
        
        if development_mode:
            logger.info(f"Development mode: Using local directory for repository: {repo_path}")
        
        # Get workspace path for directory creation
        workspace_path = os.path.dirname(repo_path)
        
        # Normalize paths for Windows
        workspace_path = os.path.normpath(workspace_path)
        repo_path = os.path.normpath(repo_path)
        
        try:
            # Create workspace directory if it doesn't exist (only needed in production mode)
            if not development_mode and not os.path.exists(workspace_path):
                os.makedirs(workspace_path)
                logger.info(f"Created workspace directory: {workspace_path}")
            
            # Check if repository already exists
            if os.path.exists(repo_path) and os.path.isdir(repo_path):
                # Check if it's a valid git repository
                git_dir = os.path.join(repo_path, '.git')
                if os.path.exists(git_dir):
                    logger.info(f"Repository already exists at: {repo_path}")
                    return True
                else:
                    logger.warning(f"Directory exists but is not a git repository: {repo_path}")
                    # Remove the directory if it's not a git repo
                    shutil.rmtree(repo_path)
            
            # Clone the repository
            logger.info(f"Cloning repository from {repo_url} to {repo_path}")
            kwargs = self._get_subprocess_kwargs()
            kwargs['timeout'] = 60
            result = subprocess.run([
                'git', 'clone', repo_url, repo_path
            ], **kwargs)
            
            if result.returncode == 0:
                logger.info(f"Successfully cloned repository to: {repo_path}")
                return True
            else:
                logger.error(f"Failed to clone repository. Error: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("Git clone operation timed out")
            return False
        except Exception as e:
            logger.error(f"Error checking/cloning repository: {str(e)}")
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
                logger.info(f"Set git user.name for participant {participant_id}")
            
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
                logger.info(f"Set git user.email for participant {participant_id}")
                
            return True
            
        except Exception as e:
            logger.warning(f"Failed to set git config: {str(e)}")
            return False
        finally:
            try:
                os.chdir(original_cwd)
            except Exception as e:
                logger.warning(f"Failed to restore working directory: {str(e)}")
    
    def ensure_branch(self, repo_path: str, branch_name: str, source_branch: str = None, 
                     participant_id: str = None, github_token: Optional[str] = None, 
                     github_org: str = None, skip_backup: bool = False) -> bool:
        """
        Ensure a specific branch exists and is checked out.
        Uses simplified, deterministic approach for creating branches from specified sources.
        Thread-safe with repository-level locking.
        
        Args:
            repo_path: Path to the repository
            branch_name: Name of the branch to ensure (e.g., 'stage-1', 'tutorial')
            source_branch: Source branch to create from if branch doesn't exist (optional)
                          If None, will try to create from remote branch with same name
            participant_id: Participant ID for backup operations (optional)
            github_token: GitHub token for backup operations (optional)
            github_org: GitHub organization for backup operations (optional)
            skip_backup: Skip backup operations (used when already on correct branch)
        
        Returns:
            True if successful, False otherwise
        """
        # Get repository-specific lock to prevent concurrent access
        repo_lock = self._get_repo_lock(repo_path)
        
        with repo_lock:
            try:
                original_cwd = os.getcwd()
                os.chdir(repo_path)
                
                logger.info(f"Setting up branch: {branch_name} (locked)")
                
                # Step 1: Check current branch to see if backup is needed
                kwargs = self._get_subprocess_kwargs()
                kwargs['timeout'] = 5
                result = subprocess.run(['git', 'branch', '--show-current'], **kwargs)
                current_branch = result.stdout.strip() if result.returncode == 0 else None
                
                # Step 2: Fetch latest remote refs
                kwargs['timeout'] = 15
                result = subprocess.run(['git', 'fetch', 'origin'], **kwargs)
                if result.returncode != 0:
                    logger.warning(f"Failed to fetch from remote: {result.stderr}")
                
                # Step 3: Check if the branch already exists locally
                result = subprocess.run(['git', 'branch', '--list', branch_name], **kwargs)
                branch_exists = branch_name in result.stdout
                
                if branch_exists and current_branch == branch_name:
                    # Already on the correct branch, no backup needed
                    logger.info(f"Already on correct branch {branch_name}")
                    return True
                
                if branch_exists:
                    # Branch exists, just switch to it
                    logger.info(f"Branch {branch_name} exists locally, switching to it")
                    result = subprocess.run(['git', 'checkout', branch_name], **kwargs)
                    if result.returncode != 0:
                        logger.warning(f"Failed to checkout existing branch {branch_name}: {result.stderr}")
                        return False
                    logger.info(f"Successfully switched to existing {branch_name}")
                    return True
                
                # Step 4: Create new branch from specified source
                if source_branch:
                    # Create from specified source branch
                    logger.info(f"Creating {branch_name} from {source_branch}")
                    
                    # Check if source branch exists (local or remote)
                    if source_branch.startswith('origin/'):
                        # Remote source branch
                        result = subprocess.run(['git', 'branch', '-r', '--list', source_branch], **kwargs)
                        if source_branch not in result.stdout:
                            logger.error(f"Error: {source_branch} branch not found. Cannot create {branch_name}.")
                            return False
                    else:
                        # Local source branch
                        result = subprocess.run(['git', 'branch', '--list', source_branch], **kwargs)
                        if source_branch not in result.stdout:
                            logger.error(f"Error: {source_branch} branch not found locally. Cannot create {branch_name}.")
                            return False
                    
                    # Create branch from source
                    result = subprocess.run(['git', 'checkout', '-b', branch_name, source_branch], **kwargs)
                    if result.returncode != 0:
                        logger.warning(f"Failed to create {branch_name} from {source_branch}: {result.stderr}")
                        return False
                    
                    logger.info(f"Successfully created {branch_name} from {source_branch}")
                else:
                    # Try to create from remote branch with same name
                    remote_branch = f"origin/{branch_name}"
                    result = subprocess.run(['git', 'branch', '-r', '--list', remote_branch], **kwargs)
                    if remote_branch in result.stdout:
                        # Create from remote branch
                        logger.info(f"Creating local {branch_name} branch from remote")
                        result = subprocess.run(['git', 'checkout', '-b', branch_name, remote_branch], **kwargs)
                        if result.returncode != 0:
                            logger.warning(f"Failed to create {branch_name} from remote: {result.stderr}")
                            return False
                        logger.info(f"Successfully created and switched to {branch_name} branch")
                    else:
                        logger.error(f"Error: {remote_branch} branch not found. {branch_name} branch must exist on remote or source_branch must be specified.")
                        return False
                
                logger.info(f"Successfully ensured branch {branch_name} is active")
                return True
                
            except Exception as e:
                logger.info(f"Error ensuring branch: {str(e)}")
                return False
            finally:
                try:
                    os.chdir(original_cwd)
                except Exception as e:
                    logger.warning(f"Failed to restore working directory: {str(e)}")

    def ensure_stage_branch(self, repo_path: str, study_stage: int, participant_id: str = None, 
                           github_token: Optional[str] = None, github_org: str = None, 
                           skip_backup: bool = False) -> bool:
        """
        Ensure the correct branch exists and is checked out for the given study stage.
        Uses simplified, deterministic approach:
        - stage-1: Always created from remote stage-1 branch
        - stage-2: Always created from remote stage-1 branch
        
        Args:
            repo_path: Path to the repository
            study_stage: The study stage (1 or 2)
            participant_id: Participant ID for backup operations (optional)
            github_token: GitHub token for backup operations (optional)
            github_org: GitHub organization for backup operations (optional)
            skip_backup: Skip backup operations (used when already on correct branch)
        
        Returns:
            True if successful, False otherwise
        """
        branch_name = f"stage-{study_stage}"
        
        if study_stage == 1:
            # Stage-1: Always create from remote stage-1 branch
            source_branch = "origin/stage-1"
        elif study_stage == 2:
            # Stage-2: Always create from remote stage-1 branch
            source_branch = "origin/stage-1"
        else:
            logger.error(f"Error: Unsupported study stage: {study_stage}")
            return False

        return self.ensure_branch(
            repo_path=repo_path,
            branch_name=branch_name,
            source_branch=source_branch,
            participant_id=participant_id,
            github_token=github_token,
            github_org=github_org,
            skip_backup=skip_backup
        )
    
    def setup_repository_for_stage(self, participant_id: str, study_stage: int, 
                                 development_mode: bool, github_token: Optional[str], 
                                 github_org: str) -> bool:
        """
        Set up the repository for a specific study stage by ensuring the correct branch is active.
        This should ONLY be called when a participant starts working on a stage from the task page.
        After this, participants are free to work on any branch they choose.
        
        Args:
            participant_id: The participant's unique identifier
            study_stage: The study stage (1 or 2)
            development_mode: Whether running in development mode
            github_token: GitHub personal access token (optional)
            github_org: GitHub organization name
        
        Returns:
            True if successful, False otherwise
        """
        repo_path = self.get_repository_path(participant_id, development_mode, "study")
        
        if not os.path.exists(repo_path):
            logger.info(f"Repository does not exist at: {repo_path}")
            return False
        
        # Ensure git config is set up
        self.ensure_git_config(repo_path, participant_id)
        
        # Ensure the correct stage branch is active (with backup support for initial setup)
        if not self.ensure_stage_branch(repo_path, study_stage, participant_id, github_token, github_org):
            logger.warning(f"Failed to set up branch for stage {study_stage}")
            return False
        
        logger.info(f"Repository successfully set up for stage {study_stage}")
        return True
    
    def commit_and_backup_all(self, participant_id: str, study_stage: Optional[int], commit_message: str,
                             development_mode: bool, github_token: Optional[str], 
                             github_org: str, repo_type: str = "study") -> bool:
        """
        Unified method to commit changes on current branch and backup all branches.
        This is the main method called when requirements are completed or timer expires.
        Can also be used for tutorial completion by passing study_stage=None and repo_type="tutorial".
        Thread-safe with repository-level locking.
        
        Args:
            participant_id: The participant's unique identifier
            study_stage: The study stage (1 or 2) - used for logging purposes (None for tutorial)
            commit_message: Message for the commit
            development_mode: Whether running in development mode
            github_token: GitHub personal access token (optional)
            github_org: GitHub organization name
            repo_type: Type of repository ("study" or "tutorial")
        
        Returns:
            True if successful, False otherwise
        """
        repo_path = self.get_repository_path(participant_id, development_mode, repo_type)
        
        # Get repository-specific lock to prevent concurrent access
        repo_lock = self._get_repo_lock(repo_path)
        
        with repo_lock:
            original_cwd = os.getcwd()
            
            try:
                # Check if repository exists
                if not os.path.exists(repo_path):
                    logger.info(f"Repository does not exist at: {repo_path}")
                    return False
                
                # Check if it's a valid git repository
                git_dir = os.path.join(repo_path, '.git')
                if not os.path.exists(git_dir):
                    logger.info(f"Not a valid git repository: {repo_path}")
                    return False
                
                # Ensure git config is set up
                self.ensure_git_config(repo_path, participant_id)
                
                # Change to repository directory
                os.chdir(repo_path)
                
                logger.info(f"Committing changes for {participant_id} (locked)")
                
                # Step 1: Commit any changes on the current branch
                success = self._commit_current_branch_changes(study_stage, commit_message)
                if not success:
                    logger.info("Failed to commit changes on current branch")
                    return False
                
                # Step 2: Push all branches to remote as backup (if we have authentication)
                if github_token:
                    success = self._push_all_branches_backup(participant_id, github_token, github_org, repo_type)
                    if not success:
                        logger.info("Warning: Failed to backup all branches to remote")
                        # Don't return False here - local commit succeeded
                else:
                    logger.info("No GitHub token provided - changes committed locally only")
                
                logger.info(f"Successfully completed commit and backup workflow for {participant_id}")
                return True
                
            except Exception as e:
                logger.info(f"Error in commit and backup workflow: {str(e)}")
                return False
            finally:
                try:
                    os.chdir(original_cwd)
                except Exception as e:
                    logger.warning(f"Failed to restore original working directory: {str(e)}")
    
    def _commit_current_branch_changes(self, study_stage: Optional[int], commit_message: str) -> bool:
        """
        Commit any changes on the current branch.
        
        Args:
            study_stage: The study stage for logging (optional, for tutorial use None)
            commit_message: Message for the commit
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Check if there are any changes to commit
            kwargs = self._get_subprocess_kwargs()
            kwargs['timeout'] = 10
            result = subprocess.run(['git', 'status', '--porcelain'], **kwargs)
            
            if result.returncode != 0:
                logger.warning(f"Failed to check git status. Error: {result.stderr}")
                return False
            
            has_changes = bool(result.stdout.strip())
            
            if not has_changes:
                logger.info("No changes to commit on current branch")
                return True
            
            # Get current branch name for logging
            result = subprocess.run(['git', 'branch', '--show-current'], **kwargs)
            current_branch = result.stdout.strip() if result.returncode == 0 else "unknown"
            
            # Add all changes
            result = subprocess.run(['git', 'add', '.'], **kwargs)
            if result.returncode != 0:
                logger.warning(f"Failed to add changes. Error: {result.stderr}")
                return False
            
            # Create commit message with timestamp
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            if study_stage is not None:
                full_commit_message = f"[Stage {study_stage}] {commit_message} - {timestamp}"
            else:
                full_commit_message = f"{commit_message} - {timestamp}"
            
            # Commit changes
            result = subprocess.run(['git', 'commit', '-m', full_commit_message], **kwargs)
            if result.returncode != 0:
                logger.warning(f"Failed to commit changes. Error: {result.stderr}")
                return False
            
            logger.info(f"Successfully committed changes on branch '{current_branch}': {full_commit_message}")
            return True
            
        except Exception as e:
            logger.info(f"Error committing current branch changes: {str(e)}")
            return False
    
    def _push_all_branches_backup(self, participant_id: str, github_token: str, github_org: str, repo_type: str = "study") -> bool:
        """
        Push all local branches to remote as backup.
        
        Args:
            participant_id: The participant's unique identifier
            github_token: GitHub personal access token
            github_org: GitHub organization name
            repo_type: Type of repository ("study" or "tutorial")
        
        Returns:
            True if successful, False otherwise
        """
        try:
            repo_name = f"study-{participant_id}"
            authenticated_url = self.github_service.get_authenticated_repo_url(repo_name, github_token, github_org)
            
            kwargs = self._get_subprocess_kwargs()
            kwargs['timeout'] = 10
            result = subprocess.run(['git', 'remote', 'set-url', 'origin', authenticated_url], **kwargs)
            if result.returncode != 0:
                logger.warning(f"Failed to set authenticated remote URL: {result.stderr}")
            
            # Get list of all local branches
            result = subprocess.run(['git', 'branch', '--format=%(refname:short)'], **kwargs)
            if result.returncode != 0:
                logger.warning(f"Failed to get list of local branches: {result.stderr}")
                return False
            
            local_branches = [branch.strip() for branch in result.stdout.strip().split('\n') if branch.strip()]
            
            if not local_branches:
                logger.info("No local branches found to backup")
                return True
            
            logger.info(f"Backing up {len(local_branches)} branches to remote...")
            
            # Push each branch with retry logic
            success_count = 0
            for branch in local_branches:
                if self._push_branch_with_retry(branch, max_retries=2):
                    success_count += 1
                    logger.info(f"Successfully backed up branch: {branch}")
                else:
                    logger.warning(f"Failed to backup branch: {branch}")
            
            logger.info(f"Backup completed: {success_count}/{len(local_branches)} branches backed up successfully")
            return success_count > 0  # Success if at least one branch was backed up
            
        except Exception as e:
            logger.info(f"Error backing up all branches: {str(e)}")
            return False
    
    def _push_branch_with_retry(self, branch_name: str, max_retries: int = 2) -> bool:
        """
        Push a specific branch with simple retry logic.
        
        Args:
            branch_name: Name of the branch to push
            max_retries: Maximum number of retry attempts
        
        Returns:
            True if successful, False otherwise
        """
        for attempt in range(max_retries):
            try:
                kwargs = self._get_subprocess_kwargs()
                kwargs['timeout'] = 30
                result = subprocess.run(['git', 'push', 'origin', branch_name], **kwargs)
                
                if result.returncode == 0:
                    return True
                else:
                    logger.info(f"Push failed for {branch_name} (attempt {attempt + 1}/{max_retries}): {result.stderr}")
                    if attempt < max_retries - 1:
                        # Try to fetch and retry on next attempt
                        fetch_result = subprocess.run(['git', 'fetch', 'origin'], **kwargs)
                        if fetch_result.returncode != 0:
                            logger.warning(f"Failed to fetch before retry: {fetch_result.stderr}")
                        
            except subprocess.TimeoutExpired:
                logger.info(f"Push timeout for {branch_name} (attempt {attempt + 1}/{max_retries})")
            except Exception as e:
                logger.info(f"Error pushing {branch_name} (attempt {attempt + 1}/{max_retries}): {str(e)}")
        
        return False

    def ensure_tutorial_branch(self, repo_path: str) -> bool:
        """
        Ensure tutorial branch is checked out.
        Uses simplified, deterministic approach: tutorial branch must exist on remote.
        
        Args:
            repo_path: Path to the repository
        
        Returns:
            True if successful, False otherwise
        """
        return self.ensure_branch(repo_path=repo_path, branch_name="tutorial")

    def setup_tutorial_repository(self, participant_id: str, development_mode: bool,
                                 github_token: str, github_org: str) -> bool:
        """
        Set up tutorial repository in a separate directory.
        Clones the tutorial repository to tutorial-{participant_id} directory.
        
        Args:
            participant_id: The participant ID
            development_mode: Whether in development mode
            github_token: GitHub authentication token
            github_org: GitHub organization name
            
        Returns:
            bool: Success status
        """
        try:
            # Clone tutorial repository to separate directory
            success = self.check_and_clone_repository(
                participant_id, development_mode, github_token, github_org, "tutorial"
            )
            if not success:
                logger.warning(f"Failed to clone tutorial repository")
                return False
            
            # Get tutorial repository path
            tutorial_repo_path = self.get_repository_path(participant_id, development_mode, "tutorial")
            
            # Ensure git config is set up
            if not self.ensure_git_config(tutorial_repo_path, participant_id):
                logger.warning(f"Failed to set up git config for tutorial")
                return False
            
            # Ensure we're on the tutorial branch (if it exists)
            self.ensure_tutorial_branch(tutorial_repo_path)
            
            logger.info(f"Tutorial repository successfully set up at: {tutorial_repo_path}")
            return True
            
        except Exception as e:
            logger.info(f"Error setting up tutorial repository: {str(e)}")
            return False

    def commit_tutorial_completion(self, participant_id: str, development_mode: bool,
                                 github_token: str, github_org: str) -> bool:
        """
        Commit tutorial completion to the tutorial repository.
        Uses the unified commit and backup workflow for the tutorial repository.
        
        Args:
            participant_id: The participant ID
            development_mode: Whether in development mode
            github_token: GitHub authentication token
            github_org: GitHub organization name
            
        Returns:
            bool: Success status
        """
        try:
            commit_message = f"Tutorial completion - {participant_id}"
            
            # Use the unified commit and backup method for tutorial repository
            return self.commit_and_backup_all(
                participant_id=participant_id,
                study_stage=None,  # None indicates tutorial
                commit_message=commit_message,
                development_mode=development_mode,
                github_token=github_token,
                github_org=github_org,
                repo_type="tutorial"
            )
            
        except Exception as e:
            logger.info(f"Error committing tutorial completion: {str(e)}")
            return False
    

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
    
    def _get_subprocess_kwargs(self) -> Dict[str, Any]:
        """
        Get subprocess keyword arguments with platform-specific settings.
        On Windows, prevents terminal windows from flickering by setting CREATE_NO_WINDOW flag.
        
        Returns:
            Dictionary of keyword arguments for subprocess.run()
        """
        kwargs = {
            'capture_output': True,
            'text': True,
        }
        
        # On Windows, prevent terminal window from showing
        if platform.system() == "Windows":
            kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
            kwargs['shell'] = True  # Use shell=True for Windows compatibility
        
        return kwargs
    
    def open_vscode_with_repository(self, participant_id: str, development_mode: bool,
                                  study_stage: Optional[int] = None, repo_type: str = "study") -> bool:
        """
        Open VS Code with the participant's cloned repository.
        If study_stage is provided, ensures the correct branch is active before opening.
        
        Args:
            participant_id: The participant's unique identifier
            development_mode: Whether running in development mode
            study_stage: Study stage to ensure correct branch (optional, only for study repos)
            repo_type: Type of repository ("study" or "tutorial")
        
        Returns:
            True if successful, False otherwise
        """
        # Get the repository path
        repo_path = self.repository_manager.get_repository_path(participant_id, development_mode, repo_type)
        
        # Normalize path
        repo_path = os.path.normpath(repo_path)
        
        try:
            # Check if repository exists
            if not os.path.exists(repo_path):
                logger.info(f"Repository does not exist at: {repo_path}")
                return False
            
            # If study_stage is provided and it's a study repo, ensure the correct branch is active
            if study_stage is not None and repo_type == "study":
                if not self.repository_manager.ensure_stage_branch(repo_path, study_stage, skip_backup=True):
                    logger.warning(f"Failed to ensure correct branch for stage {study_stage}")
            
            # Try to open VS Code with the repository
            logger.info(f"Opening VS Code with repository: {repo_path}")
            
            # Use 'code' command to open VS Code with the repository folder
            kwargs = self._get_subprocess_kwargs()
            kwargs['timeout'] = 10
            result = subprocess.run([
                'code', repo_path
            ], **kwargs)
            
            if result.returncode == 0:
                logger.info(f"Successfully opened VS Code with repository: {repo_path}")
                return True
            else:
                logger.warning(f"Failed to open VS Code. Error: {result.stderr}")
                # Try alternative method for macOS
                try:
                    kwargs = self._get_subprocess_kwargs()
                    kwargs['timeout'] = 10
                    result = subprocess.run([
                        'open', '-a', 'Visual Studio Code', repo_path
                    ], **kwargs)
                    
                    if result.returncode == 0:
                        logger.info(f"Successfully opened VS Code using 'open' command: {repo_path}")
                        return True
                    else:
                        logger.warning(f"Failed to open VS Code with 'open' command. Error: {result.stderr}")
                        return False
                except Exception as e:
                    logger.info(f"Error trying 'open' command: {str(e)}")
                    return False
                
        except subprocess.TimeoutExpired:
            logger.info("VS Code open operation timed out")
            return False
        except FileNotFoundError:
            logger.info("VS Code ('code' command) not found in PATH. Please ensure VS Code is installed and the 'code' command is available.")
            return False
        except Exception as e:
            logger.info(f"Error opening VS Code: {str(e)}")
            return False

    def open_vscode_with_tutorial(self, participant_id: str, development_mode: bool) -> bool:
        """
        Open VS Code with the participant's tutorial repository.
        
        Args:
            participant_id: The participant's unique identifier
            development_mode: Whether running in development mode
        
        Returns:
            True if successful, False otherwise
        """
        # Use the unified method with tutorial repo type
        return self.open_vscode_with_repository(
            participant_id=participant_id,
            development_mode=development_mode,
            study_stage=None,
            repo_type="tutorial"
        )
