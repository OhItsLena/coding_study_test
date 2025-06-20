import os
import time
import json
from flask import Flask, render_template, request, session, redirect, url_for, jsonify
from dotenv import load_dotenv
from services import (
    load_task_requirements, get_tasks_for_stage, get_session_data, update_session_data,
    get_coding_condition, get_study_stage, get_participant_id, open_vscode_with_repository,
    check_and_clone_repository, commit_code_changes, test_github_connectivity,
    setup_repository_for_stage, log_route_visit, should_log_route, mark_route_as_logged,
    mark_stage_transition, get_async_github_stats, get_async_github_queue_size,
    load_tutorials, get_tutorial_by_condition,
    test_github_connectivity_async, stop_async_github_service, wait_for_async_github_completion,
    save_vscode_workspace_storage, save_vscode_workspace_storage_async,
    start_session_recording, stop_session_recording, is_recording_active,
    setup_tutorial_branch, open_vscode_with_tutorial, push_tutorial_code,
    get_session_log_history, determine_correct_route
)

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

# Development mode configuration
DEVELOPMENT_MODE = os.getenv('DEVELOPMENT_MODE', 'false').lower() == 'true'
DEV_PARTICIPANT_ID = os.getenv('DEV_PARTICIPANT_ID', 'dev-participant-001')
DEV_STAGE = int(os.getenv('DEV_STAGE', '1'))
DEV_CODING_CONDITION = os.getenv('DEV_CODING_CONDITION', 'vibe')

# GitHub authentication configuration
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN', '')
GITHUB_ORG = os.getenv('GITHUB_ORG', 'LMU-Vibe-Coding-Study')

# Async GitHub configuration
ASYNC_GITHUB_MODE = os.getenv('ASYNC_GITHUB_MODE', 'true').lower() == 'true'

# Load task requirements at startup
TASK_REQUIREMENTS = load_task_requirements()

# Load tutorials at startup
TUTORIALS = load_tutorials()

def check_automatic_rerouting(current_route, participant_id, study_stage, development_mode):
    """
    Check if user should be automatically rerouted based on session history.
    
    Args:
        current_route: The route the user is trying to access
        participant_id: The participant's ID
        study_stage: Current study stage
        development_mode: Whether in development mode
    
    Returns:
        Flask redirect response if rerouting is needed, None otherwise
    """
    try:
        # Determine what route the user should be on based on their history
        correct_route = determine_correct_route(participant_id, development_mode, study_stage, current_route)
        
        if correct_route and correct_route != current_route:
            print(f"Automatic rerouting: {current_route} -> {correct_route} for participant {participant_id}, stage {study_stage}")
            
            # Map route names to URL endpoints
            route_mapping = {
                'home': 'home',
                'background_questionnaire': 'background_questionnaire', 
                'tutorial': 'tutorial',
                'task': 'task',
                'ux_questionnaire': 'ux_questionnaire',
                'goodbye': 'goodbye',
                'welcome_back': 'welcome_back'
            }
            
            if correct_route in route_mapping:
                return redirect(url_for(route_mapping[correct_route]))
        
        return None
        
    except Exception as e:
        print(f"Error in automatic rerouting: {str(e)}")
        return None

