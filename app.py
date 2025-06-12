import os
import shutil
import subprocess
import requests
import json
import time
from datetime import datetime
from flask import Flask, render_template, request, session, redirect, url_for, jsonify
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

# Development mode configuration
DEVELOPMENT_MODE = os.getenv('DEVELOPMENT_MODE', 'false').lower() == 'true'
DEV_PARTICIPANT_ID = os.getenv('DEV_PARTICIPANT_ID', 'dev-participant-001')

# GitHub authentication configuration
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN', '')
GITHUB_ORG = os.getenv('GITHUB_ORG', 'LMU-Vibe-Coding-Study')

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

# Load task requirements at startup
TASK_REQUIREMENTS = load_task_requirements()

def get_tasks_for_stage(study_stage):
    """
    Get the appropriate tasks based on the study stage.
    Returns the list of tasks for the given stage.
    """
    if study_stage == 1:
        return TASK_REQUIREMENTS.get('stage1_tasks', [])
    elif study_stage == 2:
        return TASK_REQUIREMENTS.get('stage2_tasks', [])
    else:
        return TASK_REQUIREMENTS.get('stage1_tasks', [])  # Default to stage 1

def get_session_data(study_stage):
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

def update_session_data(study_stage, current_task=None, completed_tasks=None, timer_start=None, timer_finished=None):
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
    import hashlib
    hash_value = int(hashlib.md5(participant_id.encode()).hexdigest(), 16)
    return "vibe" if hash_value % 2 == 0 else "ai-assisted"

def get_study_stage(participant_id):
    """
    Determine if the participant is in stage 1 or stage 2 of the study.
    Stage 1: No repository exists in the expected location yet
    Stage 2: Repository already exists in the expected location
    Returns either 1 or 2.
    """
    if DEVELOPMENT_MODE:
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

def get_participant_id():
    """
    Get the participant_id from Azure VM tags using the Instance Metadata Service.
    In development mode, returns a mocked participant ID.
    Returns the participant_id if found, otherwise returns a default message.
    """
    if DEVELOPMENT_MODE:
        print(f"Development mode: Using mocked participant ID: {DEV_PARTICIPANT_ID}")
        return DEV_PARTICIPANT_ID
    
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

def get_authenticated_repo_url(repo_name):
    """
    Construct the authenticated GitHub repository URL.
    If GITHUB_TOKEN is provided, includes it in the URL for authentication.
    Returns the URL for cloning/accessing the repository.
    """
    if GITHUB_TOKEN:
        # Use token-based authentication with HTTPS
        return f"https://{GITHUB_TOKEN}@github.com/{GITHUB_ORG}/{repo_name}.git"
    else:
        # Use public HTTPS URL (for public repositories only)
        return f"https://github.com/{GITHUB_ORG}/{repo_name}.git"

def open_vscode_with_repository(participant_id):
    """
    Open VS Code with the participant's cloned repository.
    Returns True if successful, False otherwise.
    """
    # Get the repository path
    if DEVELOPMENT_MODE:
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

def check_and_clone_repository(participant_id):
    """
    Check if the GitHub repository for the participant exists in the workspace directory.
    If not, clone it to that location.
    In development mode, clones to the current project directory.
    """
    if DEVELOPMENT_MODE:
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
    repo_url = get_authenticated_repo_url(repo_name)
    
    # Normalize paths for Windows
    workspace_path = os.path.normpath(workspace_path)
    repo_path = os.path.normpath(repo_path)
    
    try:
        # Create workspace directory if it doesn't exist (only needed in production mode)
        if not DEVELOPMENT_MODE and not os.path.exists(workspace_path):
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

def get_repository_path(participant_id):
    """
    Get the path to the participant's repository.
    Returns the absolute path to the repository.
    """
    if DEVELOPMENT_MODE:
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

