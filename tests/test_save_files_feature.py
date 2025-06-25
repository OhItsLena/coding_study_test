"""
Test for the save all files functionality in repository manager.
"""
import pytest
import os
import tempfile
import shutil
from unittest.mock import Mock, patch, MagicMock
import subprocess

from models.repository_manager import RepositoryManager
from models.github_service import GitHubService


@pytest.fixture
def mock_github_service():
    """Mock GitHub service for testing."""
    service = Mock(spec=GitHubService)
    service.get_authenticated_repo_url.return_value = "https://token@github.com/org/repo.git"
    return service


@pytest.fixture
def repository_manager(mock_github_service):
    """Create a repository manager instance for testing."""
    return RepositoryManager(mock_github_service)


@pytest.fixture
def temp_repo_path():
    """Create a temporary repository path for testing."""
    temp_dir = tempfile.mkdtemp()
    repo_path = os.path.join(temp_dir, "test-repo")
    os.makedirs(repo_path)
    yield repo_path
    shutil.rmtree(temp_dir, ignore_errors=True)


class TestSaveAllFilesInVSCode:
    """Test the save all files functionality."""
    
    @patch('subprocess.run')
    @patch('platform.system')
    def test_save_all_files_vscode_command_success(self, mock_platform, mock_subprocess, repository_manager, temp_repo_path):
        """Test successful file saving using VS Code CLI command."""
        mock_platform.return_value = "Darwin"  # macOS
        mock_subprocess.return_value.returncode = 0
        mock_subprocess.return_value.stdout = ""
        mock_subprocess.return_value.stderr = ""
        
        result = repository_manager.save_all_files_in_vscode(temp_repo_path)
        
        assert result is True
        mock_subprocess.assert_called_with(
            ['code', '--command', 'workbench.action.files.saveAll'],
            capture_output=True,
            text=True,
            timeout=15
        )
    
    @patch('subprocess.run')
    @patch('platform.system')
    def test_save_all_files_fallback_to_applescript(self, mock_platform, mock_subprocess, repository_manager, temp_repo_path):
        """Test fallback to AppleScript on macOS when VS Code command fails."""
        mock_platform.return_value = "Darwin"  # macOS
        
        # First call (VS Code command) fails, second call (AppleScript) succeeds
        mock_subprocess.side_effect = [
            Mock(returncode=1, stderr="Command failed"),  # VS Code command fails
            Mock(returncode=0, stdout="", stderr="")      # AppleScript succeeds
        ]
        
        result = repository_manager.save_all_files_in_vscode(temp_repo_path)
        
        assert result is True
        assert mock_subprocess.call_count == 2
        
        # Check that AppleScript was called
        applescript_call = mock_subprocess.call_args_list[1]
        assert 'osascript' in applescript_call[0][0]
    
    @patch('subprocess.run')
    @patch('platform.system')
    def test_save_all_files_linux_xdotool(self, mock_platform, mock_subprocess, repository_manager, temp_repo_path):
        """Test Linux xdotool method when VS Code command fails."""
        mock_platform.return_value = "Linux"
        
        # VS Code command fails, xdotool search succeeds, xdotool key succeeds
        mock_subprocess.side_effect = [
            Mock(returncode=1, stderr="Command failed"),     # VS Code command fails
            Mock(returncode=0, stdout="12345", stderr=""),   # xdotool search finds window
            Mock(returncode=0, stdout="", stderr="")         # xdotool key succeeds
        ]
        
        result = repository_manager.save_all_files_in_vscode(temp_repo_path)
        
        assert result is True
        assert mock_subprocess.call_count == 3
        
        # Check that xdotool was called
        xdotool_search_call = mock_subprocess.call_args_list[1]
        assert 'xdotool' in xdotool_search_call[0][0]
        assert 'search' in xdotool_search_call[0][0]
    
    @patch('subprocess.run')
    @patch('platform.system')
    def test_save_all_files_windows_powershell(self, mock_platform, mock_subprocess, repository_manager, temp_repo_path):
        """Test Windows PowerShell method when VS Code command fails."""
        mock_platform.return_value = "Windows"
        
        # VS Code command fails, PowerShell succeeds
        mock_subprocess.side_effect = [
            Mock(returncode=1, stderr="Command failed"),  # VS Code command fails
            Mock(returncode=0, stdout="", stderr="")      # PowerShell succeeds
        ]
        
        result = repository_manager.save_all_files_in_vscode(temp_repo_path)
        
        assert result is True
        assert mock_subprocess.call_count == 2
        
        # Check that PowerShell was called
        powershell_call = mock_subprocess.call_args_list[1]
        assert 'powershell' in powershell_call[0][0]
    
    @patch('subprocess.run')
    def test_save_all_files_all_methods_fail_gracefully(self, mock_subprocess, repository_manager, temp_repo_path):
        """Test that the function gracefully handles all methods failing."""
        # All subprocess calls fail
        mock_subprocess.return_value.returncode = 1
        mock_subprocess.return_value.stderr = "All methods failed"
        
        result = repository_manager.save_all_files_in_vscode(temp_repo_path)
        
        # Should still return True to not fail the commit
        assert result is True
    
    @patch('subprocess.run')
    def test_save_all_files_timeout_gracefully(self, mock_subprocess, repository_manager, temp_repo_path):
        """Test that the function gracefully handles timeouts."""
        mock_subprocess.side_effect = subprocess.TimeoutExpired(['code'], 15)
        
        result = repository_manager.save_all_files_in_vscode(temp_repo_path)
        
        # Should return True to not fail the commit
        assert result is True
    
    @patch('subprocess.run')
    def test_save_all_files_file_not_found_gracefully(self, mock_subprocess, repository_manager, temp_repo_path):
        """Test that the function gracefully handles VS Code CLI not being available."""
        mock_subprocess.side_effect = FileNotFoundError("VS Code CLI not found")
        
        result = repository_manager.save_all_files_in_vscode(temp_repo_path)
        
        # Should return True to not fail the commit
        assert result is True