@app.route('/')
def home():
    participant_id = get_participant_id(DEVELOPMENT_MODE, DEV_PARTICIPANT_ID)
    study_stage = get_study_stage(participant_id, DEVELOPMENT_MODE, DEV_STAGE)
    
    # Check for automatic rerouting based on session history
    reroute = check_automatic_rerouting('home', participant_id, study_stage, DEVELOPMENT_MODE)
    if reroute:
        return reroute
    
    coding_condition = get_coding_condition(participant_id, DEVELOPMENT_MODE, DEV_CODING_CONDITION)
    
    # Log route visit if this is the first time
    if should_log_route(session, 'home', study_stage):
        log_route_visit(
            participant_id=participant_id,
            route_name='home',
            development_mode=DEVELOPMENT_MODE,
            study_stage=study_stage,
            session_data={'first_home_visit': True},
            github_token=GITHUB_TOKEN,
            github_org=GITHUB_ORG,
            async_mode=ASYNC_GITHUB_MODE
        )
        mark_route_as_logged(session, 'home', study_stage)
    
    # Stage 2 participants should go directly to welcome back screen
    if study_stage == 2:
        return redirect(url_for('welcome_back'))
    
    return render_template('home.jinja', 
                         participant_id=participant_id,
                         study_stage=study_stage,
                         coding_condition=coding_condition)

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
    
    # Prepare data for template
    task_requirements = get_tasks_for_stage(study_stage, TASK_REQUIREMENTS)
    current_task = stage1_data['current_task'] if study_stage == 1 else stage2_data['current_task']
    completed_tasks = stage1_data['completed_tasks'] if study_stage == 1 else stage2_data['completed_tasks']
    
    # Prepare VS Code status
    vscode_status = {}
    for stage in [1, 2]:
        vscode_key = f'vscode_opened_stage{stage}'
        vscode_status[stage] = session.get(vscode_key, False)
    
    # Prepare session items for template
    session_items = list(session.items())
    
    # Check recording status
    recording_active = is_recording_active()
    
    return render_template('debug_session.jinja',
                         current_time=time.strftime('%Y-%m-%d %H:%M:%S'),
                         participant_id=participant_id,
                         study_stage=study_stage,
                         development_mode=DEVELOPMENT_MODE,
                         stage1_data=stage1_data,
                         stage2_data=stage2_data,
                         timer_info=timer_info,
                         task_requirements=task_requirements,
                         current_task=current_task,
                         completed_tasks=completed_tasks,
                         vscode_status=vscode_status,
                         session_items=session_items,
                         recording_active=recording_active)

@app.route('/background-questionnaire')
def background_questionnaire():
    participant_id = get_participant_id(DEVELOPMENT_MODE, DEV_PARTICIPANT_ID)
    study_stage = get_study_stage(participant_id, DEVELOPMENT_MODE, DEV_STAGE)
    
    # Check for automatic rerouting based on session history
    reroute = check_automatic_rerouting('background_questionnaire', participant_id, study_stage, DEVELOPMENT_MODE)
    if reroute:
        return reroute
    
    # Check and clone repository when user starts the session (first time accessing this route)
    if should_log_route(session, 'background_questionnaire', study_stage):
        print(f"\nUser started session - checking and cloning repository for participant: {participant_id}")
        check_and_clone_repository(participant_id, DEVELOPMENT_MODE, GITHUB_TOKEN, GITHUB_ORG)
    
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
    
    # Check for automatic rerouting based on session history
    reroute = check_automatic_rerouting('ux_questionnaire', participant_id, study_stage, DEVELOPMENT_MODE)
    if reroute:
        return reroute
    
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
    
    # Save VS Code workspace storage at the end of the coding session
    print(f"Saving VS Code workspace storage for participant {participant_id}, stage {study_stage}")
    if ASYNC_GITHUB_MODE:
        # Use async mode for background processing
        save_vscode_workspace_storage_async(
            participant_id, study_stage, DEVELOPMENT_MODE, GITHUB_TOKEN, GITHUB_ORG
        )
        print(f"VS Code workspace storage save queued for background processing for participant {participant_id}")
    else:
        # Use synchronous mode
        vscode_storage_success = save_vscode_workspace_storage(
            participant_id, study_stage, DEVELOPMENT_MODE, GITHUB_TOKEN, GITHUB_ORG
        )
        
        if vscode_storage_success:
            print(f"VS Code workspace storage successfully saved for participant {participant_id}")
        else:
            print(f"Failed to save VS Code workspace storage for participant {participant_id}")
    
    if ux_survey_url == '#':
        return render_template('survey_error.jinja', 
                             participant_id=participant_id,
                             study_stage=study_stage)
    
    return render_template('ux_questionnaire.jinja', 
                         participant_id=participant_id,
                         study_stage=study_stage,
                         url=ux_survey_url)

