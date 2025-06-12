#!/usr/bin/env python3
"""
Test script to demonstrate the logging functionality.
This script tests the key logging functions without requiring a full Flask app run.
"""
import os
import sys
import tempfile
import shutil
from datetime import datetime

# Add the current directory to Python path so we can import helpers
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from helpers import (
    get_logs_directory_path, 
    ensure_logging_repository, 
    log_route_visit,
    should_log_route,
    mark_route_as_logged
)

def test_logging_functionality():
    """Test the logging functionality with a mock participant."""
    print("🧪 Testing Study Flow Logging System")
    print("=" * 50)
    
    # Test parameters
    participant_id = "test-participant-001"
    development_mode = True
    study_stage = 1
    
    # Mock session for testing
    mock_session = {}
    
    print(f"Testing with participant: {participant_id}")
    print(f"Development mode: {development_mode}")
    print(f"Study stage: {study_stage}")
    print()
    
    # Test 1: Check logs directory path
    print("📁 Test 1: Logs directory path")
    logs_path = get_logs_directory_path(participant_id, development_mode)
    print(f"Logs path: {logs_path}")
    print()
    
    # Test 2: Ensure logging repository
    print("🔧 Test 2: Setting up logging repository")
    setup_success = ensure_logging_repository(participant_id, development_mode, None, None)
    print(f"Repository setup success: {setup_success}")
    
    if os.path.exists(logs_path):
        print(f"✅ Logs directory created at: {logs_path}")
        if os.path.exists(os.path.join(logs_path, '.git')):
            print("✅ Git repository initialized")
        if os.path.exists(os.path.join(logs_path, 'README.md')):
            print("✅ README.md created")
    print()
    
    # Test 3: Test route logging logic
    print("🚦 Test 3: Route logging logic")
    
    # Test should_log_route function
    should_log_home = should_log_route(mock_session, 'home', study_stage)
    print(f"Should log 'home' route (first time): {should_log_home}")
    
    # Mark route as logged
    mark_route_as_logged(mock_session, 'home', study_stage)
    
    # Test again - should return False now
    should_log_home_again = should_log_route(mock_session, 'home', study_stage)
    print(f"Should log 'home' route (second time): {should_log_home_again}")
    print(f"Session state: {mock_session}")
    print()
    
    # Test 4: Actual route logging
    print("📝 Test 4: Logging route visits")
    
    # Test different route types
    test_routes = [
        ('home', {'first_visit': True}),
        ('tutorial', {'tutorial_accessed': True, 'coding_condition': 'ai-assisted'}),
        ('task', {'coding_session_start': True, 'current_task': 1}),
        ('task_completion_1', {'event_type': 'task_completion', 'task_id': 1}),
        ('ux_questionnaire', {'study_completion': True})
    ]
    
    for route_name, session_data in test_routes:
        print(f"Logging route: {route_name}")
        success = log_route_visit(
            participant_id=participant_id,
            route_name=route_name,
            development_mode=development_mode,
            study_stage=study_stage,
            session_data=session_data
        )
        print(f"  Success: {success}")
    print()
    
    # Test 5: Check log file contents
    print("📄 Test 5: Checking log file contents")
    log_file_path = os.path.join(logs_path, 'route_visits.json')
    if os.path.exists(log_file_path):
        print("✅ Log file exists")
        try:
            import json
            with open(log_file_path, 'r', encoding='utf-8') as f:
                log_data = json.load(f)
            
            print(f"Number of logged visits: {len(log_data.get('visits', []))}")
            print("\nLogged routes:")
            for visit in log_data.get('visits', []):
                timestamp = visit.get('timestamp', 'Unknown')
                route = visit.get('route', 'Unknown')
                stage = visit.get('study_stage', 'Unknown')
                print(f"  - {route} (stage {stage}) at {timestamp}")
        except Exception as e:
            print(f"❌ Error reading log file: {e}")
    else:
        print("❌ Log file not found")
    print()
    
    # Test 6: Test stage 2 logging
    print("🔄 Test 6: Testing stage 2 logging")
    study_stage_2 = 2
    
    # Reset session for stage 2
    mock_session_stage2 = {}
    
    # Test that we can log the same routes for stage 2
    should_log_welcome_back = should_log_route(mock_session_stage2, 'welcome_back', study_stage_2)
    print(f"Should log 'welcome_back' for stage 2: {should_log_welcome_back}")
    
    success = log_route_visit(
        participant_id=participant_id,
        route_name='welcome_back',
        development_mode=development_mode,
        study_stage=study_stage_2,
        session_data={'stage_transition': 'stage_1_to_stage_2', 'returning_participant': True}
    )
    print(f"Welcome back logging success: {success}")
    print()
    
    print("🎉 Logging functionality test completed!")
    print(f"📁 Logs are stored in: {logs_path}")
    print("You can examine the generated files and git history there.")

if __name__ == "__main__":
    test_logging_functionality()
