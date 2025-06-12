import os
import time
from flask import Flask, render_template, request, session, redirect, url_for, jsonify
from dotenv import load_dotenv
from helpers import (
    load_task_requirements, get_tasks_for_stage, get_session_data, update_session_data,
    get_coding_condition, get_study_stage, get_participant_id, open_vscode_with_repository,
    check_and_clone_repository, commit_code_changes, test_github_connectivity,
    setup_repository_for_stage, log_route_visit, should_log_route, mark_route_as_logged,
    mark_stage_transition
)

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

# Development mode configuration
DEVELOPMENT_MODE = os.getenv('DEVELOPMENT_MODE', 'false').lower() == 'true'
DEV_PARTICIPANT_ID = os.getenv('DEV_PARTICIPANT_ID', 'dev-participant-001')
DEV_STAGE = int(os.getenv('DEV_STAGE', '1'))

# GitHub authentication configuration
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN', '')
GITHUB_ORG = os.getenv('GITHUB_ORG', 'LMU-Vibe-Coding-Study')

# Load task requirements at startup
TASK_REQUIREMENTS = load_task_requirements()

@app.route('/')
def home():
    participant_id = get_participant_id(DEVELOPMENT_MODE, DEV_PARTICIPANT_ID)
    study_stage = get_study_stage(participant_id, DEVELOPMENT_MODE, DEV_STAGE)
    
    # Log route visit if this is the first time
    if should_log_route(session, 'home', study_stage):
        log_route_visit(
            participant_id=participant_id,
            route_name='home',
            development_mode=DEVELOPMENT_MODE,
            study_stage=study_stage,
            session_data={'first_home_visit': True},
            github_token=GITHUB_TOKEN,
            github_org=GITHUB_ORG
        )
        mark_route_as_logged(session, 'home', study_stage)
    
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