@app.route('/goodbye')
def goodbye():
    participant_id = get_participant_id(DEVELOPMENT_MODE, DEV_PARTICIPANT_ID)
    study_stage = get_study_stage(participant_id, DEVELOPMENT_MODE, DEV_STAGE)
    
    # Check for automatic rerouting based on session history
    reroute = check_automatic_rerouting('goodbye', participant_id, study_stage, DEVELOPMENT_MODE)
    if reroute:
        return reroute
    
    coding_condition = get_coding_condition(participant_id, DEVELOPMENT_MODE, DEV_CODING_CONDITION)
    
    # Log route visit if this is the first time
    if should_log_route(session, 'goodbye', study_stage):
        # Include session data for context about study completion
        session_data = get_session_data(session, study_stage)
        session_data['study_session_complete'] = True
        session_data['goodbye_page_accessed'] = True
        session_data['final_coding_condition'] = coding_condition
        
        log_route_visit(
            participant_id=participant_id,
            route_name='goodbye',
            development_mode=DEVELOPMENT_MODE,
            study_stage=study_stage,
            session_data=session_data,
            github_token=GITHUB_TOKEN,
            github_org=GITHUB_ORG,
            async_mode=ASYNC_GITHUB_MODE
        )
        mark_route_as_logged(session, 'goodbye', study_stage)
        
        # Stop screen recording when participant reaches goodbye page (study completely finished)
        if is_recording_active():
            recording_stopped = stop_session_recording()
            if recording_stopped:
                print(f"✅ Screen recording stopped - participant {participant_id} reached goodbye page")
            else:
                print(f"❌ Failed to stop screen recording for participant {participant_id} at goodbye page")
        else:
            print(f"ℹ️ No active screen recording to stop for participant {participant_id} at goodbye page")
    
    return render_template('goodbye.jinja', 
                         participant_id=participant_id,
                         study_stage=study_stage,
                         coding_condition=coding_condition)

@app.route('/tutorial')
def tutorial():
    participant_id = get_participant_id(DEVELOPMENT_MODE, DEV_PARTICIPANT_ID)
    study_stage = get_study_stage(participant_id, DEVELOPMENT_MODE, DEV_STAGE)
    
    # Check for automatic rerouting based on session history
    reroute = check_automatic_rerouting('tutorial', participant_id, study_stage, DEVELOPMENT_MODE)
    if reroute:
        return reroute
    
    # Log route visit if this is the first time
    if should_log_route(session, 'tutorial', study_stage):
        coding_condition = get_coding_condition(participant_id, DEVELOPMENT_MODE, DEV_CODING_CONDITION)
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
            github_org=GITHUB_ORG,
            async_mode=ASYNC_GITHUB_MODE
        )
        mark_route_as_logged(session, 'tutorial', study_stage)
        
        # Set up tutorial branch and open VS Code (only on first visit)
        print(f"Setting up tutorial branch for {participant_id}")
        tutorial_setup_success = setup_tutorial_branch(
            participant_id, DEVELOPMENT_MODE, GITHUB_TOKEN, GITHUB_ORG
        )
        
        if tutorial_setup_success:
            print(f"Opening VS Code with tutorial for {participant_id}")
            vscode_success = open_vscode_with_tutorial(participant_id, DEVELOPMENT_MODE)
            if not vscode_success:
                print(f"Failed to open VS Code with tutorial for {participant_id}")
        else:
            print(f"Failed to set up tutorial branch for {participant_id}")
    
    # Stage 2 participants should skip the tutorial
    if study_stage == 2:
        return redirect(url_for('welcome_back'))
    
    coding_condition = get_coding_condition(participant_id, DEVELOPMENT_MODE, DEV_CODING_CONDITION)
    tutorial_data = get_tutorial_by_condition(coding_condition, TUTORIALS)
    
    return render_template('tutorial.jinja', 
                         participant_id=participant_id,
                         study_stage=study_stage,
                         coding_condition=coding_condition,
                         tutorial=tutorial_data)

