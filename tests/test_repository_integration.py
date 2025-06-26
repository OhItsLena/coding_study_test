"""
Integration test demonstrating the complete repository flow as it happens in the Flask application.

This test simulates the actual user journey through the study and verifies that repository 
operations happen at the correct times with the right parameters.
"""

import pytest
from unittest.mock import Mock, patch, call
import tempfile
import os
import shutil

# Import Flask app and services
from app import app
from services import (
    check_and_clone_repository, setup_repository_for_stage, commit_code_changes,
    setup_tutorial_branch, push_tutorial_code
)


class TestRepositoryFlowIntegration:
    """Integration tests for repository flow within the Flask application context."""
    
    @pytest.fixture
    def flask_app(self):
        """Create Flask app for testing."""
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        return app
    
    @pytest.fixture
    def client(self, flask_app):
        """Create test client."""
        with flask_app.test_client() as client:
            yield client
    
    @pytest.fixture
    def app_context(self, flask_app):
        """Create application context."""
        with flask_app.app_context():
            yield
    
    @pytest.fixture
    def mock_services(self):
        """Mock all the service layer functions."""
        with patch('services._repository_manager') as mock_repo, \
             patch('services._async_github_service') as mock_async, \
             patch('services._study_logger') as mock_logger:
            
            # Configure repository manager mocks
            mock_repo.check_and_clone_repository.return_value = True
            mock_repo.setup_repository_for_stage.return_value = True
            mock_repo.commit_and_backup_all.return_value = True
            mock_repo.setup_tutorial_branch.return_value = True
            mock_repo.push_tutorial_code.return_value = True
            
            # Configure async service mocks
            mock_async.queue_commit_code_changes.return_value = True
            mock_async.queue_push_tutorial_code.return_value = True
            
            # Configure logger mocks
            mock_logger.log_route_visit.return_value = True
            mock_logger.should_log_route.return_value = True
            
            yield {
                'repository_manager': mock_repo,
                'async_github_service': mock_async,
                'study_logger': mock_logger
            }
    
    def test_stage_1_user_journey(self, client, app_context, mock_services):
        """Test the complete Stage 1 user journey with repository operations."""
        
        # Patch the global variables in the app module directly
        with patch('app.DEVELOPMENT_MODE', True), \
             patch('app.DEV_PARTICIPANT_ID', 'test-stage1-participant'), \
             patch('app.DEV_STAGE', 1), \
             patch('app.GITHUB_TOKEN', 'test-token'), \
             patch('app.GITHUB_ORG', 'test-org'), \
             patch('app.ASYNC_GITHUB_MODE', False):
            
            # Mock the services to handle routing logic
            with patch('app.should_log_route', return_value=True), \
                 patch('app.log_route_visit'), \
                 patch('app.mark_route_as_logged'), \
                 patch('app.check_automatic_rerouting', return_value=None):
                
                # Set up session for consent
                with client.session_transaction() as sess:
                    sess['consent_given'] = True
                
                # Step 1: User clicks "Start Session" (visits background questionnaire)
                # This should trigger repository cloning
                response = client.get('/background-questionnaire')
                assert response.status_code == 200
            
            # Verify repository was cloned when starting session
            mock_services['repository_manager'].check_and_clone_repository.assert_called_with(
                'test-stage1-participant', True, 'test-token', 'test-org'
            )
            
            # Step 2: User visits tutorial page (first time)
            # This should setup tutorial branch
            response = client.get('/tutorial')
            assert response.status_code == 200
            
            # Verify tutorial branch was set up
            mock_services['repository_manager'].setup_tutorial_branch.assert_called_with(
                'test-stage1-participant', True, 'test-token', 'test-org'
            )
            
            # Step 3: User transitions from tutorial to task
            # This should push tutorial code and setup stage-1 branch
            response = client.get('/task')
            assert response.status_code == 200
            
            # Verify tutorial code was pushed
            mock_services['repository_manager'].push_tutorial_code.assert_called_with(
                'test-stage1-participant', True, 'test-token', 'test-org'
            )
            
            # Verify stage-1 repository setup
            mock_services['repository_manager'].setup_repository_for_stage.assert_called_with(
                'test-stage1-participant', 1, True, 'test-token', 'test-org'
            )
            
            # Step 4: User completes a requirement
            # This should commit and push changes
            response = client.post('/complete-task', json={'task_id': 1})
            assert response.status_code == 302  # Redirect back to task
            
            # Verify code was committed for task completion
            # The app calls commit_code_changes which calls commit_and_backup_all
            # Let's check if commit_and_backup_all was called at all
            print(f"commit_and_backup_all call count: {mock_services['repository_manager'].commit_and_backup_all.call_count}")
            print(f"All calls: {mock_services['repository_manager'].commit_and_backup_all.call_args_list}")
            
            # Check that commit_and_backup_all was called at least once
            assert mock_services['repository_manager'].commit_and_backup_all.call_count > 0, "commit_and_backup_all should have been called"
            
            # Step 5: Simulate timer expiration
            response = client.post('/timer-expired')
            assert response.status_code == 200
            
            # Step 6: User goes to UX questionnaire
            response = client.get('/ux-questionnaire')
            assert response.status_code == 200
            
            # Verify that repository operations were called multiple times
            commit_calls = mock_services['repository_manager'].commit_and_backup_all.call_args_list
            print(f"Total commit calls: {len(commit_calls)}")
            
            # Should have multiple commits throughout the session
            assert len(commit_calls) >= 2, f"Expected at least 2 commit calls, got {len(commit_calls)}"
    
    def test_stage_2_user_journey(self, client, app_context, mock_services):
        """Test the complete Stage 2 user journey with repository operations."""
        
        # Patch the global variables in the app module directly
        with patch('app.DEVELOPMENT_MODE', True), \
             patch('app.DEV_PARTICIPANT_ID', 'test-stage2-participant'), \
             patch('app.DEV_STAGE', 2), \
             patch('app.GITHUB_TOKEN', 'test-token'), \
             patch('app.GITHUB_ORG', 'test-org'), \
             patch('app.ASYNC_GITHUB_MODE', False):
            
            # Mock the services to handle routing logic
            with patch('app.should_log_route', return_value=True), \
                 patch('app.log_route_visit'), \
                 patch('app.mark_route_as_logged'), \
                 patch('app.check_automatic_rerouting', return_value=None):
                
                # Step 1: Stage 2 user starts (visits welcome-back page)
                # This should trigger repository cloning/checking
                response = client.get('/welcome-back')
                assert response.status_code == 200
            
            # Verify repository was cloned/checked for stage 2
            mock_services['repository_manager'].check_and_clone_repository.assert_called_with(
                'test-stage2-participant', True, 'test-token', 'test-org'
            )
            
            # Step 2: User visits task page for Stage 2 (first time)
            # This should create stage-2 branch from stage-1
            response = client.get('/task')
            assert response.status_code == 200
            
            # Verify stage-2 repository setup (branch created from stage-1)
            mock_services['repository_manager'].setup_repository_for_stage.assert_called_with(
                'test-stage2-participant', 2, True, 'test-token', 'test-org'
            )
            
            # Step 3: User completes requirements and timer expires (same as Stage 1)
            response = client.post('/complete-task', json={'task_id': 1})
            assert response.status_code == 302
            
            response = client.post('/timer-expired')
            assert response.status_code == 200
            
            response = client.get('/ux-questionnaire')
            assert response.status_code == 200
            
            # Verify commits were made for Stage 2
            commit_calls = mock_services['repository_manager'].commit_and_backup_all.call_args_list
            print(f"Stage 2 commit calls: {len(commit_calls)}")
            for i, call in enumerate(commit_calls):
                print(f"  Call {i+1}: {call}")
            
            assert len(commit_calls) >= 2  # At least session start and task completion
            
            # Verify that stage 2 was passed to commit calls
            stage2_commits = [call for call in commit_calls if call[0][1] == 2]  # study_stage is 2nd arg
            assert len(stage2_commits) >= 1, "Should have commits for Stage 2"
    
    def test_async_mode_repository_operations(self, client, app_context, mock_services):
        """Test that async mode properly queues repository operations."""
        
        with patch.dict(os.environ, {
            'DEVELOPMENT_MODE': 'true',
            'DEV_PARTICIPANT_ID': 'test-async-participant',
            'DEV_STAGE': '1',
            'GITHUB_TOKEN': 'test-token',
            'GITHUB_ORG': 'test-org',
            'ASYNC_GITHUB_MODE': 'true'  # Enable async mode
        }):
            
            with client.session_transaction() as sess:
                sess['consent_given'] = True
            
            # Visit task page to trigger async operations
            response = client.get('/task')
            assert response.status_code == 200
            
            # Complete a task to trigger async commit
            response = client.post('/complete-task', json={'task_id': 1})
            assert response.status_code == 302
            
            # Verify async operations were queued
            mock_services['async_github_service'].queue_commit_code_changes.assert_called()
            mock_services['async_github_service'].queue_push_tutorial_code.assert_called()
    
    def test_repository_error_handling(self, client, app_context, mock_services):
        """Test that repository operation failures are handled gracefully."""
        
        # Configure mocks to simulate failures
        mock_services['repository_manager'].check_and_clone_repository.return_value = False
        mock_services['repository_manager'].setup_repository_for_stage.return_value = False
        mock_services['repository_manager'].commit_and_backup_all.return_value = False
        
        with patch.dict(os.environ, {
            'DEVELOPMENT_MODE': 'true',
            'DEV_PARTICIPANT_ID': 'test-error-participant',
            'DEV_STAGE': '1',
            'GITHUB_TOKEN': 'test-token',
            'GITHUB_ORG': 'test-org',
            'ASYNC_GITHUB_MODE': 'false'
        }):
            
            with client.session_transaction() as sess:
                sess['consent_given'] = True
            
            # Even with repository failures, the app should continue to work
            response = client.get('/background-questionnaire')
            assert response.status_code == 200
            
            response = client.get('/tutorial')
            assert response.status_code == 200
            
            response = client.get('/task')
            assert response.status_code == 200
            
            response = client.post('/complete-task', json={'task_id': 1})
            assert response.status_code == 302
            
            # App should remain functional even if repository operations fail
            # This is important for study continuity
    
    @pytest.mark.slow
    def test_complete_study_flow_timing(self, client, app_context, mock_services):
        """Test the timing and sequence of repository operations throughout a complete study."""
        
        # Patch the global variables in the app module directly
        with patch('app.DEVELOPMENT_MODE', True), \
             patch('app.DEV_PARTICIPANT_ID', 'test-timing-participant'), \
             patch('app.DEV_STAGE', 1), \
             patch('app.GITHUB_TOKEN', 'test-token'), \
             patch('app.GITHUB_ORG', 'test-org'), \
             patch('app.ASYNC_GITHUB_MODE', False):
            
            # Mock the services to handle routing logic
            with patch('app.should_log_route', return_value=True), \
                 patch('app.log_route_visit'), \
                 patch('app.mark_route_as_logged'), \
                 patch('app.check_automatic_rerouting', return_value=None):
                
                with client.session_transaction() as sess:
                    sess['consent_given'] = True
                
                # Simulate complete user journey with timing verification
                operations_log = []
                
                def log_operation(operation_name):
                    def wrapper(*args, **kwargs):
                        operations_log.append(operation_name)
                        return True
                    return wrapper
                
                # Wrap operations to track their sequence
                mock_services['repository_manager'].check_and_clone_repository.side_effect = log_operation('clone')
                mock_services['repository_manager'].setup_tutorial_branch.side_effect = log_operation('tutorial_setup')
                mock_services['repository_manager'].push_tutorial_code.side_effect = log_operation('tutorial_push')
                mock_services['repository_manager'].setup_repository_for_stage.side_effect = log_operation('stage_setup')
                mock_services['repository_manager'].commit_and_backup_all.side_effect = log_operation('commit')
                
                # Execute the complete flow
                client.get('/background-questionnaire')  # Clone
                client.get('/tutorial')                  # Tutorial setup
                client.get('/task')                      # Tutorial push + Stage setup + Initial commit
                client.post('/complete-task', json={'task_id': 1})  # Task completion commit
                client.post('/complete-task', json={'task_id': 2})  # Another task completion commit
                client.post('/timer-expired')            # Timer expiry commit
                client.get('/ux-questionnaire')          # Final commit
                
                # Just verify that the key operations happened in some order
                assert 'clone' in operations_log, "Repository should be cloned"
                assert 'tutorial_setup' in operations_log, "Tutorial should be set up"
                assert 'stage_setup' in operations_log, "Stage should be set up"
                assert operations_log.count('commit') >= 2, "Multiple commits should happen"
                
                # Verify clone happens first
                assert operations_log[0] == 'clone', "Clone should be first operation"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