def commit_code_changes(participant_id, study_stage, commit_message):
    """
    Commit any changes in the participant's repository with a descriptive message.
    Returns True if successful, False otherwise.
    """
    repo_path = get_repository_path(participant_id)
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
        if GITHUB_TOKEN:
            # Set up the authenticated remote URL
            repo_name = f"study-{participant_id}"
            authenticated_url = get_authenticated_repo_url(repo_name)
            
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

def push_code_changes(participant_id):
    """
    Push committed changes to the remote repository.
    Returns True if successful, False otherwise.
    """
    repo_path = get_repository_path(participant_id)
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
        if GITHUB_TOKEN:
            repo_name = f"study-{participant_id}"
            authenticated_url = get_authenticated_repo_url(repo_name)
            
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

@app.route('/')
def home():
    participant_id = get_participant_id()
    study_stage = get_study_stage(participant_id)
    
    # Stage 2 participants should go directly to welcome back screen
    if study_stage == 2:
        return redirect(url_for('welcome_back'))
    
    return render_template('home.jinja', 
                         participant_id=participant_id,
                         study_stage=study_stage)

@app.route('/clear-session')
def clear_session():
    session.clear()
    return "Session cleared! <a href='/'>Go to home</a>"

@app.route('/background-questionnaire')
def background_questionnaire():
    participant_id = get_participant_id()
    study_stage = get_study_stage(participant_id)
    
    # Stage 2 participants should skip the background questionnaire
    if study_stage == 2:
        return redirect(url_for('welcome_back'))
    
    survey_url = os.getenv('SURVEY_URL', '#')
    
    if survey_url == '#':
        return render_template('survey_error.jinja', 
                             participant_id=participant_id,
                             study_stage=study_stage)
    
    return render_template('background_questionnaire.jinja', 
                         participant_id=participant_id,
                         study_stage=study_stage,
                         url=survey_url)

@app.route('/ux-questionnaire')
def ux_questionnaire():
    participant_id = get_participant_id()
    study_stage = get_study_stage(participant_id)
    ux_survey_url = os.getenv('UX_SURVEY_URL', '#')
    
    # Commit any remaining code changes before leaving for the survey
    commit_message = "Session ended - proceeding to UX questionnaire"
    commit_success = commit_code_changes(participant_id, study_stage, commit_message)
    
    if commit_success:
        print(f"Final code changes committed before UX survey for participant {participant_id}")
    else:
        print(f"No changes to commit or commit failed before UX survey for participant {participant_id}")
    
    if ux_survey_url == '#':
        return render_template('survey_error.jinja', 
                             participant_id=participant_id,
                             study_stage=study_stage)
    
    return render_template('ux_questionnaire.jinja', 
                         participant_id=participant_id,
                         study_stage=study_stage,
                         url=ux_survey_url)

@app.route('/tutorial')
def tutorial():
    participant_id = get_participant_id()
    study_stage = get_study_stage(participant_id)
    
    # Stage 2 participants should skip the tutorial
    if study_stage == 2:
        return redirect(url_for('welcome_back'))
    
    coding_condition = get_coding_condition(participant_id)
    return render_template('tutorial.jinja', 
                         participant_id=participant_id,
                         study_stage=study_stage,
                         coding_condition=coding_condition)

@app.route('/welcome-back')
def welcome_back():
    participant_id = get_participant_id()
    study_stage = get_study_stage(participant_id)
    coding_condition = get_coding_condition(participant_id)
    
    # Redirect to home if this is actually stage 1
    if study_stage == 1:
        return redirect(url_for('home'))
    
    return render_template('welcome_back.jinja', 
                         participant_id=participant_id,
                         study_stage=study_stage,
                         coding_condition=coding_condition)