@app.route('/welcome-back')
def welcome_back():
    participant_id = get_participant_id(DEVELOPMENT_MODE, DEV_PARTICIPANT_ID)
    study_stage = get_study_stage(participant_id, DEVELOPMENT_MODE, DEV_STAGE)
    
    # Check for automatic rerouting based on session history
    reroute = check_automatic_rerouting('welcome_back', participant_id, study_stage, DEVELOPMENT_MODE)
    if reroute:
        return reroute
    
    coding_condition = get_coding_condition(participant_id, DEVELOPMENT_MODE, DEV_CODING_CONDITION)
    
    # Check and clone repository when stage 2 user starts (first time accessing this route)
    if should_log_route(session, 'welcome_back', study_stage):
        print(f"\nStage 2 user started session - checking and cloning repository for participant: {participant_id}")
        check_and_clone_repository(participant_id, DEVELOPMENT_MODE, GITHUB_TOKEN, GITHUB_ORG)
    
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
    
    # Check for automatic rerouting based on session history
    reroute = check_automatic_rerouting('task', participant_id, study_stage, DEVELOPMENT_MODE)
    if reroute:
        return reroute
    
    coding_condition = get_coding_condition(participant_id, DEVELOPMENT_MODE, DEV_CODING_CONDITION)
    
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
            github_org=GITHUB_ORG,
            async_mode=ASYNC_GITHUB_MODE
        )
        mark_route_as_logged(session, 'task', study_stage)
        
        # Push tutorial code when transitioning from tutorial to task (only for stage 1)
        if study_stage == 1:
            print(f"Pushing tutorial code for {participant_id} before starting coding task")
            push_tutorial_code(
                participant_id, DEVELOPMENT_MODE, GITHUB_TOKEN, GITHUB_ORG, 
                async_mode=ASYNC_GITHUB_MODE
            )
    
    # Initialize timer if not started yet
    if timer_start is None:
        timer_start = time.time()
        update_session_data(session, study_stage, timer_start=timer_start)
        
        # Recording already started at server startup, no need to start again
        print(f"Coding session timer started for participant {participant_id}, stage {study_stage}")
        
        # Make an initial commit to mark the start of this coding session
        commit_message = f"Started coding session - Condition: {coding_condition}"
        commit_success = commit_code_changes(participant_id, study_stage, commit_message, DEVELOPMENT_MODE, GITHUB_TOKEN, GITHUB_ORG, async_mode=ASYNC_GITHUB_MODE)
        
        if commit_success:
            print(f"Initial commit {'queued' if ASYNC_GITHUB_MODE else 'made'} for session start - participant {participant_id}, stage {study_stage}")
        else:
            print(f"No initial commit needed or failed for participant {participant_id}, stage {study_stage}")
    
    # Calculate elapsed time and remaining time
    elapsed_time = time.time() - timer_start
    remaining_time = max(0, 2400 - elapsed_time)  # 40 minutes = 2400 seconds
    
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
            github_org=GITHUB_ORG,
            async_mode=ASYNC_GITHUB_MODE
        )
        
        # Commit code changes when task is completed
        commit_message = f"Completed task {task_id}: {task_title}"
        commit_success = commit_code_changes(participant_id, study_stage, commit_message, DEVELOPMENT_MODE, GITHUB_TOKEN, GITHUB_ORG, async_mode=ASYNC_GITHUB_MODE)
        
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