class TestCommitWithFileSaving:
    """Test that commit operations properly save files first."""
    
    @patch.object(RepositoryManager, 'save_all_files_in_vscode')
    @patch.object(RepositoryManager, 'ensure_git_config')
    @patch.object(RepositoryManager, 'ensure_stage_branch')
    @patch.object(RepositoryManager, '_push_with_retry')
    @patch('subprocess.run')
    @patch('os.path.exists')
    @patch('os.getcwd')
    @patch('os.chdir')
    def test_commit_code_changes_saves_files_first(self, mock_chdir, mock_getcwd, mock_exists, 
                                                  mock_subprocess, mock_push, mock_ensure_branch,
                                                  mock_ensure_config, mock_save_files, 
                                                  repository_manager, temp_repo_path):
        """Test that commit_code_changes calls save_all_files_in_vscode before committing."""
        # Setup mocks
        mock_exists.return_value = True
        mock_getcwd.return_value = "/original"
        mock_ensure_config.return_value = True
        mock_ensure_branch.return_value = True
        mock_save_files.return_value = True
        mock_push.return_value = True
        
        # Mock git status to show changes exist
        mock_subprocess.return_value.returncode = 0
        mock_subprocess.return_value.stdout = "M file.txt\n"
        mock_subprocess.return_value.stderr = ""
        
        # Mock repository path
        with patch.object(repository_manager, 'get_repository_path', return_value=temp_repo_path):
            result = repository_manager.commit_code_changes(
                participant_id="test-participant",
                study_stage=1,
                commit_message="Test commit",
                development_mode=True,
                github_token="token",
                github_org="org"
            )
        
        # Verify that save_all_files_in_vscode was called
        mock_save_files.assert_called_once_with(temp_repo_path)
        assert result is True