@app.route('/task')
def task():
    participant_id = get_participant_id()
    study_stage = get_study_stage(participant_id)
    coding_condition = get_coding_condition(participant_id)
    
    # Get stage-specific session data
    session_data = get_session_data(study_stage)
    current_task = session_data['current_task']
    completed_tasks = session_data['completed_tasks']
    timer_start = session_data['timer_start']
    timer_finished = session_data['timer_finished']
    
    # Initialize timer if not started yet
    if timer_start is None:
        timer_start = time.time()
        update_session_data(study_stage, timer_start=timer_start)
        
        # Make an initial commit to mark the start of this coding session
        coding_condition = get_coding_condition(participant_id)
        commit_message = f"Started coding session - Condition: {coding_condition}"
        commit_success = commit_code_changes(participant_id, study_stage, commit_message)
        
        if commit_success:
            print(f"Initial commit made for session start - participant {participant_id}, stage {study_stage}")
        else:
            print(f"No initial commit needed or failed for participant {participant_id}, stage {study_stage}")
    
    # Calculate elapsed time and remaining time
    elapsed_time = time.time() - timer_start
    remaining_time = max(0, 200 - elapsed_time)  # 40 minutes = 2400 seconds
    
    # Get tasks appropriate for the current study stage
    task_requirements = get_tasks_for_stage(study_stage)
    
    # Check if this is the first time accessing the task page for this stage
    # If so, automatically open VS Code with the repository
    stage_key = f'stage{study_stage}'
    vscode_opened_key = f'vscode_opened_{stage_key}'
    
    if not session.get(vscode_opened_key, False):
        # Mark that we've attempted to open VS Code for this stage
        session[vscode_opened_key] = True
        
        # Try to open VS Code with the repository
        vscode_success = open_vscode_with_repository(participant_id)
        if vscode_success:
            print(f"VS Code opened successfully for participant {participant_id}, stage {study_stage}")
        else:
            print(f"Failed to open VS Code for participant {participant_id}, stage {study_stage}")
    
    # Debug logging
    print(f"Task route - Participant: {participant_id}, Stage: {study_stage}")
    print(f"Current task: {current_task}, Completed tasks: {completed_tasks}")
    print(f"Total tasks available: {len(task_requirements)}")
    print(f"Timer - Elapsed: {elapsed_time:.1f}s, Remaining: {remaining_time:.1f}s")
    
    return render_template('task.jinja', 
                         participant_id=participant_id,
                         study_stage=study_stage,
                         coding_condition=coding_condition,
                         current_task=current_task,
                         completed_tasks=completed_tasks,
                         task_requirements=task_requirements,
                         total_tasks=len(task_requirements),
                         timer_start=timer_start,
                         remaining_time=remaining_time,
                         timer_finished=timer_finished)

@app.route('/open-vscode')
def open_vscode():
    participant_id = get_participant_id()
    
    # Try to open VS Code with the repository
    vscode_success = open_vscode_with_repository(participant_id)
    
    if vscode_success:
        print(f"VS Code opened successfully for participant {participant_id} (manual request)")
    else:
        print(f"Failed to open VS Code for participant {participant_id} (manual request)")
    
    # Redirect back to the task page
    return redirect(url_for('task'))

@app.route('/complete-task', methods=['POST'])
def complete_task():
    participant_id = get_participant_id()
    study_stage = get_study_stage(participant_id)
    task_id = int(request.form.get('task_id', 1))
    
    # Get stage-specific session data
    session_data = get_session_data(study_stage)
    completed_tasks = session_data['completed_tasks']
    timer_finished = session_data['timer_finished']
    
    # Get tasks appropriate for the current study stage
    task_requirements = get_tasks_for_stage(study_stage)
    
    # Debug logging
    print(f"Complete task - Participant: {participant_id}, Stage: {study_stage}")
    print(f"Completing task {task_id}, Previously completed: {completed_tasks}")
    print(f"Timer finished: {timer_finished}")
    
    if task_id not in completed_tasks:
        completed_tasks.append(task_id)
        update_session_data(study_stage, completed_tasks=completed_tasks)
        print(f"Task {task_id} marked as completed for stage {study_stage}")
        
        # Commit code changes when task is completed
        task_title = "Unknown Task"
        if task_id <= len(task_requirements):
            task_title = task_requirements[task_id - 1].get('title', f'Task {task_id}')
        
        commit_message = f"Completed task {task_id}: {task_title}"
        commit_success = commit_code_changes(participant_id, study_stage, commit_message)
        
        if commit_success:
            print(f"Code changes committed for task {task_id}")
        else:
            print(f"Failed to commit code changes for task {task_id}")
    
    # Only move to next task if timer hasn't finished
    if not timer_finished and task_id < len(task_requirements):
        next_task = task_id + 1
        update_session_data(study_stage, current_task=next_task)
        print(f"Moving to next task: {next_task}")
    else:
        print(f"Timer finished or all tasks completed for stage {study_stage}")
    
    return redirect(url_for('task'))

