#!/usr/bin/env python3
"""
Test script for tutorial functionality
"""

import os
import sys
import tempfile
import shutil
from unittest.mock import patch, MagicMock

# Add the project root to the path
sys.path.insert(0, '/Users/hammerer/git/coding_study_test_tool')

from models.repository_manager import RepositoryManager
from models.github_service import GitHubService

def test_tutorial_branch_creation():
    """Test tutorial branch creation functionality"""
    print("Testing tutorial branch creation...")
    
    # Create a temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        # Mock the GitHub service
        github_service = MagicMock(spec=GitHubService)
        github_service.get_authenticated_repo_url.return_value = "https://test-repo.git"
        
        # Create repository manager
        repo_manager = RepositoryManager(github_service)
        
        # Mock the get_repository_path method to use our temp directory
        test_repo_path = os.path.join(temp_dir, "test-repo")
        os.makedirs(test_repo_path)
        
        # Initialize a git repo in the test directory
        import subprocess
        kwargs = {
            'cwd': test_repo_path,
            'capture_output': True,
            'text': True
        }
        
        # Initialize git repo
        subprocess.run(['git', 'init'], **kwargs)
        subprocess.run(['git', 'config', 'user.name', 'Test User'], **kwargs)
        subprocess.run(['git', 'config', 'user.email', 'test@example.com'], **kwargs)
        
        # Create initial README
        readme_path = os.path.join(test_repo_path, 'README.md')
        with open(readme_path, 'w') as f:
            f.write('# Test Repository\n')
        
        subprocess.run(['git', 'add', 'README.md'], **kwargs)
        subprocess.run(['git', 'commit', '-m', 'Initial commit'], **kwargs)
        
        # Patch the get_repository_path method
        with patch.object(repo_manager, 'get_repository_path', return_value=test_repo_path):
            with patch.object(repo_manager, 'ensure_git_config', return_value=True):
                # Test tutorial branch setup
                result = repo_manager.setup_tutorial_branch(
                    participant_id="test-participant",
                    development_mode=True,
                    github_token="test-token",
                    github_org="test-org"
                )
                
                if result:
                    print("✅ Tutorial branch setup successful")
                    
                    # Check if tutorial branch exists
                    branch_result = subprocess.run(['git', 'branch', '--list', 'tutorial'], **kwargs)
                    if 'tutorial' in branch_result.stdout:
                        print("✅ Tutorial branch created successfully")
                    else:
                        print("❌ Tutorial branch not found")
                        return False
                        
                    # Check if we're on tutorial branch
                    current_branch_result = subprocess.run(['git', 'branch', '--show-current'], **kwargs)
                    if current_branch_result.stdout.strip() == 'tutorial':
                        print("✅ Currently on tutorial branch")
                    else:
                        print("❌ Not on tutorial branch")
                        return False
                        
                else:
                    print("❌ Tutorial branch setup failed")
                    return False
        
        print("✅ All tutorial tests passed!")
        return True

if __name__ == "__main__":
    success = test_tutorial_branch_creation()
    if success:
        print("\n🎉 Tutorial functionality test completed successfully!")
    else:
        print("\n❌ Tutorial functionality test failed!")
        sys.exit(1)
