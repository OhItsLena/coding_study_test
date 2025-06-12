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


def get_study_stage(participant_id, development_mode):
    """
    Determine if the participant is in stage 1 or stage 2 of the study.
    Stage 1: No repository exists in the expected location yet
    Stage 2: Repository already exists in the expected location
    Returns either 1 or 2.
    """
    if development_mode:
        # In development mode, use current directory
        current_dir = os.path.dirname(os.path.abspath(__file__))
        workspace_path = current_dir
        repo_name = f"study-{participant_id}"
        repo_path = os.path.join(workspace_path, repo_name)
    else:
        # Use user's home directory with a workspace folder
        home_dir = os.path.expanduser("~")
        workspace_path = os.path.join(home_dir, "workspace")
        repo_name = f"study-{participant_id}"
        repo_path = os.path.join(workspace_path, repo_name)
    
    # Normalize paths for Windows
    repo_path = os.path.normpath(repo_path)
    
    # Check if repository already exists and is a valid git repository
    if os.path.exists(repo_path) and os.path.isdir(repo_path):
        git_dir = os.path.join(repo_path, '.git')
        if os.path.exists(git_dir):
            return 2  # Stage 2: Repository exists
    
    return 1  # Stage 1: No repository found


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


def open_vscode_with_repository(participant_id, development_mode):
    """
    Open VS Code with the participant's cloned repository.
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


def commit_code_changes(participant_id, study_stage, commit_message, development_mode, github_token, github_org):
    """
    Commit any changes in the participant's repository with a descriptive message.
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
        
        # Check if there are any changes to commit
        result = subprocess.run([
            'git', 'status', '--porcelain'
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode != 0:
            print(f"Failed to check git status. Error: {result.stderr}")
            return False
        
        # If no changes, nothing to commit
        if not result.stdout.strip():
            print(f"No changes to commit in repository: {repo_path}")
            return True
        
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
            
            # Push changes to remote repository
            result = subprocess.run([
                'git', 'push', 'origin', 'main'
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                print(f"Successfully pushed changes to remote repository")
            else:
                # Try pushing to 'master' branch if 'main' doesn't exist
                result = subprocess.run([
                    'git', 'push', 'origin', 'master'
                ], capture_output=True, text=True, timeout=30)
                
                if result.returncode == 0:
                    print(f"Successfully pushed changes to remote repository (master branch)")
                else:
                    print(f"Warning: Failed to push changes to remote repository. Error: {result.stderr}")
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


def push_code_changes(participant_id, development_mode, github_token, github_org):
    """
    Push committed changes to the remote repository.
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
        
        # Push changes to remote repository
        result = subprocess.run([
            'git', 'push', 'origin', 'main'
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            print(f"Successfully pushed changes to remote repository for participant {participant_id}")
            return True
        else:
            # Try pushing to 'master' branch if 'main' doesn't exist
            result = subprocess.run([
                'git', 'push', 'origin', 'master'
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                print(f"Successfully pushed changes to remote repository (master branch) for participant {participant_id}")
                return True
            else:
                print(f"Failed to push changes to remote repository. Error: {result.stderr}")
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