@app.route('/timer-expired', methods=['POST'])
def timer_expired():
    """Handle when the 40-minute timer expires"""
    participant_id = get_participant_id()
    study_stage = get_study_stage(participant_id)
    
    # Mark timer as finished
    update_session_data(study_stage, timer_finished=True)
    
    # Commit any code changes when timer expires
    commit_message = "Timer expired - 40 minutes completed"
    commit_success = commit_code_changes(participant_id, study_stage, commit_message)
    
    if commit_success:
        print(f"Code changes committed when timer expired for participant {participant_id}")
    else:
        print(f"No changes to commit or commit failed when timer expired for participant {participant_id}")
    
    return jsonify({'status': 'success'})

@app.route('/get-timer-status')
def get_timer_status():
    """Get current timer status"""
    participant_id = get_participant_id()
    study_stage = get_study_stage(participant_id)
    
    session_data = get_session_data(study_stage)
    timer_start = session_data['timer_start']
    timer_finished = session_data['timer_finished']
    
    if timer_start is None:
        return jsonify({
            'timer_started': False,
            'remaining_time': 2400
        })
    
    elapsed_time = time.time() - timer_start
    remaining_time = max(0, 2400 - elapsed_time)
    
    return jsonify({
        'timer_started': True,
        'remaining_time': remaining_time,
        'timer_finished': timer_finished
    })

def test_github_connectivity(participant_id):
    """
    Test GitHub connectivity and authentication by checking if the repository exists.
    Returns True if the repository is accessible, False otherwise.
    """
    try:
        repo_name = f"study-{participant_id}"
        
        if GITHUB_TOKEN:
            # Test with authenticated request
            headers = {'Authorization': f'token {GITHUB_TOKEN}'}
            response = requests.get(
                f"https://api.github.com/repos/{GITHUB_ORG}/{repo_name}",
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
                f"https://api.github.com/repos/{GITHUB_ORG}/{repo_name}",
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

if __name__ == '__main__':
    # Print mode information
    if DEVELOPMENT_MODE:
        print("=" * 50)
        print("RUNNING IN DEVELOPMENT MODE")
        print(f"Participant ID: {DEV_PARTICIPANT_ID}")
        print("Repository will be cloned to current directory")
        print("=" * 50)
    else:
        print("Running in production mode")
    
    # Get participant ID and check/clone repository on startup
    participant_id = get_participant_id()
    study_stage = get_study_stage(participant_id)
    print(f"Starting server for participant: {participant_id}")
    print(f"Study stage: {study_stage} ({'Repository not found' if study_stage == 1 else 'Repository exists'})")
    
    # Test GitHub connectivity
    print("\nTesting GitHub connectivity...")
    if GITHUB_TOKEN:
        print(f"GitHub authentication enabled for organization: {GITHUB_ORG}")
    else:
        print("No GitHub token provided - using public access only")
    
    github_available = test_github_connectivity(participant_id)
    if not github_available:
        print("Warning: GitHub repository may not be accessible")
    
    # Check and clone repository if needed
    print("\nChecking repository...")
    check_and_clone_repository(participant_id)
    
    app.run(host='127.0.0.1', port=8085, debug=True)