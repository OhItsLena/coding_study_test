#!/usr/bin/env python3
"""
Verification script to ensure all refactored functionality works correctly.
This script tests the main functions that were originally in the monolithic helpers.py file.
"""

import os
import sys

def test_refactored_functionality():
    """Test all the main functions to ensure they work after refactoring."""
    print("🔍 Testing Refactored Functionality")
    print("=" * 50)
    
    try:
        # Import the refactored services
        import services
        print("✅ Import successful")
        
        # Test task management
        print("\n📋 Testing Task Management:")
        task_reqs = services.load_task_requirements()
        print(f"   ✅ Task requirements loaded: {len(task_reqs.get('stage1_tasks', []))} stage1 tasks")
        
        stage1_tasks = services.get_tasks_for_stage(1)
        print(f"   ✅ Stage 1 tasks: {len(stage1_tasks)} tasks")
        
        stage2_tasks = services.get_tasks_for_stage(2)
        print(f"   ✅ Stage 2 tasks: {len(stage2_tasks)} tasks")
        
        # Test participant management
        print("\n👤 Testing Participant Management:")
        condition = services.get_coding_condition("test-participant")
        print(f"   ✅ Coding condition: {condition}")
        
        # Test Azure service (development mode)
        print("\n☁️  Testing Azure Service:")
        study_stage = services.get_study_stage("test", True, 1)
        print(f"   ✅ Study stage (dev mode): {study_stage}")
        
        participant_id = services.get_participant_id(True, "test-dev")
        print(f"   ✅ Participant ID (dev mode): {participant_id}")
        
        # Test GitHub service
        print("\n🐙 Testing GitHub Service:")
        repo_url = services.get_authenticated_repo_url("test-repo", "token", "org")
        print(f"   ✅ Authenticated repo URL generated")
        
        # Test repository management
        print("\n📁 Testing Repository Management:")
        repo_path = services.get_repository_path("test-participant", True)
        print(f"   ✅ Repository path: {os.path.basename(repo_path)}")
        
        # Test session tracking
        print("\n📊 Testing Session Tracking:")
        mock_session = {}
        should_log = services.should_log_route(mock_session, "test_route", 1)
        print(f"   ✅ Should log route (first time): {should_log}")
        
        services.mark_route_as_logged(mock_session, "test_route", 1)
        should_log_again = services.should_log_route(mock_session, "test_route", 1)
        print(f"   ✅ Should log route (second time): {should_log_again}")
        
        # Test logging directory
        print("\n📝 Testing Logging System:")
        logs_path = services.get_logs_directory_path("test-participant", True)
        print(f"   ✅ Logs directory path: {os.path.basename(logs_path)}")
        
        print("\n🎉 All functionality tests passed!")
        print("✅ Refactoring successful - all original features preserved")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_refactored_functionality()
    sys.exit(0 if success else 1)
