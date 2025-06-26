"""
Test suite for repository management flow throughout the study stages.

This test validates the complete repository management workflow:
- Stage 1: Repository cloning, tutorial branch setup, stage-1 branch creation, commits and pushes
- Stage 2: stage-2 branch creation from stage-1, commits and pushes
- Covers all major transition points and automatic commits/pushes
"""

import os
import pytest
import tempfile
import shutil
import subprocess
from unittest.mock import Mock, patch, MagicMock, call
from datetime import datetime

from models.repository_manager import RepositoryManager
from models.github_service import GitHubService
from models.study_logger import StudyLogger


class TestRepositoryFlow:
    """Test the complete repository management flow for both study stages."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test repositories."""
        temp_dir = tempfile.mkdtemp(prefix="coding_study_test_")
        yield temp_dir
        # Cleanup
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def mock_github_service(self):
        """Mock GitHub service for testing."""
        mock_service = Mock(spec=GitHubService)
        mock_service.get_authenticated_repo_url.return_value = "https://github.com/test-org/study-test-participant.git"
        mock_service.test_github_connectivity.return_value = True
        return mock_service
    
    @pytest.fixture
    def repository_manager(self, mock_github_service):
        """Create a RepositoryManager instance with mocked dependencies."""
        return RepositoryManager(mock_github_service)
    
    @pytest.fixture
    def git_repo(self, temp_dir):
        """Create a mock git repository for testing."""
        repo_path = os.path.join(temp_dir, "study-test-participant")
        os.makedirs(repo_path)
        
        # Initialize as git repo
        original_cwd = os.getcwd()
        try:
            os.chdir(repo_path)
            subprocess.run(['git', 'init'], capture_output=True, check=True)
            subprocess.run(['git', 'config', 'user.name', 'Test User'], capture_output=True, check=True)
            subprocess.run(['git', 'config', 'user.email', 'test@example.com'], capture_output=True, check=True)
            
            # Create initial commit on main branch
            with open('README.md', 'w') as f:
                f.write("# Test Repository\n")
            subprocess.run(['git', 'add', '.'], capture_output=True, check=True)
            subprocess.run(['git', 'commit', '-m', 'Initial commit'], capture_output=True, check=True)
            
            # Create and checkout tutorial branch
            subprocess.run(['git', 'checkout', '-b', 'tutorial'], capture_output=True, check=True)
            with open('tutorial.py', 'w') as f:
                f.write("# Tutorial code\nprint('Hello tutorial')\n")
            subprocess.run(['git', 'add', '.'], capture_output=True, check=True)
            subprocess.run(['git', 'commit', '-m', 'Tutorial setup'], capture_output=True, check=True)
            subprocess.run(['git', 'checkout', 'main'], capture_output=True, check=True)
            
        finally:
            os.chdir(original_cwd)
        
        return repo_path
    
    def test_stage_1_complete_flow(self, repository_manager, temp_dir, git_repo):
        """Test the complete Stage 1 flow: clone → tutorial → task setup → commits → pushes."""
        participant_id = "test-participant"
        github_token = "test-token"
        github_org = "test-org"
        
        # Mock the repository path to use our test repo
        with patch.object(repository_manager, 'get_repository_path', return_value=git_repo):
            # Mock subprocess calls for remote operations
            with patch('subprocess.run') as mock_run:
                # Configure subprocess mock responses
                def side_effect(*args, **kwargs):
                    command = args[0]
                    if command == ['git', 'fetch', 'origin']:
                        return Mock(returncode=0, stdout="", stderr="")
                    elif command == ['git', 'branch', '--show-current']:
                        return Mock(returncode=0, stdout="main\n", stderr="")
                    elif command == ['git', 'branch', '--list', 'tutorial']:
                        return Mock(returncode=0, stdout="  tutorial\n", stderr="")
                    elif command == ['git', 'branch', '--list', 'stage-1']:
                        return Mock(returncode=0, stdout="", stderr="")  # Branch doesn't exist initially
                    elif command == ['git', 'branch', '-r', '--list', 'origin/tutorial']:
                        return Mock(returncode=0, stdout="  origin/tutorial\n", stderr="")
                    elif command == ['git', 'branch', '-r', '--list', 'origin/main']:
                        return Mock(returncode=0, stdout="  origin/main\n", stderr="")
                    elif command == ['git', 'checkout', 'tutorial']:
                        return Mock(returncode=0, stdout="", stderr="")
                    elif command == ['git', 'checkout', '-b', 'stage-1', 'origin/main']:
                        return Mock(returncode=0, stdout="", stderr="")
                    elif command == ['git', 'status', '--porcelain']:
                        return Mock(returncode=0, stdout="M tutorial.py\n", stderr="")  # Simulate changes
                    elif command == ['git', 'add', '.']:
                        return Mock(returncode=0, stdout="", stderr="")
                    elif 'git' in command and 'commit' in command:
                        return Mock(returncode=0, stdout="", stderr="")
                    elif command == ['git', 'branch', '--format=%(refname:short)']:
                        return Mock(returncode=0, stdout="main\ntutorial\nstage-1\n", stderr="")
                    elif 'git' in command and 'push' in command:
                        return Mock(returncode=0, stdout="", stderr="")
                    elif command == ['git', 'remote', 'set-url', 'origin'] + [repository_manager.github_service.get_authenticated_repo_url.return_value]:
                        return Mock(returncode=0, stdout="", stderr="")
                    else:
                        # Default success for other git commands
                        return Mock(returncode=0, stdout="", stderr="")
                
                mock_run.side_effect = side_effect
                
                # Step 1: When user clicks start session - repository is cloned (already exists in our test)
                # This would typically be called from the background_questionnaire route
                clone_success = repository_manager.check_and_clone_repository(
                    participant_id, True, github_token, github_org
                )
                assert clone_success, "Repository clone/check should succeed"
                
                # Step 2: When user visits tutorial page first time - tutorial branch is checked out
                tutorial_success = repository_manager.setup_tutorial_branch(
                    participant_id, True, github_token, github_org
                )
                assert tutorial_success, "Tutorial branch setup should succeed"
                
                # Step 3: When user goes from tutorial to task - code is committed and pushed
                tutorial_push_success = repository_manager.push_tutorial_code(
                    participant_id, True, github_token, github_org
                )
                assert tutorial_push_success, "Tutorial code push should succeed"
                
                # Step 4: When user visits task page first time - stage-1 branch is created from main
                stage_setup_success = repository_manager.setup_repository_for_stage(
                    participant_id, 1, True, github_token, github_org
                )
                assert stage_setup_success, "Stage 1 repository setup should succeed"
                
                # Step 5: When user marks requirement as completed - code is committed and pushed
                requirement_commit_success = repository_manager.commit_and_backup_all(
                    participant_id, 1, "Completed requirement 1", True, github_token, github_org
                )
                assert requirement_commit_success, "Requirement completion commit should succeed"
                
                # Step 6: When timer ends - code is committed and pushed
                timer_commit_success = repository_manager.commit_and_backup_all(
                    participant_id, 1, "Timer expired - 40 minutes completed", True, github_token, github_org
                )
                assert timer_commit_success, "Timer expiration commit should succeed"
                
                # Step 7: When user goes to UX questionnaire - code is committed and pushed
                ux_commit_success = repository_manager.commit_and_backup_all(
                    participant_id, 1, "Session ended - proceeding to UX questionnaire", True, github_token, github_org
                )
                assert ux_commit_success, "UX questionnaire transition commit should succeed"
                
                # Verify that key git operations were called
                git_calls = [call for call in mock_run.call_args_list if call[0][0][0] == 'git']
                
                # Should have calls for: fetch, checkout tutorial, checkout stage-1, commits, pushes
                fetch_calls = [call for call in git_calls if 'fetch' in call[0][0]]
                checkout_calls = [call for call in git_calls if 'checkout' in call[0][0]]
                commit_calls = [call for call in git_calls if 'commit' in call[0][0]]
                push_calls = [call for call in git_calls if 'push' in call[0][0]]
                
                assert len(fetch_calls) > 0, "Should have fetch calls"
                assert len(checkout_calls) >= 2, "Should have checkout calls for tutorial and stage-1"
                assert len(commit_calls) >= 4, "Should have multiple commit calls"
                assert len(push_calls) >= 3, "Should have multiple push calls"
    
    def test_stage_2_complete_flow(self, repository_manager, temp_dir, git_repo):
        """Test the complete Stage 2 flow: stage-2 branch from stage-1 → commits → pushes."""
        participant_id = "test-participant"
        github_token = "test-token"
        github_org = "test-org"
        
        # Mock the repository path to use our test repo
        with patch.object(repository_manager, 'get_repository_path', return_value=git_repo):
            # Setup stage-1 branch first (simulate it exists from Stage 1)
            original_cwd = os.getcwd()
            try:
                os.chdir(git_repo)
                subprocess.run(['git', 'checkout', '-b', 'stage-1'], capture_output=True, check=True)
                with open('stage1_work.py', 'w') as f:
                    f.write("# Stage 1 work\nprint('Stage 1 completed')\n")
                subprocess.run(['git', 'add', '.'], capture_output=True, check=True)
                subprocess.run(['git', 'commit', '-m', 'Stage 1 work'], capture_output=True, check=True)
            finally:
                os.chdir(original_cwd)
            
            # Mock subprocess calls for Stage 2 operations
            with patch('subprocess.run') as mock_run:
                def side_effect(*args, **kwargs):
                    command = args[0]
                    if command == ['git', 'fetch', 'origin']:
                        return Mock(returncode=0, stdout="", stderr="")
                    elif command == ['git', 'branch', '--show-current']:
                        return Mock(returncode=0, stdout="stage-1\n", stderr="")
                    elif command == ['git', 'branch', '--list', 'stage-2']:
                        return Mock(returncode=0, stdout="", stderr="")  # Branch doesn't exist initially
                    elif command == ['git', 'branch', '--list', 'stage-1']:
                        return Mock(returncode=0, stdout="  stage-1\n", stderr="")  # Exists from Stage 1
                    elif command == ['git', 'checkout', '-b', 'stage-2', 'stage-1']:
                        return Mock(returncode=0, stdout="", stderr="")
                    elif command == ['git', 'status', '--porcelain']:
                        return Mock(returncode=0, stdout="M stage1_work.py\n", stderr="")  # Simulate changes
                    elif command == ['git', 'add', '.']:
                        return Mock(returncode=0, stdout="", stderr="")
                    elif 'git' in command and 'commit' in command:
                        return Mock(returncode=0, stdout="", stderr="")
                    elif command == ['git', 'branch', '--format=%(refname:short)']:
                        return Mock(returncode=0, stdout="main\ntutorial\nstage-1\nstage-2\n", stderr="")
                    elif 'git' in command and 'push' in command:
                        return Mock(returncode=0, stdout="", stderr="")
                    elif command == ['git', 'remote', 'set-url', 'origin'] + [repository_manager.github_service.get_authenticated_repo_url.return_value]:
                        return Mock(returncode=0, stdout="", stderr="")
                    else:
                        return Mock(returncode=0, stdout="", stderr="")
                
                mock_run.side_effect = side_effect
                
                # Stage 2 Flow
                # Step 1: When user visits task page first time in Stage 2 - stage-2 branch created from stage-1
                stage2_setup_success = repository_manager.setup_repository_for_stage(
                    participant_id, 2, True, github_token, github_org
                )
                assert stage2_setup_success, "Stage 2 repository setup should succeed"
                
                # Step 2: When user marks requirement as completed - code is committed and pushed
                requirement_commit_success = repository_manager.commit_and_backup_all(
                    participant_id, 2, "Completed requirement 1", True, github_token, github_org
                )
                assert requirement_commit_success, "Stage 2 requirement completion commit should succeed"
                
                # Step 3: When timer ends - code is committed and pushed
                timer_commit_success = repository_manager.commit_and_backup_all(
                    participant_id, 2, "Timer expired - 40 minutes completed", True, github_token, github_org
                )
                assert timer_commit_success, "Stage 2 timer expiration commit should succeed"
                
                # Step 4: When user goes to UX questionnaire - code is committed and pushed
                ux_commit_success = repository_manager.commit_and_backup_all(
                    participant_id, 2, "Session ended - proceeding to UX questionnaire", True, github_token, github_org
                )
                assert ux_commit_success, "Stage 2 UX questionnaire transition commit should succeed"
                
                # Verify that stage-2 branch creation was called correctly
                git_calls = [call for call in mock_run.call_args_list if call[0][0][0] == 'git']
                
                # Should have call to create stage-2 from stage-1
                checkout_calls = [call for call in git_calls if 'checkout' in call[0][0] and '-b' in call[0][0]]
                stage2_checkout = [call for call in checkout_calls if 'stage-2' in call[0][0] and 'stage-1' in call[0][0]]
                
                assert len(stage2_checkout) > 0, "Should create stage-2 branch from stage-1"
                
                # Should have multiple commits and pushes
                commit_calls = [call for call in git_calls if 'commit' in call[0][0]]
                push_calls = [call for call in git_calls if 'push' in call[0][0]]
                
                assert len(commit_calls) >= 3, "Should have multiple commit calls for Stage 2"
                assert len(push_calls) >= 3, "Should have multiple push calls for Stage 2"
    
    def test_branch_creation_logic(self, repository_manager, git_repo):
        """Test the specific branch creation logic for different stages."""
        with patch.object(repository_manager, 'get_repository_path', return_value=git_repo):
            with patch('subprocess.run') as mock_run:
                # Mock responses for stage-1 branch creation
                def side_effect_stage1(*args, **kwargs):
                    command = args[0]
                    if command == ['git', 'fetch', 'origin']:
                        return Mock(returncode=0, stdout="", stderr="")
                    elif command == ['git', 'branch', '--show-current']:
                        return Mock(returncode=0, stdout="main\n", stderr="")
                    elif command == ['git', 'branch', '--list', 'stage-1']:
                        return Mock(returncode=0, stdout="", stderr="")  # Doesn't exist
                    elif command == ['git', 'branch', '-r', '--list', 'origin/main']:
                        return Mock(returncode=0, stdout="  origin/main\n", stderr="")
                    elif command == ['git', 'checkout', '-b', 'stage-1', 'origin/main']:
                        return Mock(returncode=0, stdout="", stderr="")
                    else:
                        return Mock(returncode=0, stdout="", stderr="")
                
                mock_run.side_effect = side_effect_stage1
                
                # Test stage-1 branch creation from origin/main
                stage1_success = repository_manager.ensure_stage_branch(git_repo, 1)
                assert stage1_success, "Stage-1 branch should be created from origin/main"
                
                # Verify correct git commands were called
                checkout_calls = [call for call in mock_run.call_args_list 
                                if 'git' in call[0][0] and 'checkout' in call[0][0] and '-b' in call[0][0]]
                
                assert any('stage-1' in str(call) and 'origin/main' in str(call) for call in checkout_calls), \
                    "Should create stage-1 from origin/main"
                
                # Reset mock for stage-2 test
                mock_run.reset_mock()
                
                # Mock responses for stage-2 branch creation
                def side_effect_stage2(*args, **kwargs):
                    command = args[0]
                    if command == ['git', 'fetch', 'origin']:
                        return Mock(returncode=0, stdout="", stderr="")
                    elif command == ['git', 'branch', '--show-current']:
                        return Mock(returncode=0, stdout="stage-1\n", stderr="")
                    elif command == ['git', 'branch', '--list', 'stage-2']:
                        return Mock(returncode=0, stdout="", stderr="")  # Doesn't exist
                    elif command == ['git', 'branch', '--list', 'stage-1']:
                        return Mock(returncode=0, stdout="  stage-1\n", stderr="")  # Exists
                    elif command == ['git', 'checkout', '-b', 'stage-2', 'stage-1']:
                        return Mock(returncode=0, stdout="", stderr="")
                    else:
                        return Mock(returncode=0, stdout="", stderr="")
                
                mock_run.side_effect = side_effect_stage2
                
                # Test stage-2 branch creation from local stage-1
                stage2_success = repository_manager.ensure_stage_branch(git_repo, 2)
                assert stage2_success, "Stage-2 branch should be created from local stage-1"
                
                # Verify correct git commands were called
                checkout_calls = [call for call in mock_run.call_args_list 
                                if 'git' in call[0][0] and 'checkout' in call[0][0] and '-b' in call[0][0]]
                
                assert any('stage-2' in str(call) and 'stage-1' in str(call) for call in checkout_calls), \
                    "Should create stage-2 from stage-1"
    
    def test_commit_and_backup_workflow(self, repository_manager, git_repo):
        """Test the commit and backup workflow that happens at various transition points."""
        participant_id = "test-participant"
        github_token = "test-token"
        github_org = "test-org"
        
        with patch.object(repository_manager, 'get_repository_path', return_value=git_repo):
            with patch('subprocess.run') as mock_run:
                def side_effect(*args, **kwargs):
                    command = args[0]
                    if command == ['git', 'status', '--porcelain']:
                        return Mock(returncode=0, stdout="M test_file.py\nA new_file.py\n", stderr="")
                    elif command == ['git', 'branch', '--show-current']:
                        return Mock(returncode=0, stdout="stage-1\n", stderr="")
                    elif command == ['git', 'add', '.']:
                        return Mock(returncode=0, stdout="", stderr="")
                    elif 'git' in command and 'commit' in command:
                        return Mock(returncode=0, stdout="", stderr="")
                    elif command == ['git', 'branch', '--format=%(refname:short)']:
                        return Mock(returncode=0, stdout="main\ntutorial\nstage-1\n", stderr="")
                    elif 'git' in command and 'push' in command:
                        return Mock(returncode=0, stdout="", stderr="")
                    elif command == ['git', 'remote', 'set-url', 'origin'] + [repository_manager.github_service.get_authenticated_repo_url.return_value]:
                        return Mock(returncode=0, stdout="", stderr="")
                    else:
                        return Mock(returncode=0, stdout="", stderr="")
                
                mock_run.side_effect = side_effect
                
                # Test commit and backup workflow
                success = repository_manager.commit_and_backup_all(
                    participant_id, 1, "Test commit message", True, github_token, github_org
                )
                
                assert success, "Commit and backup workflow should succeed"
                
                # Verify the sequence of operations
                git_calls = [call[0][0] for call in mock_run.call_args_list if call[0][0][0] == 'git']
                
                # Should check status first
                assert ['git', 'status', '--porcelain'] in git_calls, "Should check git status"
                
                # Should add changes
                assert ['git', 'add', '.'] in git_calls, "Should add changes"
                
                # Should have commit command
                commit_calls = [call for call in git_calls if 'commit' in call]
                assert len(commit_calls) > 0, "Should have commit calls"
                
                # Should have push commands for backup
                push_calls = [call for call in git_calls if 'push' in call]
                assert len(push_calls) > 0, "Should have push calls for backup"
    
    def test_tutorial_workflow(self, repository_manager, git_repo):
        """Test the tutorial-specific workflow including branch setup and code pushing."""
        participant_id = "test-participant"
        github_token = "test-token"
        github_org = "test-org"
        
        with patch.object(repository_manager, 'get_repository_path', return_value=git_repo):
            with patch('subprocess.run') as mock_run:
                def side_effect(*args, **kwargs):
                    command = args[0]
                    if command == ['git', 'fetch', 'origin']:
                        return Mock(returncode=0, stdout="", stderr="")
                    elif command == ['git', 'branch', '--show-current']:
                        return Mock(returncode=0, stdout="main\n", stderr="")
                    elif command == ['git', 'branch', '--list', 'tutorial']:
                        return Mock(returncode=0, stdout="  tutorial\n", stderr="")
                    elif command == ['git', 'checkout', 'tutorial']:
                        return Mock(returncode=0, stdout="", stderr="")
                    elif command == ['git', 'branch', '-r', '--list', 'origin/tutorial']:
                        return Mock(returncode=0, stdout="  origin/tutorial\n", stderr="")
                    elif command == ['git', 'pull', 'origin', 'tutorial']:
                        return Mock(returncode=0, stdout="", stderr="")
                    elif command == ['git', 'status', '--porcelain']:
                        return Mock(returncode=0, stdout="M tutorial.py\n", stderr="")
                    elif command == ['git', 'add', '.']:
                        return Mock(returncode=0, stdout="", stderr="")
                    elif 'git' in command and 'commit' in command:
                        return Mock(returncode=0, stdout="", stderr="")
                    elif command == ['git', 'branch', '--format=%(refname:short)']:
                        return Mock(returncode=0, stdout="main\ntutorial\n", stderr="")
                    elif 'git' in command and 'push' in command:
                        return Mock(returncode=0, stdout="", stderr="")
                    elif command == ['git', 'remote', 'set-url', 'origin'] + [repository_manager.github_service.get_authenticated_repo_url.return_value]:
                        return Mock(returncode=0, stdout="", stderr="")
                    else:
                        return Mock(returncode=0, stdout="", stderr="")
                
                mock_run.side_effect = side_effect
                
                # Test tutorial setup
                tutorial_setup_success = repository_manager.setup_tutorial_branch(
                    participant_id, True, github_token, github_org
                )
                assert tutorial_setup_success, "Tutorial branch setup should succeed"
                
                # Test tutorial code push (when transitioning from tutorial to task)
                tutorial_push_success = repository_manager.push_tutorial_code(
                    participant_id, True, github_token, github_org
                )
                assert tutorial_push_success, "Tutorial code push should succeed"
                
                # Verify tutorial branch operations
                git_calls = [call[0][0] for call in mock_run.call_args_list if call[0][0][0] == 'git']
                
                # Should checkout tutorial branch
                assert ['git', 'checkout', 'tutorial'] in git_calls, "Should checkout tutorial branch"
                
                # Should sync with remote tutorial
                assert ['git', 'pull', 'origin', 'tutorial'] in git_calls, "Should pull tutorial updates"
    
    def test_error_handling(self, repository_manager, git_repo):
        """Test error handling in repository operations."""
        participant_id = "test-participant"
        github_token = "test-token"
        github_org = "test-org"
        
        with patch.object(repository_manager, 'get_repository_path', return_value=git_repo):
            # Test failure in git operations
            with patch('subprocess.run') as mock_run:
                # Simulate git command failure
                mock_run.return_value = Mock(returncode=1, stdout="", stderr="Git command failed")
                
                # Test that failures are handled gracefully
                success = repository_manager.ensure_stage_branch(git_repo, 1)
                assert not success, "Should return False when git operations fail"
                
                success = repository_manager.commit_and_backup_all(
                    participant_id, 1, "Test commit", True, github_token, github_org
                )
                assert not success, "Should return False when commit operations fail"
    
    @pytest.mark.integration
    def test_integration_with_services_layer(self):
        """Test integration with the services layer that the Flask app uses."""
        # This test would import and test the services.py functions
        # that orchestrate the repository management
        
        from services import (
            check_and_clone_repository, setup_repository_for_stage,
            commit_code_changes, setup_tutorial_branch, push_tutorial_code
        )
        
        participant_id = "test-integration"
        development_mode = True
        github_token = "test-token"
        github_org = "test-org"
        
        # Mock the underlying components
        with patch('services._repository_manager') as mock_repo_manager:
            mock_repo_manager.check_and_clone_repository.return_value = True
            mock_repo_manager.setup_repository_for_stage.return_value = True
            mock_repo_manager.commit_and_backup_all.return_value = True
            mock_repo_manager.setup_tutorial_branch.return_value = True
            mock_repo_manager.push_tutorial_code.return_value = True
            
            # Test the services layer functions
            assert check_and_clone_repository(participant_id, development_mode, github_token, github_org)
            assert setup_repository_for_stage(participant_id, 1, development_mode, github_token, github_org)
            assert setup_tutorial_branch(participant_id, development_mode, github_token, github_org)
            assert push_tutorial_code(participant_id, development_mode, github_token, github_org, async_mode=False)
            
            # For commit_code_changes, we need to test both async and sync modes
            with patch('services._async_github_service') as mock_async_service:
                mock_async_service.queue_commit_code_changes.return_value = True
                
                # Test async mode
                assert commit_code_changes(participant_id, 1, "Test commit", development_mode, 
                                         github_token, github_org, async_mode=True)
                
                # Test sync mode  
                assert commit_code_changes(participant_id, 1, "Test commit", development_mode,
                                         github_token, github_org, async_mode=False)


if __name__ == '__main__':
    pytest.main([__file__])