@app.route('/debug-async-github')
def debug_async_github():
    """Debug route to display async GitHub service statistics during development"""
    if not DEVELOPMENT_MODE:
        return "Only available in development mode", 403
    
    stats = get_async_github_stats()
    queue_size = get_async_github_queue_size()
    
    return render_template('debug_async_github.jinja',
                         current_time=time.strftime('%Y-%m-%d %H:%M:%S'),
                         async_mode=ASYNC_GITHUB_MODE,
                         development_mode=DEVELOPMENT_MODE,
                         github_token=GITHUB_TOKEN,
                         github_org=GITHUB_ORG,
                         stats=stats,
                         queue_size=queue_size)

@app.route('/debug-recording')
def debug_recording():
    """Debug route for manually controlling screen recording during development"""
    if not DEVELOPMENT_MODE:
        return "Only available in development mode", 403
    
    action = request.args.get('action', 'status')
    participant_id = get_participant_id(DEVELOPMENT_MODE, DEV_PARTICIPANT_ID)
    study_stage = get_study_stage(participant_id, DEVELOPMENT_MODE, DEV_STAGE)
    
    if action == 'start':
        result = start_session_recording(participant_id, study_stage, DEVELOPMENT_MODE)
        message = f"Recording started: {result}"
    elif action == 'stop':
        result = stop_session_recording()
        message = f"Recording stopped: {result}"
    else:
        message = "Available actions: ?action=start or ?action=stop"
    
    recording_active = is_recording_active()
    
    return f"""
    <h2>🎥 Screen Recording Debug</h2>
    <p><strong>Participant:</strong> {participant_id}</p>
    <p><strong>Stage:</strong> {study_stage}</p>
    <p><strong>Recording Active:</strong> {'✅ YES' if recording_active else '❌ NO'}</p>
    <p><strong>Action Result:</strong> {message}</p>
    <hr>
    <a href="/debug-recording?action=start">Start Recording</a> | 
    <a href="/debug-recording?action=stop">Stop Recording</a> | 
    <a href="/debug-recording">Status Only</a>
    <br><br>
    <a href="/debug-session">← Back to Debug Session</a>
    """

