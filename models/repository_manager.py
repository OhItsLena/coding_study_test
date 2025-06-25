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
        Handles remote synchronization to avoid conflicts.
        
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
            
            # First, fetch latest remote refs to ensure we have up-to-date information
            print(f"Fetching latest remote refs for {branch_name}")
            kwargs = self._get_subprocess_kwargs()
            kwargs['timeout'] = 15
            result = subprocess.run(['git', 'fetch', 'origin'], **kwargs)
            if result.returncode != 0:
                print(f"Warning: Failed to fetch from remote. Error: {result.stderr}")
                # Continue anyway - might be first time or network issue
            
            # Check if the branch already exists locally
            kwargs = self._get_subprocess_kwargs()
            kwargs['timeout'] = 10
            result = subprocess.run([
                'git', 'branch', '--list', branch_name
            ], **kwargs)
            branch_exists_locally = branch_name in result.stdout
            
            # Check if the branch exists on remote
            kwargs = self._get_subprocess_kwargs()
            kwargs['timeout'] = 10
            result = subprocess.run([
                'git', 'branch', '-r', '--list', f'origin/{branch_name}'
            ], **kwargs)
            branch_exists_remotely = f'origin/{branch_name}' in result.stdout
            
            if branch_exists_locally and branch_exists_remotely:
                # Both local and remote exist - checkout local and pull updates
                print(f"Branch {branch_name} exists both locally and remotely - syncing")
                kwargs = self._get_subprocess_kwargs()
                kwargs['timeout'] = 10
                result = subprocess.run(['git', 'checkout', branch_name], **kwargs)
                
                if result.returncode != 0:
                    print(f"Failed to checkout local branch {branch_name}. Error: {result.stderr}")
                    return False
                
                # For stage-1, ensure it's properly based on main/master before pulling
                if study_stage == 1:
                    if not self._ensure_stage1_based_on_main(branch_name):
                        print(f"Warning: Failed to ensure {branch_name} is based on main/master")
                
                # Pull updates from remote with merge strategy
                kwargs = self._get_subprocess_kwargs()
                kwargs['timeout'] = 20
                result = subprocess.run(['git', 'pull', 'origin', branch_name], **kwargs)
                
                if result.returncode != 0:
                    print(f"Warning: Failed to pull updates from remote {branch_name}. Error: {result.stderr}")
                    print("Continuing with local branch - manual merge may be required later")
                else:
                    print(f"Successfully synchronized {branch_name} with remote")
                    
            elif branch_exists_locally:
                # Only local branch exists - just switch to it
                print(f"Switching to existing local branch: {branch_name}")
                kwargs = self._get_subprocess_kwargs()
                kwargs['timeout'] = 10
                result = subprocess.run(['git', 'checkout', branch_name], **kwargs)
                
                if result.returncode != 0:
                    print(f"Failed to checkout local branch {branch_name}. Error: {result.stderr}")
                    return False
                
                # For stage-1, ensure it's properly based on main/master
                if study_stage == 1:
                    if not self._ensure_stage1_based_on_main(branch_name):
                        print(f"Warning: Failed to ensure {branch_name} is based on main/master")
                    
            elif branch_exists_remotely:
                # Only remote branch exists - create local tracking branch
                print(f"Creating local branch {branch_name} tracking remote origin/{branch_name}")
                kwargs = self._get_subprocess_kwargs()
                kwargs['timeout'] = 15
                result = subprocess.run([
                    'git', 'checkout', '-b', branch_name, f'origin/{branch_name}'
                ], **kwargs)
                
                if result.returncode != 0:
                    print(f"Failed to create tracking branch {branch_name}. Error: {result.stderr}")
                    return False
                
                # For stage-1, ensure it's properly based on main/master after checkout
                if study_stage == 1:
                    if not self._ensure_stage1_based_on_main(branch_name):
                        print(f"Warning: Failed to ensure {branch_name} is based on main/master")
                    
            else:
                # Neither local nor remote exist - create new branch from appropriate base
                print(f"Creating new branch: {branch_name}")
                
                kwargs = self._get_subprocess_kwargs()
                kwargs['timeout'] = 10
                
                if study_stage == 1:
                    # Stage-1 should be created from main/master
                    # First check if we have a remote
                    result = subprocess.run(['git', 'remote'], **kwargs)
                    has_remote = bool(result.stdout.strip())
                    
                    if has_remote:
                        # Check if main branch exists (newer repos use 'main')
                        result = subprocess.run(['git', 'branch', '-r', '--list', 'origin/main'], **kwargs)
                        base_branch = 'main' if 'origin/main' in result.stdout else 'master'
                        base_ref = f'origin/{base_branch}'
                        
                        # Fetch the latest main/master branch
                        result = subprocess.run(['git', 'fetch', 'origin', base_branch], **kwargs)
                        if result.returncode != 0:
                            print(f"Warning: Failed to fetch {base_branch} branch. Error: {result.stderr}")
                        
                        print(f"Creating {branch_name} from remote {base_branch} branch")
                    else:
                        # No remote, use local main/master branch
                        # Check if main branch exists locally
                        result = subprocess.run(['git', 'branch', '--list', 'main'], **kwargs)
                        if 'main' in result.stdout:
                            base_ref = 'main'
                            base_branch = 'main'
                        else:
                            # Check for master branch
                            result = subprocess.run(['git', 'branch', '--list', 'master'], **kwargs)
                            if 'master' in result.stdout:
                                base_ref = 'master'
                                base_branch = 'master'
                            else:
                                print("Error: Neither main nor master branch exists locally")
                                return False
                        
                        print(f"Creating {branch_name} from local {base_branch} branch")
                    
                elif study_stage == 2:
                    # Stage-2 should be created from stage-1
                    stage1_branch = 'stage-1'
                    
                    # Check if stage-1 exists locally or remotely
                    result = subprocess.run(['git', 'branch', '--list', stage1_branch], **kwargs)
                    stage1_exists_locally = stage1_branch in result.stdout
                    
                    result = subprocess.run(['git', 'branch', '-r', '--list', f'origin/{stage1_branch}'], **kwargs)
                    stage1_exists_remotely = f'origin/{stage1_branch}' in result.stdout
                    
                    if stage1_exists_remotely:
                        # Fetch latest stage-1 from remote
                        result = subprocess.run(['git', 'fetch', 'origin', stage1_branch], **kwargs)
                        if result.returncode != 0:
                            print(f"Warning: Failed to fetch {stage1_branch} branch. Error: {result.stderr}")
                        base_ref = f'origin/{stage1_branch}'
                    elif stage1_exists_locally:
                        base_ref = stage1_branch
                    else:
                        print(f"Error: {stage1_branch} branch does not exist. Cannot create {branch_name}")
                        return False
                    
                    print(f"Creating {branch_name} from {stage1_branch} branch")
                    
                else:
                    print(f"Error: Unsupported study stage: {study_stage}")
                    return False
                
                # Create new branch from the determined base
                kwargs = self._get_subprocess_kwargs()
                kwargs['timeout'] = 15
                result = subprocess.run(['git', 'checkout', '-b', branch_name, base_ref], **kwargs)
                
                if result.returncode != 0:
                    print(f"Failed to create branch {branch_name} from {base_ref}. Error: {result.stderr}")
                    return False
                
                print(f"Successfully created {branch_name} from {base_ref}")
            
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
    
    def _ensure_stage1_based_on_main(self, branch_name: str) -> bool:
        """
        Ensure that a stage-1 branch is properly based on main/master branch.
        This method checks if the stage-1 branch has the latest main/master changes
        and resets it if necessary to ensure it starts from the correct base.
        
        Args:
            branch_name: Name of the stage-1 branch
        
        Returns:
            True if successful, False otherwise
        """
        try:
            kwargs = self._get_subprocess_kwargs()
            kwargs['timeout'] = 10
            
            # Check if we have a remote
            result = subprocess.run(['git', 'remote'], **kwargs)
            has_remote = bool(result.stdout.strip())
            
            if has_remote:
                # Determine which base branch to use (main or master) from remote
                result = subprocess.run(['git', 'branch', '-r', '--list', 'origin/main'], **kwargs)
                base_branch = 'main' if 'origin/main' in result.stdout else 'master'
                base_ref = f'origin/{base_branch}'
                
                # Fetch the latest base branch
                result = subprocess.run(['git', 'fetch', 'origin', base_branch], **kwargs)
                if result.returncode != 0:
                    print(f"Warning: Failed to fetch {base_branch} branch. Error: {result.stderr}")
                    return False
            else:
                # No remote, use local main/master branch
                result = subprocess.run(['git', 'branch', '--list', 'main'], **kwargs)
                if 'main' in result.stdout:
                    base_branch = 'main'
                    base_ref = 'main'
                else:
                    result = subprocess.run(['git', 'branch', '--list', 'master'], **kwargs)
                    if 'master' in result.stdout:
                        base_branch = 'master'
                        base_ref = 'master'
                    else:
                        print("Error: Neither main nor master branch exists locally")
                        return False
            
            # Check if stage-1 branch has commits that main/master doesn't have
            # This helps us determine if stage-1 was created from a different branch (like tutorial)
            result = subprocess.run([
                'git', 'rev-list', '--count', f'{base_ref}..{branch_name}'
            ], **kwargs)
            
            if result.returncode != 0:
                print(f"Warning: Failed to check branch divergence. Error: {result.stderr}")
                return False
            
            commits_ahead = int(result.stdout.strip()) if result.stdout.strip().isdigit() else 0
            
            # Check if main/master has commits that stage-1 doesn't have
            result = subprocess.run([
                'git', 'rev-list', '--count', f'{branch_name}..{base_ref}'
            ], **kwargs)
            
            if result.returncode != 0:
                print(f"Warning: Failed to check branch behind count. Error: {result.stderr}")
                return False
            
            commits_behind = int(result.stdout.strip()) if result.stdout.strip().isdigit() else 0
            
            # If stage-1 is behind main/master, we should update it
            if commits_behind > 0:
                print(f"Stage-1 branch is {commits_behind} commits behind {base_branch}. Updating...")
                
                # If stage-1 has its own commits, we need to be careful about preserving work
                if commits_ahead > 0:
                    print(f"Stage-1 branch has {commits_ahead} commits ahead of {base_branch}. Attempting to rebase...")
                    
                    # Try to rebase stage-1 onto main/master
                    result = subprocess.run([
                        'git', 'rebase', base_ref
                    ], **kwargs)
                    
                    if result.returncode == 0:
                        print(f"Successfully rebased {branch_name} onto {base_branch}")
                        return True
                    else:
                        print(f"Rebase failed: {result.stderr}")
                        # Abort the rebase and try merge instead
                        subprocess.run(['git', 'rebase', '--abort'], **kwargs)
                        
                        print(f"Attempting to merge {base_branch} into {branch_name}...")
                        result = subprocess.run([
                            'git', 'merge', base_ref
                        ], **kwargs)
                        
                        if result.returncode == 0:
                            print(f"Successfully merged {base_branch} into {branch_name}")
                            return True
                        else:
                            print(f"Merge also failed: {result.stderr}")
                            return False
                else:
                    # No commits ahead, safe to reset to main/master
                    print(f"Resetting {branch_name} to match {base_branch}")
                    result = subprocess.run([
                        'git', 'reset', '--hard', base_ref
                    ], **kwargs)
                    
                    if result.returncode == 0:
                        print(f"Successfully reset {branch_name} to {base_branch}")
                        return True
                    else:
                        print(f"Failed to reset branch: {result.stderr}")
                        return False
            else:
                print(f"Stage-1 branch is up to date with {base_branch}")
                return True
                
        except Exception as e:
            print(f"Error ensuring stage-1 is based on main: {str(e)}")
            return False
    
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
        Handles remote synchronization to avoid conflicts.
        
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
            
            # Ensure we're on the correct stage branch (this now handles remote sync)
            if not self.ensure_stage_branch(repo_path, study_stage):
                print(f"Failed to ensure stage branch for stage {study_stage}")
                return False
            
            # Check if there are any changes to commit
            kwargs = self._get_subprocess_kwargs()
            kwargs['timeout'] = 10
            result = subprocess.run(['git', 'status', '--porcelain'], **kwargs)
            
            if result.returncode != 0:
                print(f"Failed to check git status. Error: {result.stderr}")
                return False
            
            has_changes = bool(result.stdout.strip())
            
            if not has_changes:
                print("No changes to commit")
                return True
            
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
                return self._push_with_retry(participant_id, study_stage, github_token, github_org)
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
    
    def _push_with_retry(self, participant_id: str, study_stage: int, 
                        github_token: str, github_org: str, max_retries: int = 3) -> bool:
        """
        Push changes with retry logic and conflict resolution.
        
        Args:
            participant_id: The participant's unique identifier
            study_stage: The study stage (1 or 2)
            github_token: GitHub personal access token
            github_org: GitHub organization name
            max_retries: Maximum number of retry attempts
        
        Returns:
            True if successful, False otherwise
        """
        branch_name = f"stage-{study_stage}"
        
        for attempt in range(max_retries):
            try:
                # Set up the authenticated remote URL
                repo_name = f"study-{participant_id}"
                authenticated_url = self.github_service.get_authenticated_repo_url(repo_name, github_token, github_org)
                
                # Update the origin URL to use authentication
                kwargs = self._get_subprocess_kwargs()
                kwargs['timeout'] = 10
                result = subprocess.run([
                    'git', 'remote', 'set-url', 'origin', authenticated_url
                ], **kwargs)
                
                if result.returncode != 0:
                    print(f"Warning: Failed to set authenticated remote URL. Error: {result.stderr}")
                
                # Attempt to push changes to the stage-specific branch
                kwargs = self._get_subprocess_kwargs()
                kwargs['timeout'] = 30
                result = subprocess.run([
                    'git', 'push', 'origin', branch_name
                ], **kwargs)
                
                if result.returncode == 0:
                    print(f"Successfully pushed changes to remote repository branch: {branch_name}")
                    return True
                else:
                    error_msg = result.stderr.lower()
                    if 'rejected' in error_msg or 'non-fast-forward' in error_msg:
                        print(f"Push rejected (attempt {attempt + 1}/{max_retries}). Trying to sync with remote...")
                        
                        # Try to pull and merge remote changes
                        if self._sync_with_remote_branch(branch_name):
                            print("Successfully synced with remote. Retrying push...")
                            continue
                        else:
                            print("Failed to sync with remote branch")
                            if attempt == max_retries - 1:
                                return False
                    else:
                        print(f"Push failed with error: {result.stderr}")
                        if attempt == max_retries - 1:
                            return False
                        
            except subprocess.TimeoutExpired:
                print(f"Push operation timed out (attempt {attempt + 1}/{max_retries})")
                if attempt == max_retries - 1:
                    return False
            except Exception as e:
                print(f"Error during push attempt {attempt + 1}: {str(e)}")
                if attempt == max_retries - 1:
                    return False
        
        return False
    
    def _sync_with_remote_branch(self, branch_name: str) -> bool:
        """
        Sync local branch with remote branch by pulling and merging changes.
        
        Args:
            branch_name: Name of the branch to sync
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Fetch latest changes
            kwargs = self._get_subprocess_kwargs()
            kwargs['timeout'] = 15
            result = subprocess.run(['git', 'fetch', 'origin'], **kwargs)
            
            if result.returncode != 0:
                print(f"Failed to fetch from remote: {result.stderr}")
                return False
            
            # Try to pull and merge
            kwargs = self._get_subprocess_kwargs()
            kwargs['timeout'] = 20
            result = subprocess.run(['git', 'pull', 'origin', branch_name], **kwargs)
            
            if result.returncode == 0:
                print(f"Successfully merged remote changes for {branch_name}")
                return True
            else:
                # If automatic merge fails, try to resolve with merge strategy
                print(f"Automatic merge failed, trying merge strategy: {result.stderr}")
                
                # Reset to try a different approach
                result = subprocess.run(['git', 'merge', '--abort'], **kwargs)
                
                # Try merge with strategy favoring our changes
                result = subprocess.run([
                    'git', 'pull', 'origin', branch_name, '--strategy=recursive', '--strategy-option=ours'
                ], **kwargs)
                
                if result.returncode == 0:
                    print(f"Successfully resolved merge conflicts for {branch_name}")
                    return True
                else:
                    print(f"Failed to resolve merge conflicts: {result.stderr}")
                    return False
                    
        except Exception as e:
            print(f"Error syncing with remote branch: {str(e)}")
            return False
    
    def push_code_changes(self, participant_id: str, study_stage: int, development_mode: bool,
                        github_token: Optional[str], github_org: str) -> bool:
        """
        Push committed changes to the remote repository on the correct stage branch.
        Uses enhanced retry logic and conflict resolution.
        
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
            
            # Ensure we're on the correct stage branch (this now handles remote sync)
            if not self.ensure_stage_branch(repo_path, study_stage):
                print(f"Failed to ensure stage branch for stage {study_stage}")
                return False
            
            # Use enhanced push with retry logic if we have a token
            if github_token:
                return self._push_with_retry(participant_id, study_stage, github_token, github_org)
            else:
                print("No GitHub token provided - cannot push to remote")
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

    def setup_tutorial_branch(self, participant_id: str, development_mode: bool,
                             github_token: str, github_org: str) -> bool:
        """
        Set up tutorial branch for participant.
        
        Args:
            participant_id: The participant ID
            development_mode: Whether in development mode
            github_token: GitHub authentication token
            github_org: GitHub organization name
            
        Returns:
            bool: Success status
        """
        try:
            repo_path = self.get_repository_path(participant_id, development_mode)
            
            # Ensure repository exists first
            if not os.path.exists(repo_path):
                success = self.check_and_clone_repository(
                    participant_id, development_mode, github_token, github_org
                )
                if not success:
                    print(f"Failed to clone repository for tutorial setup")
                    return False
            
            # Ensure git config is set up
            if not self.ensure_git_config(repo_path, participant_id):
                print(f"Failed to set up git config for tutorial")
                return False
                
            # Create and checkout tutorial branch
            kwargs = self._get_subprocess_kwargs()
            kwargs['cwd'] = repo_path
            
            # First, fetch all remote branches to ensure we have the latest refs
            result = subprocess.run(['git', 'fetch', 'origin'], **kwargs)
            if result.returncode != 0:
                print(f"Warning: Failed to fetch from origin: {result.stderr}")
            
            # Check if tutorial branch exists locally
            result = subprocess.run(['git', 'branch', '--list', 'tutorial'], **kwargs)
            local_tutorial_exists = bool(result.stdout.strip())
            
            # Check if tutorial branch exists remotely
            result = subprocess.run(['git', 'branch', '-r', '--list', 'origin/tutorial'], **kwargs)
            remote_tutorial_exists = bool(result.stdout.strip())
            
            if local_tutorial_exists:
                # Local tutorial branch exists, just switch to it
                result = subprocess.run(['git', 'checkout', 'tutorial'], **kwargs)
                if result.returncode != 0:
                    print(f"Failed to checkout existing tutorial branch: {result.stderr}")
                    return False
                print(f"Switched to existing local tutorial branch for {participant_id}")
                
                # If remote also exists, pull any updates
                if remote_tutorial_exists:
                    result = subprocess.run(['git', 'pull', 'origin', 'tutorial'], **kwargs)
                    if result.returncode != 0:
                        print(f"Warning: Failed to pull tutorial branch updates: {result.stderr}")
                    else:
                        print(f"Updated tutorial branch from remote for {participant_id}")
                        
            elif remote_tutorial_exists:
                # Remote tutorial branch exists but not local, checkout from remote
                result = subprocess.run(['git', 'checkout', '-b', 'tutorial', 'origin/tutorial'], **kwargs)
                if result.returncode != 0:
                    print(f"Failed to checkout tutorial branch from remote: {result.stderr}")
                    return False
                print(f"Checked out tutorial branch from remote for {participant_id}")
                
            else:
                # Neither local nor remote tutorial branch exists, create new one
                result = subprocess.run(['git', 'checkout', '-b', 'tutorial'], **kwargs)
                if result.returncode != 0:
                    print(f"Failed to create new tutorial branch: {result.stderr}")
                    return False
                print(f"Created new tutorial branch for {participant_id}")
            
            return True
            
        except Exception as e:
            print(f"Error setting up tutorial branch: {str(e)}")
            return False

    def push_tutorial_code(self, participant_id: str, development_mode: bool,
                          github_token: str, github_org: str) -> bool:
        """
        Push tutorial code to remote tutorial branch.
        Uses enhanced retry logic and conflict resolution.
        
        Args:
            participant_id: The participant ID
            development_mode: Whether in development mode
            github_token: GitHub authentication token
            github_org: GitHub organization name
            
        Returns:
            bool: Success status
        """
        try:
            repo_path = self.get_repository_path(participant_id, development_mode)
            
            if not os.path.exists(repo_path):
                print(f"Repository does not exist for tutorial push: {repo_path}")
                return False
            
            original_cwd = os.getcwd()
            os.chdir(repo_path)
            
            try:
                # Ensure we're on tutorial branch and sync with remote
                kwargs = self._get_subprocess_kwargs()
                kwargs['timeout'] = 15
                
                # Fetch latest refs
                result = subprocess.run(['git', 'fetch', 'origin'], **kwargs)
                if result.returncode != 0:
                    print(f"Warning: Failed to fetch from remote: {result.stderr}")
                
                # Ensure we're on tutorial branch
                result = subprocess.run(['git', 'branch', '--show-current'], **kwargs)
                if result.returncode != 0:
                    print(f"Failed to check current branch: {result.stderr}")
                    return False
                    
                current_branch = result.stdout.strip()
                if current_branch != 'tutorial':
                    # Switch to tutorial branch
                    result = subprocess.run(['git', 'checkout', 'tutorial'], **kwargs)
                    if result.returncode != 0:
                        print(f"Failed to switch to tutorial branch: {result.stderr}")
                        return False
                
                # Sync with remote tutorial branch if it exists
                result = subprocess.run(['git', 'branch', '-r', '--list', 'origin/tutorial'], **kwargs)
                if result.stdout.strip():
                    # Remote tutorial branch exists, pull updates
                    result = subprocess.run(['git', 'pull', 'origin', 'tutorial'], **kwargs)
                    if result.returncode != 0:
                        print(f"Warning: Failed to pull tutorial updates: {result.stderr}")
                
                # Check if there are any changes to commit
                result = subprocess.run(['git', 'status', '--porcelain'], **kwargs)
                if result.returncode != 0:
                    print(f"Failed to check git status: {result.stderr}")
                    return False
                    
                has_changes = bool(result.stdout.strip())
                
                if has_changes:
                    # Add all changes
                    result = subprocess.run(['git', 'add', '.'], **kwargs)
                    if result.returncode != 0:
                        print(f"Failed to add tutorial changes: {result.stderr}")
                        return False
                    
                    # Commit changes
                    commit_message = f"Tutorial completion - {participant_id}"
                    result = subprocess.run(['git', 'commit', '-m', commit_message], **kwargs)
                    if result.returncode != 0:
                        print(f"Failed to commit tutorial changes: {result.stderr}")
                        return False
                    
                    print(f"Committed tutorial changes for {participant_id}")
                
                # Use enhanced push with retry logic
                return self._push_tutorial_with_retry(participant_id, github_token, github_org)
                
            finally:
                os.chdir(original_cwd)
            
        except Exception as e:
            print(f"Error pushing tutorial code: {str(e)}")
            return False
    
    def _push_tutorial_with_retry(self, participant_id: str, github_token: str, 
                                 github_org: str, max_retries: int = 3) -> bool:
        """
        Push tutorial code with retry logic and conflict resolution.
        
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
                kwargs['timeout'] = 10
                result = subprocess.run([
                    'git', 'remote', 'set-url', 'origin', authenticated_url
                ], **kwargs)
                
                if result.returncode != 0:
                    print(f"Warning: Failed to set authenticated remote URL: {result.stderr}")
                
                # Attempt to push tutorial branch
                kwargs = self._get_subprocess_kwargs()
                kwargs['timeout'] = 30
                result = subprocess.run(['git', 'push', 'origin', 'tutorial'], **kwargs)
                
                if result.returncode == 0:
                    print(f"Successfully pushed tutorial code for {participant_id}")
                    return True
                else:
                    error_msg = result.stderr.lower()
                    if 'rejected' in error_msg or 'non-fast-forward' in error_msg:
                        print(f"Tutorial push rejected (attempt {attempt + 1}/{max_retries}). Trying to sync with remote...")
                        
                        # Try to sync with remote tutorial branch
                        if self._sync_with_remote_branch('tutorial'):
                            print("Successfully synced tutorial with remote. Retrying push...")
                            continue
                        else:
                            print("Failed to sync tutorial with remote branch")
                            if attempt == max_retries - 1:
                                return False
                    else:
                        print(f"Tutorial push failed with error: {result.stderr}")
                        if attempt == max_retries - 1:
                            return False
                        
            except subprocess.TimeoutExpired:
                print(f"Tutorial push operation timed out (attempt {attempt + 1}/{max_retries})")
                if attempt == max_retries - 1:
                    return False
            except Exception as e:
                print(f"Error during tutorial push attempt {attempt + 1}: {str(e)}")
                if attempt == max_retries - 1:
                    return False
        
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

    def open_vscode_with_tutorial(self, participant_id: str, development_mode: bool) -> bool:
        """
        Open VS Code with the participant's repository on the tutorial branch.
        
        Args:
            participant_id: The participant's unique identifier
            development_mode: Whether running in development mode
        
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
            
            # Ensure we're on tutorial branch
            kwargs = self.repository_manager._get_subprocess_kwargs()
            kwargs['cwd'] = repo_path
            
            result = subprocess.run(['git', 'checkout', 'tutorial'], **kwargs)
            if result.returncode != 0:
                print(f"Failed to checkout tutorial branch: {result.stderr}")
                return False
            
            # Try to open VS Code with the repository
            print(f"Opening VS Code with tutorial branch: {repo_path}")
            
            # Use 'code' command to open VS Code with the repository folder
            kwargs = self._get_subprocess_kwargs()
            kwargs['timeout'] = 10
            result = subprocess.run([
                'code', repo_path
            ], **kwargs)
            
            if result.returncode == 0:
                print(f"Successfully opened VS Code with tutorial: {repo_path}")
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
                        print(f"Successfully opened VS Code with tutorial using 'open' command: {repo_path}")
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
            print(f"Error opening VS Code with tutorial: {str(e)}")
            return False
