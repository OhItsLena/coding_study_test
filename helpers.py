"""
Helper functions for the coding study Flask application.
This module contains all utility functions for participant management,
repository operations, GitHub connectivity, and session management.
"""

import os
import shutil
import subprocess
import requests
import json
import hashlib
from datetime import datetime


def load_task_requirements():
    """
    Load task requirements from the JSON file.
    Returns a dictionary with stage1_tasks and stage2_tasks.
    """
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        json_path = os.path.join(current_dir, 'task_requirements.json')
        
        with open(json_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
            return data
    except Exception as e:
        print(f"Error loading task requirements: {str(e)}")
        return {"stage1_tasks": [], "stage2_tasks": []}


def get_tasks_for_stage(study_stage, task_requirements):
    """
    Get the appropriate tasks based on the study stage.
    Returns the list of tasks for the given stage.
    """
    if study_stage == 1:
        return task_requirements.get('stage1_tasks', [])
    elif study_stage == 2:
        return task_requirements.get('stage2_tasks', [])
    else:
        return task_requirements.get('stage1_tasks', [])  # Default to stage 1


def get_session_data(session, study_stage):
    """
    Get session data specific to the current study stage.
    Returns a dictionary with current_task and completed_tasks for the stage.
    """
    stage_key = f'stage{study_stage}'
    return {
        'current_task': session.get(f'current_task_{stage_key}', 1),
        'completed_tasks': session.get(f'completed_tasks_{stage_key}', []),
        'stage_key': stage_key,
        'timer_start': session.get(f'timer_start_{stage_key}'),
        'timer_finished': session.get(f'timer_finished_{stage_key}', False)
    }


def update_session_data(session, study_stage, current_task=None, completed_tasks=None, timer_start=None, timer_finished=None):
    """
    Update session data specific to the current study stage.
    """
    stage_key = f'stage{study_stage}'
    
    if current_task is not None:
        session[f'current_task_{stage_key}'] = current_task
    
    if completed_tasks is not None:
        session[f'completed_tasks_{stage_key}'] = completed_tasks
    
    if timer_start is not None:
        session[f'timer_start_{stage_key}'] = timer_start
    
    if timer_finished is not None:
        session[f'timer_finished_{stage_key}'] = timer_finished


def get_coding_condition(participant_id):
    """
    Determine the coding condition based on participant ID.
    Returns either 'vibe' for vibe coding or 'ai-assisted' for AI-assisted coding.
    """
    # Simple hash-based assignment for consistent condition per participant
    # This ensures the same participant always gets the same condition
    if participant_id == "Study Participant":
        return "vibe"  # Default for unknown participants
    
    # Use hash of participant ID to assign condition
    hash_value = int(hashlib.md5(participant_id.encode()).hexdigest(), 16)
    return "vibe" if hash_value % 2 == 0 else "ai-assisted"


def get_study_stage(participant_id, development_mode, dev_stage=1):
    """
    Determine if the participant is in stage 1 or stage 2 of the study.
    
    Gets the study_stage from Azure VM tags using the Instance Metadata Service.
    In development mode, returns the dev_stage parameter.
    Returns 1 if the tag cannot be found.
    
    Returns either 1 or 2.
    """
    if development_mode:
        print(f"Development mode: Using mocked study stage: {dev_stage}")
        return dev_stage
    
    try:
        # Azure Instance Metadata Service endpoint for tags
        metadata_url = "http://169.254.169.254/metadata/instance/compute/tags?api-version=2021-02-01&format=text"
        headers = {'Metadata': 'true'}
        
        # Set a short timeout since this is a local metadata service
        response = requests.get(metadata_url, headers=headers, timeout=5)
        
        if response.status_code == 200:
            tags_text = response.text
            # Tags are returned as semicolon-separated key:value pairs
            for tag in tags_text.split(';'):
                if ':' in tag:
                    key, value = tag.split(':', 1)
                    if key.strip().lower() == 'study_stage':
                        try:
                            stage = int(value.strip())
                            if stage in [1, 2]:
                                return stage
                        except ValueError:
                            print(f"Invalid study_stage tag value: {value.strip()}")
        
        # Default to stage 1 if tag not found or invalid
        return 1
    except Exception as e:
        print(f"Error getting study stage from Azure VM tags: {str(e)}")
        # Default to stage 1 if we can't reach the metadata service or any other error occurs
        return 1


def get_participant_id(development_mode, dev_participant_id):
    """
    Get the participant_id from Azure VM tags using the Instance Metadata Service.
    In development mode, returns a mocked participant ID.
    Returns the participant_id if found, otherwise returns a default message.
    """
    if development_mode:
        print(f"Development mode: Using mocked participant ID: {dev_participant_id}")
        return dev_participant_id
    
    try:
        # Azure Instance Metadata Service endpoint for tags
        metadata_url = "http://169.254.169.254/metadata/instance/compute/tags?api-version=2021-02-01&format=text"
        headers = {'Metadata': 'true'}
        
        # Set a short timeout since this is a local metadata service
        response = requests.get(metadata_url, headers=headers, timeout=5)
        
        if response.status_code == 200:
            tags_text = response.text
            # Tags are returned as semicolon-separated key:value pairs
            for tag in tags_text.split(';'):
                if ':' in tag:
                    key, value = tag.split(':', 1)
                    if key.strip().lower() == 'participant_id':
                        return value.strip()
        
        return "Study Participant"
    except Exception:
        # If we can't reach the metadata service or any other error occurs
        return "Study Participant"


def get_authenticated_repo_url(repo_name, github_token, github_org):
    """
    Construct the authenticated GitHub repository URL.
    If GITHUB_TOKEN is provided, includes it in the URL for authentication.
    Returns the URL for cloning/accessing the repository.
    """
    if github_token:
        # Use token-based authentication with HTTPS
        return f"https://{github_token}@github.com/{github_org}/{repo_name}.git"
    else:
        # Use public HTTPS URL (for public repositories only)
        return f"https://github.com/{github_org}/{repo_name}.git"


def open_vscode_with_repository(participant_id, development_mode, study_stage=None):
    """
    Open VS Code with the participant's cloned repository.
    If study_stage is provided, ensures the correct branch is active before opening.
    Returns True if successful, False otherwise.
    """
    # Get the repository path
    if development_mode:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        workspace_path = current_dir
        repo_name = f"study-{participant_id}"
        repo_path = os.path.join(workspace_path, repo_name)
    else:
        home_dir = os.path.expanduser("~")
        workspace_path = os.path.join(home_dir, "workspace")
        repo_name = f"study-{participant_id}"
        repo_path = os.path.join(workspace_path, repo_name)
    
    # Normalize path
    repo_path = os.path.normpath(repo_path)
    
    try:
        # Check if repository exists
        if not os.path.exists(repo_path):
            print(f"Repository does not exist at: {repo_path}")
            return False
        
        # If study_stage is provided, ensure the correct branch is active
        if study_stage is not None:
            if not ensure_stage_branch(repo_path, study_stage):
                print(f"Warning: Failed to ensure correct branch for stage {study_stage}")
        
        # Try to open VS Code with the repository
        print(f"Opening VS Code with repository: {repo_path}")
        
        # Use 'code' command to open VS Code with the repository folder
        result = subprocess.run([
            'code', repo_path
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print(f"Successfully opened VS Code with repository: {repo_path}")
            return True
        else:
            print(f"Failed to open VS Code. Error: {result.stderr}")
            # Try alternative method for macOS
            try:
                result = subprocess.run([
                    'open', '-a', 'Visual Studio Code', repo_path
                ], capture_output=True, text=True, timeout=10)
                
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


def check_and_clone_repository(participant_id, development_mode, github_token, github_org):
    """
    Check if the GitHub repository for the participant exists in the workspace directory.
    If not, clone it to that location.
    In development mode, clones to the current project directory.
    """
    if development_mode:
        # In development mode, use current directory
        current_dir = os.path.dirname(os.path.abspath(__file__))
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
    repo_url = get_authenticated_repo_url(repo_name, github_token, github_org)
    
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
        result = subprocess.run([
            'git', 'clone', repo_url, repo_path
        ], capture_output=True, text=True, timeout=60)
        
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


def setup_repository_for_stage(participant_id, study_stage, development_mode, github_token, github_org):
    """
    Set up the repository for a specific study stage by ensuring the correct branch is active.
    This should be called when a participant starts working on a specific stage.
    Returns True if successful, False otherwise.
    """
    repo_path = get_repository_path(participant_id, development_mode)
    
    if not os.path.exists(repo_path):
        print(f"Repository does not exist at: {repo_path}")
        return False
    
    # Ensure git config is set up
    ensure_git_config(repo_path, participant_id)
    
    # Ensure the correct stage branch is active
    if not ensure_stage_branch(repo_path, study_stage):
        print(f"Failed to set up branch for stage {study_stage}")
        return False
    
    print(f"Repository successfully set up for stage {study_stage}")
    return True


def get_repository_path(participant_id, development_mode):
    """
    Get the path to the participant's repository.
    Returns the absolute path to the repository.
    """
    if development_mode:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        workspace_path = current_dir
        repo_name = f"study-{participant_id}"
        repo_path = os.path.join(workspace_path, repo_name)
    else:
        home_dir = os.path.expanduser("~")
        workspace_path = os.path.join(home_dir, "workspace")
        repo_name = f"study-{participant_id}"
        repo_path = os.path.join(workspace_path, repo_name)
    
    return os.path.normpath(repo_path)


def ensure_git_config(repo_path, participant_id):
    """
    Ensure git config is set up for commits in the repository.
    """
    try:
        original_cwd = os.getcwd()
        os.chdir(repo_path)
        
        # Check if user.name is set
        result = subprocess.run([
            'git', 'config', 'user.name'
        ], capture_output=True, text=True, timeout=5)
        
        if result.returncode != 0 or not result.stdout.strip():
            # Set user name
            subprocess.run([
                'git', 'config', 'user.name', f'{participant_id}'
            ], capture_output=True, text=True, timeout=5)
            print(f"Set git user.name for participant {participant_id}")
        
        # Check if user.email is set
        result = subprocess.run([
            'git', 'config', 'user.email'
        ], capture_output=True, text=True, timeout=5)
        
        if result.returncode != 0 or not result.stdout.strip():
            # Set user email
            subprocess.run([
                'git', 'config', 'user.email', f'{participant_id}@study.local'
            ], capture_output=True, text=True, timeout=5)
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


def ensure_stage_branch(repo_path, study_stage):
    """
    Ensure the correct branch exists and is checked out for the given study stage.
    Creates stage-1 or stage-2 branch and switches to it.
    Returns True if successful, False otherwise.
    """
    try:
        original_cwd = os.getcwd()
        os.chdir(repo_path)
        
        branch_name = f"stage-{study_stage}"
        
        # Check if the branch already exists locally
        result = subprocess.run([
            'git', 'branch', '--list', branch_name
        ], capture_output=True, text=True, timeout=10)
        
        branch_exists_locally = branch_name in result.stdout
        
        if branch_exists_locally:
            # Branch exists locally - just switch to it
            print(f"Switching to existing local branch: {branch_name}")
            result = subprocess.run([
                'git', 'checkout', branch_name
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode != 0:
                print(f"Failed to checkout local branch {branch_name}. Error: {result.stderr}")
                return False
        else:
            # Branch doesn't exist - create it
            print(f"Creating new branch: {branch_name}")
            result = subprocess.run([
                'git', 'checkout', '-b', branch_name
            ], capture_output=True, text=True, timeout=10)
            
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


def commit_code_changes(participant_id, study_stage, commit_message, development_mode, github_token, github_org):
    """
    Commit any changes in the participant's repository with a descriptive message.
    Ensures the correct stage branch is being used and pushes to that branch.
    Returns True if successful, False otherwise.
    """
    repo_path = get_repository_path(participant_id, development_mode)
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
        ensure_git_config(repo_path, participant_id)
        
        # Change to repository directory
        os.chdir(repo_path)
        
        # Ensure we're on the correct stage branch
        if not ensure_stage_branch(repo_path, study_stage):
            print(f"Failed to ensure stage branch for stage {study_stage}")
            return False
        
        # Add all changes
        result = subprocess.run([
            'git', 'add', '.'
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode != 0:
            print(f"Failed to add changes. Error: {result.stderr}")
            return False
        
        # Create timestamp for commit
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        full_commit_message = f"[Stage {study_stage}] {commit_message} - {timestamp}"
        
        # Commit changes
        result = subprocess.run([
            'git', 'commit', '-m', full_commit_message
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode != 0:
            print(f"Failed to commit changes. Error: {result.stderr}")
            return False
        
        print(f"Successfully committed changes: {full_commit_message}")
        
        # Push changes to remote repository if we have authentication
        if github_token:
            # Set up the authenticated remote URL
            repo_name = f"study-{participant_id}"
            authenticated_url = get_authenticated_repo_url(repo_name, github_token, github_org)
            
            # Update the origin URL to use authentication
            result = subprocess.run([
                'git', 'remote', 'set-url', 'origin', authenticated_url
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode != 0:
                print(f"Warning: Failed to set authenticated remote URL. Error: {result.stderr}")
            
            # Push changes to the stage-specific branch
            branch_name = f"stage-{study_stage}"
            result = subprocess.run([
                'git', 'push', 'origin', branch_name
            ], capture_output=True, text=True, timeout=30)
            
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


def push_code_changes(participant_id, study_stage, development_mode, github_token, github_org):
    """
    Push committed changes to the remote repository on the correct stage branch.
    Returns True if successful, False otherwise.
    """
    repo_path = get_repository_path(participant_id, development_mode)
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
        if not ensure_stage_branch(repo_path, study_stage):
            print(f"Failed to ensure stage branch for stage {study_stage}")
            return False
        
        # Set up the authenticated remote URL if we have a token
        if github_token:
            repo_name = f"study-{participant_id}"
            authenticated_url = get_authenticated_repo_url(repo_name, github_token, github_org)
            
            # Update the origin URL to use authentication
            result = subprocess.run([
                'git', 'remote', 'set-url', 'origin', authenticated_url
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode != 0:
                print(f"Warning: Failed to set authenticated remote URL. Error: {result.stderr}")
        
        # Push changes to the stage-specific branch
        branch_name = f"stage-{study_stage}"
        result = subprocess.run([
            'git', 'push', 'origin', branch_name
        ], capture_output=True, text=True, timeout=30)
        
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


def test_github_connectivity(participant_id, github_token, github_org):
    """
    Test GitHub connectivity and authentication by checking if the repository exists.
    Returns True if the repository is accessible, False otherwise.
    """
    try:
        repo_name = f"study-{participant_id}"
        
        if github_token:
            # Test with authenticated request
            headers = {'Authorization': f'token {github_token}'}
            response = requests.get(
                f"https://api.github.com/repos/{github_org}/{repo_name}",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                print(f"✓ GitHub repository {repo_name} is accessible with authentication")
                return True
            elif response.status_code == 404:
                print(f"✗ Repository {repo_name} not found or not accessible")
                return False
            elif response.status_code == 401:
                print(f"✗ GitHub authentication failed - check your token")
                return False
            else:
                print(f"✗ GitHub API returned status code: {response.status_code}")
                return False
        else:
            # Test public access without authentication
            response = requests.get(
                f"https://api.github.com/repos/{github_org}/{repo_name}",
                timeout=10
            )
            
            if response.status_code == 200:
                print(f"✓ Public repository {repo_name} is accessible")
                return True
            else:
                print(f"✗ Repository {repo_name} not publicly accessible (status: {response.status_code})")
                return False
                
    except requests.exceptions.RequestException as e:
        print(f"✗ Failed to connect to GitHub API: {str(e)}")
        return False
    except Exception as e:
        print(f"✗ Error testing GitHub connectivity: {str(e)}")
        return False


def get_logs_directory_path(participant_id, development_mode):
    """
    Get the path to the logs directory (separate from the main coding repository).
    Returns the absolute path to the logs directory.
    """
    if development_mode:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        workspace_path = current_dir
        logs_dir_name = f"logs-{participant_id}"
        logs_path = os.path.join(workspace_path, logs_dir_name)
    else:
        home_dir = os.path.expanduser("~")
        workspace_path = os.path.join(home_dir, "workspace")
        logs_dir_name = f"logs-{participant_id}"
        logs_path = os.path.join(workspace_path, logs_dir_name)
    
    return os.path.normpath(logs_path)


def ensure_logging_repository(participant_id, development_mode, github_token, github_org):
    """
    Ensure the logging repository exists and is set up with a logging branch.
    Creates a separate repository/directory for logs to keep them hidden from participants.
    Returns True if successful, False otherwise.
    """
    logs_path = get_logs_directory_path(participant_id, development_mode)
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
            
            # Set up git config
            ensure_git_config(logs_path, participant_id)
            
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


def log_route_visit(participant_id, route_name, development_mode, study_stage, session_data=None, github_token=None, github_org=None):
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
        if not ensure_logging_repository(participant_id, development_mode, github_token, github_org):
            print(f"Failed to ensure logging repository for participant {participant_id}")
            return False
        
        logs_path = get_logs_directory_path(participant_id, development_mode)
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
        route_key = f"{route_name}_stage{study_stage}"
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
                push_logs_to_remote(participant_id, development_mode, github_token, github_org)
            
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


def push_logs_to_remote(participant_id, development_mode, github_token, github_org):
    """
    Push logs to remote repository on the logging branch.
    This could be the same repository as the main study repo or a separate logs repo.
    Returns True if successful, False otherwise.
    """
    logs_path = get_logs_directory_path(participant_id, development_mode)
    original_cwd = os.getcwd()
    
    try:
        os.chdir(logs_path)
        
        # For now, we'll use the same repository structure but on logging branch
        # In production, you might want to set up a separate logs repository
        repo_name = f"study-{participant_id}"
        authenticated_url = get_authenticated_repo_url(repo_name, github_token, github_org)
        
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


def should_log_route(session, route_name, study_stage):
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


def mark_route_as_logged(session, route_name, study_stage):
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


def mark_stage_transition(participant_id, from_stage, to_stage, development_mode, github_token=None, github_org=None):
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
        if not ensure_logging_repository(participant_id, development_mode, github_token, github_org):
            print(f"Failed to ensure logging repository for participant {participant_id}")
            return False
        
        logs_path = get_logs_directory_path(participant_id, development_mode)
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
                push_logs_to_remote(participant_id, development_mode, github_token, github_org)
            
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


def get_stage_transition_history(participant_id, development_mode):
    """
    Get the stage transition history for a participant.
    
    Returns:
        List of transition entries, or empty list if none found
    """
    try:
        logs_path = get_logs_directory_path(participant_id, development_mode)
        log_file_path = os.path.join(logs_path, 'stage_transitions.json')
        
        if not os.path.exists(log_file_path):
            return []
        
        with open(log_file_path, 'r', encoding='utf-8') as f:
            transitions_data = json.load(f)
        
        return transitions_data.get('transitions', [])
        
    except Exception as e:
        print(f"Error reading stage transition history: {str(e)}")
        return []
