import os
import shutil
import subprocess
import requests
from flask import Flask, render_template_string
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

def get_participant_id():
    """
    Get the participant_id from Azure VM tags using the Instance Metadata Service.
    Returns the participant_id if found, otherwise returns a default message.
    """
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
    Check if the GitHub repository for the participant exists in the user's workspace directory.
    If not, clone it to that location.
    """
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
        # Create workspace directory if it doesn't exist
        if not os.path.exists(workspace_path):
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
    survey_url = os.getenv('SURVEY_URL', '#')
    
    if survey_url == '#':
        return render_template_string('''
            <!DOCTYPE html>
            <html>
            <head>
                <title>{{ participant_id }} - Background Survey</title>
            </head>
            <body>
                <h1>Background Survey - {{ participant_id }}</h1>
                <p style="color: red;">Survey URL not configured. Please set the SURVEY_URL environment variable.</p>
            </body>
            </html>
        ''', participant_id=participant_id)
    
    return render_template_string('''
        <!DOCTYPE html>
        <html>
        <head>
            <title>{{ participant_id }} - Background Survey</title>
        </head>
        <body>
            <h1>Background Survey - {{ participant_id }}</h1>
            <a href="{{ url }}?participant={{ participant_id }}" target="_blank">Start Survey</a>
        </body>
        </html>
    ''', participant_id=participant_id, url=survey_url)

if __name__ == '__main__':
    # Get participant ID and check/clone repository on startup
    participant_id = get_participant_id()
    print(f"Starting server for participant: {participant_id}")
    
    # Check and clone repository if needed
    check_and_clone_repository(participant_id)
    
    app.run(host='127.0.0.1', port=8085)