@app.route('/debug-routing')
def debug_routing():
    """Debug route to display routing logic and session history during development"""
    if not DEVELOPMENT_MODE:
        return "Only available in development mode", 403
    
    participant_id = get_participant_id(DEVELOPMENT_MODE, DEV_PARTICIPANT_ID)
    study_stage = get_study_stage(participant_id, DEVELOPMENT_MODE, DEV_STAGE)
    
    # Get session log history
    session_visits = get_session_log_history(participant_id, DEVELOPMENT_MODE, study_stage)
    visited_routes = [visit.get('route') for visit in session_visits if visit.get('route')]
    
    # Define the study flow for current stage
    if study_stage == 1:
        flow = ['home', 'background_questionnaire', 'tutorial', 'task', 'ux_questionnaire', 'goodbye']
        flow_name = "Stage 1 Flow"
    else:
        flow = ['welcome_back', 'task', 'ux_questionnaire', 'goodbye']
        flow_name = "Stage 2 Flow"
    
    # Find the furthest step completed
    furthest_step_index = -1
    for i, step in enumerate(flow):
        if step in visited_routes:
            furthest_step_index = i
    
    current_step = flow[furthest_step_index] if furthest_step_index >= 0 else "None"
    next_step = flow[furthest_step_index + 1] if furthest_step_index >= 0 and furthest_step_index + 1 < len(flow) else "None"
    
    # Test routing for each possible current route
    routing_tests = {}
    test_routes = ['home', 'background_questionnaire', 'tutorial', 'task', 'ux_questionnaire', 'goodbye', 'welcome_back']
    
    for route in test_routes:
        suggested_route = determine_correct_route(participant_id, DEVELOPMENT_MODE, study_stage, route)
        routing_tests[route] = suggested_route
    
    # Create flow visualization
    flow_html = []
    for i, step in enumerate(flow):
        if i <= furthest_step_index:
            # Completed step
            flow_html.append(f'<span style="color: green; font-weight: bold;">{step}</span>')
        elif i == furthest_step_index + 1:
            # Next step
            flow_html.append(f'<span style="color: blue; font-weight: bold;">{step}</span>')
        else:
            # Future step
            flow_html.append(f'<span style="color: gray;">{step}</span>')
    
    flow_display = ' → '.join(flow_html)
    
    return f"""
    <h2>🔄 Simplified Routing Debug</h2>
    <p><strong>Participant:</strong> {participant_id}</p>
    <p><strong>Stage:</strong> {study_stage}</p>
    
    <h3>{flow_name}</h3>
    <p>{flow_display}</p>
    <p><strong>Legend:</strong> <span style="color: green;">Completed</span> | <span style="color: blue;">Next Available</span> | <span style="color: gray;">Future</span></p>
    
    <p><strong>Current Step:</strong> {current_step}</p>
    <p><strong>Next Step:</strong> {next_step}</p>
    <p><strong>Visited Routes:</strong> {' → '.join(visited_routes) if visited_routes else 'None'}</p>
    
    <h3>Route Testing</h3>
    <p>Shows where each route would redirect to:</p>
    <ul>
    {''.join([f'<li><strong>{route}</strong> → {suggested if suggested else "no redirect"}</li>' for route, suggested in routing_tests.items()])}
    </ul>
    
    <h3>Session History</h3>
    <pre>{json.dumps(session_visits, indent=2, ensure_ascii=False)}</pre>
    
    <hr>
    <a href="/debug-session">← Back to Debug Session</a>
    """

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
    
    # Get participant ID for startup information (repository cloned when session starts)
    participant_id = get_participant_id(DEVELOPMENT_MODE, DEV_PARTICIPANT_ID)
    study_stage = get_study_stage(participant_id, DEVELOPMENT_MODE, DEV_STAGE)
    print(f"Starting server for participant: {participant_id}")
    print(f"Study stage: {study_stage} ({'Stage 1 - First time' if study_stage == 1 else 'Stage 2 - Returning participant'})")
    print("Note: Repository will be cloned when user clicks 'Start Session'")
    
    # Test GitHub connectivity
    print("\nTesting GitHub connectivity...")
    print(f"Async GitHub mode: {'Enabled' if ASYNC_GITHUB_MODE else 'Disabled'}")
    if GITHUB_TOKEN:
        print(f"GitHub authentication enabled for organization: {GITHUB_ORG}")
    else:
        print("No GitHub token provided - using public access only")
    
    if ASYNC_GITHUB_MODE:
        # Test connectivity asynchronously
        test_github_connectivity_async(participant_id, GITHUB_TOKEN, GITHUB_ORG)
        print("GitHub connectivity test queued for background processing")
    else:
        # Test connectivity synchronously
        github_available = test_github_connectivity(participant_id, GITHUB_TOKEN, GITHUB_ORG)
        if not github_available:
            print("Warning: GitHub repository may not be accessible")
    
    # Repository will be cloned when user starts the session
    print("\nRepository will be cloned when user clicks 'Start Session'")
    
    # Start screen recording when server starts to capture the entire participant session
    print("\nStarting screen recording at server startup...")
    recording_started = start_session_recording(participant_id, study_stage, DEVELOPMENT_MODE)
    if recording_started:
        print(f"✅ Screen recording started for participant {participant_id}, stage {study_stage}")
    else:
        print(f"❌ Failed to start screen recording for participant {participant_id}, stage {study_stage}")
    
    # Set up graceful shutdown for async service and screen recording
    def cleanup_on_exit():
        # Stop any active screen recording
        if is_recording_active():
            print("Stopping active screen recording on app shutdown...")
            stop_session_recording()
        # Stop async GitHub service
        stop_async_github_service()
    
    import atexit
    atexit.register(cleanup_on_exit)
    print("Async GitHub service and screen recording shutdown handlers registered")

    app.run(debug=DEVELOPMENT_MODE, host='127.0.0.1', port=39765)