@app.route('/debug-session')
def debug_session():
    """Debug route to display complete session state during development"""
    if not DEVELOPMENT_MODE:
        return "Only available in development mode", 403
    
    participant_id = get_participant_id(DEVELOPMENT_MODE, DEV_PARTICIPANT_ID)
    study_stage = get_study_stage(participant_id, DEVELOPMENT_MODE, DEV_STAGE)
    
    # Get session data for both stages
    stage1_data = get_session_data(session, 1)
    stage2_data = get_session_data(session, 2)
    
    # Calculate timer info if timer is started
    timer_info = {}
    for stage, data in [(1, stage1_data), (2, stage2_data)]:
        if data['timer_start']:
            elapsed = time.time() - data['timer_start']
            remaining = max(0, 2400 - elapsed)
            timer_info[stage] = {
                'elapsed_seconds': elapsed,
                'elapsed_minutes': elapsed / 60,
                'remaining_seconds': remaining,
                'remaining_minutes': remaining / 60,
                'timer_start_timestamp': data['timer_start'],
                'timer_start_readable': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(data['timer_start']))
            }
        else:
            timer_info[stage] = {'status': 'Not started'}
    
    # Build HTML response
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Development Session Debug</title>
        <style>
            body {{ font-family: monospace; margin: 20px; }}
            .section {{ margin: 20px 0; padding: 15px; border: 1px solid #ccc; border-radius: 5px; }}
            .stage {{ background: #f8f9fa; }}
            .timer {{ background: #fff3cd; }}
            .session {{ background: #d4edda; }}
            .actions {{ background: #cce7ff; }}
            table {{ border-collapse: collapse; width: 100%; margin: 10px 0; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            th {{ background: #f2f2f2; }}
            .btn {{ padding: 8px 16px; margin: 5px; text-decoration: none; border-radius: 3px; display: inline-block; }}
            .btn-danger {{ background: #dc3545; color: white; }}
            .btn-primary {{ background: #007bff; color: white; }}
            .btn-success {{ background: #28a745; color: white; }}
        </style>
    </head>
    <body>
        <h1>🐛 Development Session Debug</h1>
        <p><strong>Current Time:</strong> {time.strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p><strong>Participant ID:</strong> {participant_id}</p>
        <p><strong>Current Study Stage:</strong> {study_stage}</p>
        <p><strong>Development Mode:</strong> {DEVELOPMENT_MODE}</p>
        
        <div class="section actions">
            <h3>🔧 Quick Actions</h3>
            <a href="/clear-session" class="btn btn-danger">Clear All Session Data</a>
            <a href="/task" class="btn btn-primary">Go to Task Page</a>
            <a href="/" class="btn btn-success">Go to Home</a>
            <a href="/debug-session" class="btn btn-primary">Refresh Debug</a>
        </div>
        
        <div class="section session">
            <h3>📋 Raw Session Data</h3>
            <table>
                <tr><th>Key</th><th>Value</th></tr>
    """
    
    # Add raw session data
    for key, value in session.items():
        html += f"<tr><td>{key}</td><td>{value}</td></tr>"
    
    html += """
            </table>
        </div>
    """
    
    # Add stage-specific data
    for stage in [1, 2]:
        data = stage1_data if stage == 1 else stage2_data
        timer = timer_info[stage]
        
        html += f"""
        <div class="section stage">
            <h3>🎯 Stage {stage} Data</h3>
            <table>
                <tr><th>Property</th><th>Value</th></tr>
                <tr><td>Current Task</td><td>{data['current_task']}</td></tr>
                <tr><td>Completed Tasks</td><td>{data['completed_tasks']} (Count: {len(data['completed_tasks'])})</td></tr>
                <tr><td>Timer Finished</td><td>{data['timer_finished']}</td></tr>
                <tr><td>Timer Start</td><td>{data['timer_start']}</td></tr>
            </table>
        </div>
        
        <div class="section timer">
            <h3>⏰ Stage {stage} Timer Info</h3>
            <table>
                <tr><th>Property</th><th>Value</th></tr>
        """
        
        if 'status' in timer:
            html += f"<tr><td>Status</td><td>{timer['status']}</td></tr>"
        else:
            html += f"""
                <tr><td>Start Time</td><td>{timer['timer_start_readable']}</td></tr>
                <tr><td>Start Timestamp</td><td>{timer['timer_start_timestamp']}</td></tr>
                <tr><td>Elapsed Time</td><td>{timer['elapsed_seconds']:.1f} seconds ({timer['elapsed_minutes']:.1f} minutes)</td></tr>
                <tr><td>Remaining Time</td><td>{timer['remaining_seconds']:.1f} seconds ({timer['remaining_minutes']:.1f} minutes)</td></tr>
                <tr><td>Timer Status</td><td>{'⚠️ EXPIRED' if timer['remaining_seconds'] <= 0 else '✅ Running'}</td></tr>
            """
        
        html += """
            </table>
        </div>
        """
    
    # Add task requirements info
    task_requirements = get_tasks_for_stage(study_stage, TASK_REQUIREMENTS)
    html += f"""
        <div class="section">
            <h3>📝 Task Requirements (Stage {study_stage})</h3>
            <p><strong>Total Tasks:</strong> {len(task_requirements)}</p>
            <table>
                <tr><th>Task ID</th><th>Title</th><th>Status</th></tr>
    """
    
    current_task = stage1_data['current_task'] if study_stage == 1 else stage2_data['current_task']
    completed_tasks = stage1_data['completed_tasks'] if study_stage == 1 else stage2_data['completed_tasks']
    
    for req in task_requirements:
        if req['id'] in completed_tasks:
            status = "✅ Completed"
        elif req['id'] == current_task:
            status = "🔄 Current"
        elif req['id'] < current_task:
            status = "❓ Skipped"
        else:
            status = "🔒 Locked"
        
        html += f"<tr><td>{req['id']}</td><td>{req['title']}</td><td>{status}</td></tr>"
    
    html += """
            </table>
        </div>
        
        <div class="section">
            <h3>🔍 VS Code Status</h3>
            <table>
                <tr><th>Stage</th><th>VS Code Opened</th></tr>
    """
    
    for stage in [1, 2]:
        vscode_key = f'vscode_opened_stage{stage}'
        vscode_status = "✅ Yes" if session.get(vscode_key, False) else "❌ No"
        html += f"<tr><td>Stage {stage}</td><td>{vscode_status}</td></tr>"
    
    html += """
            </table>
        </div>
        
        <script>
            // Auto-refresh every 5 seconds
            setTimeout(() => {
                window.location.reload();
            }, 5000);
        </script>
    </body>
    </html>
    """
    
    return html

@app.route('/background-questionnaire')
def background_questionnaire():
    participant_id = get_participant_id(DEVELOPMENT_MODE, DEV_PARTICIPANT_ID)
    study_stage = get_study_stage(participant_id, DEVELOPMENT_MODE, DEV_STAGE)
    
    # Log route visit if this is the first time
    if should_log_route(session, 'background_questionnaire', study_stage):
        log_route_visit(
            participant_id=participant_id,
            route_name='background_questionnaire',
            development_mode=DEVELOPMENT_MODE,
            study_stage=study_stage,
            session_data={'first_background_questionnaire_visit': True},
            github_token=GITHUB_TOKEN,
            github_org=GITHUB_ORG
        )
        mark_route_as_logged(session, 'background_questionnaire', study_stage)
    
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
    participant_id = get_participant_id(DEVELOPMENT_MODE, DEV_PARTICIPANT_ID)
    study_stage = get_study_stage(participant_id, DEVELOPMENT_MODE, DEV_STAGE)
    
    # Log route visit if this is the first time
    if should_log_route(session, 'ux_questionnaire', study_stage):
        # Include session data for context about study completion
        session_data = get_session_data(session, study_stage)
        session_data['study_completion'] = True
        session_data['ux_questionnaire_accessed'] = True
        
        log_route_visit(
            participant_id=participant_id,
            route_name='ux_questionnaire',
            development_mode=DEVELOPMENT_MODE,
            study_stage=study_stage,
            session_data=session_data,
            github_token=GITHUB_TOKEN,
            github_org=GITHUB_ORG
        )
        mark_route_as_logged(session, 'ux_questionnaire', study_stage)
    
    ux_survey_url = os.getenv('UX_SURVEY_URL', '#')
    
    # Commit any remaining code changes before leaving for the survey
    commit_message = "Session ended - proceeding to UX questionnaire"
    commit_success = commit_code_changes(participant_id, study_stage, commit_message, DEVELOPMENT_MODE, GITHUB_TOKEN, GITHUB_ORG)
    
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
    participant_id = get_participant_id(DEVELOPMENT_MODE, DEV_PARTICIPANT_ID)
    study_stage = get_study_stage(participant_id, DEVELOPMENT_MODE, DEV_STAGE)
    
    # Log route visit if this is the first time
    if should_log_route(session, 'tutorial', study_stage):
        coding_condition = get_coding_condition(participant_id)
        session_data = {
            'tutorial_accessed': True,
            'coding_condition': coding_condition
        }
        
        log_route_visit(
            participant_id=participant_id,
            route_name='tutorial',
            development_mode=DEVELOPMENT_MODE,
            study_stage=study_stage,
            session_data=session_data,
            github_token=GITHUB_TOKEN,
            github_org=GITHUB_ORG
        )
        mark_route_as_logged(session, 'tutorial', study_stage)
    
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
    participant_id = get_participant_id(DEVELOPMENT_MODE, DEV_PARTICIPANT_ID)
    study_stage = get_study_stage(participant_id, DEVELOPMENT_MODE, DEV_STAGE)
    coding_condition = get_coding_condition(participant_id)
    
    # Log route visit if this is the first time
    if should_log_route(session, 'welcome_back', study_stage):
        session_data = {
            'stage_transition': f'stage_1_to_stage_2',
            'coding_condition': coding_condition,
            'returning_participant': True
        }
        
        log_route_visit(
            participant_id=participant_id,
            route_name='welcome_back',
            development_mode=DEVELOPMENT_MODE,
            study_stage=study_stage,
            session_data=session_data,
            github_token=GITHUB_TOKEN,
            github_org=GITHUB_ORG
        )
        mark_route_as_logged(session, 'welcome_back', study_stage)
        
        # Mark explicit stage transition from 1 to 2
        mark_stage_transition(
            participant_id=participant_id,
            from_stage=1,
            to_stage=2,
            development_mode=DEVELOPMENT_MODE,
            github_token=GITHUB_TOKEN,
            github_org=GITHUB_ORG
        )
    
    # Redirect to home if this is actually stage 1
    if study_stage == 1:
        return redirect(url_for('home'))
    
    return render_template('welcome_back.jinja', 
                         participant_id=participant_id,
                         study_stage=study_stage,
                         coding_condition=coding_condition)

@app.route('/task')
def task():
    participant_id = get_participant_id(DEVELOPMENT_MODE, DEV_PARTICIPANT_ID)
    study_stage = get_study_stage(participant_id, DEVELOPMENT_MODE, DEV_STAGE)
    coding_condition = get_coding_condition(participant_id)
    
    # Set up repository for the current stage (ensure correct branch)
    setup_success = setup_repository_for_stage(participant_id, study_stage, DEVELOPMENT_MODE, GITHUB_TOKEN, GITHUB_ORG)
    if not setup_success:
        print(f"Warning: Failed to set up repository for stage {study_stage}")
    
    # Get stage-specific session data
    session_data = get_session_data(session, study_stage)
    current_task = session_data['current_task']
    completed_tasks = session_data['completed_tasks']
    timer_start = session_data['timer_start']
    timer_finished = session_data['timer_finished']
    
    # Log route visit if this is the first time (important transition to coding phase)
    if should_log_route(session, 'task', study_stage):
        log_session_data = {
            'coding_session_start': True,
            'coding_condition': coding_condition,
            'timer_start': timer_start,
            'current_task': current_task,
            'completed_tasks': completed_tasks
        }
        
        log_route_visit(
            participant_id=participant_id,
            route_name='task',
            development_mode=DEVELOPMENT_MODE,
            study_stage=study_stage,
            session_data=log_session_data,
            github_token=GITHUB_TOKEN,
            github_org=GITHUB_ORG
        )
        mark_route_as_logged(session, 'task', study_stage)
    
    # Initialize timer if not started yet
    if timer_start is None:
        timer_start = time.time()
        update_session_data(session, study_stage, timer_start=timer_start)
        
        # Make an initial commit to mark the start of this coding session
        commit_message = f"Started coding session - Condition: {coding_condition}"
        commit_success = commit_code_changes(participant_id, study_stage, commit_message, DEVELOPMENT_MODE, GITHUB_TOKEN, GITHUB_ORG)
        
        if commit_success:
            print(f"Initial commit made for session start - participant {participant_id}, stage {study_stage}")
        else:
            print(f"No initial commit needed or failed for participant {participant_id}, stage {study_stage}")
    
    # Calculate elapsed time and remaining time
    elapsed_time = time.time() - timer_start
    remaining_time = max(0, 200 - elapsed_time)  # 40 minutes = 2400 seconds
    
    # Get tasks appropriate for the current study stage
    task_requirements = get_tasks_for_stage(study_stage, TASK_REQUIREMENTS)
    
    # Check if this is the first time accessing the task page for this stage
    # If so, automatically open VS Code with the repository
    stage_key = f'stage{study_stage}'
    vscode_opened_key = f'vscode_opened_{stage_key}'
    
    if not session.get(vscode_opened_key, False):
        # Mark that we've attempted to open VS Code for this stage
        session[vscode_opened_key] = True
        
        # Try to open VS Code with the repository
        vscode_success = open_vscode_with_repository(participant_id, DEVELOPMENT_MODE, study_stage)
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
    participant_id = get_participant_id(DEVELOPMENT_MODE, DEV_PARTICIPANT_ID)
    study_stage = get_study_stage(participant_id, DEVELOPMENT_MODE, DEV_STAGE)
    
    # Try to open VS Code with the repository
    vscode_success = open_vscode_with_repository(participant_id, DEVELOPMENT_MODE, study_stage)
    
    if vscode_success:
        print(f"VS Code opened successfully for participant {participant_id} (manual request)")
    else:
        print(f"Failed to open VS Code for participant {participant_id} (manual request)")
    
    # Redirect back to the task page
    return redirect(url_for('task'))

@app.route('/complete-task', methods=['POST'])
def complete_task():
    participant_id = get_participant_id(DEVELOPMENT_MODE, DEV_PARTICIPANT_ID)
    study_stage = get_study_stage(participant_id, DEVELOPMENT_MODE, DEV_STAGE)
    task_id = int(request.form.get('task_id', 1))
    
    # Get stage-specific session data
    session_data = get_session_data(session, study_stage)
    completed_tasks = session_data['completed_tasks']
    timer_finished = session_data['timer_finished']
    
    # Get tasks appropriate for the current study stage
    task_requirements = get_tasks_for_stage(study_stage, TASK_REQUIREMENTS)
    
    # Debug logging
    print(f"Complete task - Participant: {participant_id}, Stage: {study_stage}")
    print(f"Completing task {task_id}, Previously completed: {completed_tasks}")
    print(f"Timer finished: {timer_finished}")
    
    if task_id not in completed_tasks:
        completed_tasks.append(task_id)
        update_session_data(session, study_stage, completed_tasks=completed_tasks)
        print(f"Task {task_id} marked as completed for stage {study_stage}")
        
        # Log task completion event
        task_title = "Unknown Task"
        if task_id <= len(task_requirements):
            task_title = task_requirements[task_id - 1].get('title', f'Task {task_id}')
        
        log_session_data = {
            'event_type': 'task_completion',
            'task_id': task_id,
            'task_title': task_title,
            'completed_tasks': completed_tasks,
            'timer_finished': timer_finished
        }
        
        # Log this as a special event (not route-based)
        log_route_visit(
            participant_id=participant_id,
            route_name=f'task_completion_{task_id}',
            development_mode=DEVELOPMENT_MODE,
            study_stage=study_stage,
            session_data=log_session_data,
            github_token=GITHUB_TOKEN,
            github_org=GITHUB_ORG
        )
        
        # Commit code changes when task is completed
        commit_message = f"Completed task {task_id}: {task_title}"
        commit_success = commit_code_changes(participant_id, study_stage, commit_message, DEVELOPMENT_MODE, GITHUB_TOKEN, GITHUB_ORG)
        
        if commit_success:
            print(f"Code changes committed for task {task_id}")
        else:
            print(f"Failed to commit code changes for task {task_id}")
    
    # Only move to next task if timer hasn't finished
    if not timer_finished and task_id < len(task_requirements):
        next_task = task_id + 1
        update_session_data(session, study_stage, current_task=next_task)
        print(f"Moving to next task: {next_task}")
    else:
        print(f"Timer finished or all tasks completed for stage {study_stage}")
    
    return redirect(url_for('task'))

@app.route('/timer-expired', methods=['POST'])
def timer_expired():
    """Handle when the 40-minute timer expires"""
    participant_id = get_participant_id(DEVELOPMENT_MODE, DEV_PARTICIPANT_ID)
    study_stage = get_study_stage(participant_id, DEVELOPMENT_MODE, DEV_STAGE)
    
    # Mark timer as finished
    update_session_data(session, study_stage, timer_finished=True)
    
    # Log timer expiration event
    session_data = get_session_data(session, study_stage)
    log_session_data = {
        'event_type': 'timer_expired',
        'timer_duration_minutes': 40,
        'completed_tasks': session_data['completed_tasks'],
        'current_task': session_data['current_task']
    }
    
    log_route_visit(
        participant_id=participant_id,
        route_name='timer_expired',
        development_mode=DEVELOPMENT_MODE,
        study_stage=study_stage,
        session_data=log_session_data,
        github_token=GITHUB_TOKEN,
        github_org=GITHUB_ORG
    )
    
    # Commit any code changes when timer expires
    commit_message = "Timer expired - 40 minutes completed"
    commit_success = commit_code_changes(participant_id, study_stage, commit_message, DEVELOPMENT_MODE, GITHUB_TOKEN, GITHUB_ORG)
    
    if commit_success:
        print(f"Code changes committed when timer expired for participant {participant_id}")
    else:
        print(f"No changes to commit or commit failed when timer expired for participant {participant_id}")
    
    return jsonify({'status': 'success'})

@app.route('/get-timer-status')
def get_timer_status():
    """Get current timer status"""
    participant_id = get_participant_id(DEVELOPMENT_MODE, DEV_PARTICIPANT_ID)
    study_stage = get_study_stage(participant_id, DEVELOPMENT_MODE, DEV_STAGE)
    
    session_data = get_session_data(session, study_stage)
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
    participant_id = get_participant_id(DEVELOPMENT_MODE, DEV_PARTICIPANT_ID)
    study_stage = get_study_stage(participant_id, DEVELOPMENT_MODE, DEV_STAGE)
    print(f"Starting server for participant: {participant_id}")
    print(f"Study stage: {study_stage} ({'Repository not found' if study_stage == 1 else 'Repository exists'})")
    
    # Test GitHub connectivity
    print("\nTesting GitHub connectivity...")
    if GITHUB_TOKEN:
        print(f"GitHub authentication enabled for organization: {GITHUB_ORG}")
    else:
        print("No GitHub token provided - using public access only")
    
    github_available = test_github_connectivity(participant_id, GITHUB_TOKEN, GITHUB_ORG)
    if not github_available:
        print("Warning: GitHub repository may not be accessible")
    
    # Check and clone repository if needed
    print("\nChecking repository...")
    check_and_clone_repository(participant_id, DEVELOPMENT_MODE, GITHUB_TOKEN, GITHUB_ORG)
    
    app.run(host='127.0.0.1', port=8085, debug=True)