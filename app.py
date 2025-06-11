import os
import shutil
import subprocess
import requests
import json
from flask import Flask, render_template, request, session, redirect, url_for
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

# Development mode configuration
DEVELOPMENT_MODE = os.getenv('DEVELOPMENT_MODE', 'false').lower() == 'true'
DEV_PARTICIPANT_ID = os.getenv('DEV_PARTICIPANT_ID', 'dev-participant-001')

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
        'stage_key': stage_key
    }

def update_session_data(study_stage, current_task=None, completed_tasks=None):
    """
    Update session data specific to the current study stage.
    """
    stage_key = f'stage{study_stage}'
    
    if current_task is not None:
        session[f'current_task_{stage_key}'] = current_task
    
    if completed_tasks is not None:
        session[f'completed_tasks_{stage_key}'] = completed_tasks

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
    
    repo_url = f"https://github.com/LMU-Vibe-Coding-Study/{repo_name}"
    
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
    
    # Get tasks appropriate for the current study stage
    task_requirements = get_tasks_for_stage(study_stage)
    
    # Debug logging
    print(f"Task route - Participant: {participant_id}, Stage: {study_stage}")
    print(f"Current task: {current_task}, Completed tasks: {completed_tasks}")
    print(f"Total tasks available: {len(task_requirements)}")
    
    return render_template('task.jinja', 
                         participant_id=participant_id,
                         study_stage=study_stage,
                         coding_condition=coding_condition,
                         current_task=current_task,
                         completed_tasks=completed_tasks,
                         task_requirements=task_requirements,
                         total_tasks=len(task_requirements))

@app.route('/complete-task', methods=['POST'])
def complete_task():
    participant_id = get_participant_id()
    study_stage = get_study_stage(participant_id)
    task_id = int(request.form.get('task_id', 1))
    
    # Get stage-specific session data
    session_data = get_session_data(study_stage)
    completed_tasks = session_data['completed_tasks']
    
    # Get tasks appropriate for the current study stage
    task_requirements = get_tasks_for_stage(study_stage)
    
    # Debug logging
    print(f"Complete task - Participant: {participant_id}, Stage: {study_stage}")
    print(f"Completing task {task_id}, Previously completed: {completed_tasks}")
    
    if task_id not in completed_tasks:
        completed_tasks.append(task_id)
        update_session_data(study_stage, completed_tasks=completed_tasks)
        print(f"Task {task_id} marked as completed for stage {study_stage}")
    
    # Move to next task if available
    if task_id < len(task_requirements):
        next_task = task_id + 1
        update_session_data(study_stage, current_task=next_task)
        print(f"Moving to next task: {next_task}")
    else:
        print(f"All tasks completed for stage {study_stage}")
    
    return redirect(url_for('task'))

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
    
    # Check and clone repository if needed
    check_and_clone_repository(participant_id)
    
    app.run(host='127.0.0.1', port=8085, debug=True)