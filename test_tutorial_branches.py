#!/usr/bin/env python3
"""
Test script for tutorial branch functionality with remote branches
"""

import os
import sys
import tempfile
import shutil
import subprocess
from unittest.mock import patch, MagicMock

# Add the project root to the path
sys.path.insert(0, '/Users/hammerer/git/coding_study_test_tool')

from models.repository_manager import RepositoryManager
from models.github_service import GitHubService

def create_test_repo_with_remote_tutorial_branch(repo_path):
    """Create a test repository with a remote tutorial branch"""
    kwargs = {
        'cwd': repo_path,
        'capture_output': True,
        'text': True
    }
    
    # Initialize git repo
    subprocess.run(['git', 'init'], **kwargs)
    subprocess.run(['git', 'config', 'user.name', 'Test User'], **kwargs)
    subprocess.run(['git', 'config', 'user.email', 'test@example.com'], **kwargs)
    
    # Create initial README on main branch
    readme_path = os.path.join(repo_path, 'README.md')
    with open(readme_path, 'w') as f:
        f.write('# Test Repository\n')
    
    subprocess.run(['git', 'add', 'README.md'], **kwargs)
    subprocess.run(['git', 'commit', '-m', 'Initial commit'], **kwargs)
    subprocess.run(['git', 'branch', '-M', 'main'], **kwargs)
    
    # Create tutorial branch
    subprocess.run(['git', 'checkout', '-b', 'tutorial'], **kwargs)
    
    # Add some tutorial content
    tutorial_file = os.path.join(repo_path, 'tutorial_notes.txt')
    with open(tutorial_file, 'w') as f:
        f.write('Tutorial content from remote\n')
    
    subprocess.run(['git', 'add', 'tutorial_notes.txt'], **kwargs)
    subprocess.run(['git', 'commit', '-m', 'Add tutorial content'], **kwargs)
    
    # Switch back to main
    subprocess.run(['git', 'checkout', 'main'], **kwargs)
    
    return True

def test_remote_tutorial_branch_handling():
    """Test handling of remote tutorial branches"""
    print("Testing remote tutorial branch handling...")
    
    # Create a temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create "origin" repository with tutorial branch
        origin_repo_path = os.path.join(temp_dir, "origin-repo")
        os.makedirs(origin_repo_path)
        
        create_test_repo_with_remote_tutorial_branch(origin_repo_path)
        
        # Create "cloned" repository
        cloned_repo_path = os.path.join(temp_dir, "cloned-repo")
        
        # Clone the origin repository
        kwargs = {
            'capture_output': True,
            'text': True
        }
        
        result = subprocess.run([
            'git', 'clone', origin_repo_path, cloned_repo_path
        ], **kwargs)
        
        if result.returncode != 0:
            print(f"❌ Failed to clone test repository: {result.stderr}")
            return False
        
        # Mock the GitHub service
        github_service = MagicMock(spec=GitHubService)
        github_service.get_authenticated_repo_url.return_value = "https://test-repo.git"
        
        # Create repository manager
        repo_manager = RepositoryManager(github_service)
        
        # Patch the get_repository_path method to use our test directory
        with patch.object(repo_manager, 'get_repository_path', return_value=cloned_repo_path):
            with patch.object(repo_manager, 'ensure_git_config', return_value=True):
                # Test tutorial branch setup with existing remote tutorial branch
                result = repo_manager.setup_tutorial_branch(
                    participant_id="test-participant",
                    development_mode=True,
                    github_token="test-token",
                    github_org="test-org"
                )
                
                if not result:
                    print("❌ Tutorial branch setup failed")
                    return False
                
                print("✅ Tutorial branch setup successful")
                
                # Check if we're on tutorial branch
                kwargs = {
                    'cwd': cloned_repo_path,
                    'capture_output': True,
                    'text': True
                }
                
                current_branch_result = subprocess.run(['git', 'branch', '--show-current'], **kwargs)
                if current_branch_result.stdout.strip() != 'tutorial':
                    print(f"❌ Not on tutorial branch, currently on: {current_branch_result.stdout.strip()}")
                    return False
                
                print("✅ Currently on tutorial branch")
                
                # Check if tutorial content from remote is present
                tutorial_file = os.path.join(cloned_repo_path, 'tutorial_notes.txt')
                if not os.path.exists(tutorial_file):
                    print("❌ Tutorial content from remote not found")
                    return False
                
                with open(tutorial_file, 'r') as f:
                    content = f.read()
                    if 'Tutorial content from remote' not in content:
                        print("❌ Tutorial content from remote not correct")
                        return False
                
                print("✅ Tutorial content from remote is present")
        
        print("✅ All remote tutorial branch tests passed!")
        return True

def test_local_tutorial_branch_handling():
    """Test handling when local tutorial branch already exists"""
    print("Testing local tutorial branch handling...")
    
    # Create a temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        test_repo_path = os.path.join(temp_dir, "test-repo")
        os.makedirs(test_repo_path)
        
        kwargs = {
            'cwd': test_repo_path,
            'capture_output': True,
            'text': True
        }
        
        # Initialize git repo with local tutorial branch
        subprocess.run(['git', 'init'], **kwargs)
        subprocess.run(['git', 'config', 'user.name', 'Test User'], **kwargs)
        subprocess.run(['git', 'config', 'user.email', 'test@example.com'], **kwargs)
        
        # Create initial README
        readme_path = os.path.join(test_repo_path, 'README.md')
        with open(readme_path, 'w') as f:
            f.write('# Test Repository\n')
        
        subprocess.run(['git', 'add', 'README.md'], **kwargs)
        subprocess.run(['git', 'commit', '-m', 'Initial commit'], **kwargs)
        
        # Create local tutorial branch
        subprocess.run(['git', 'checkout', '-b', 'tutorial'], **kwargs)
        subprocess.run(['git', 'checkout', 'main'], **kwargs)
        
        # Mock the GitHub service
        github_service = MagicMock(spec=GitHubService)
        github_service.get_authenticated_repo_url.return_value = "https://test-repo.git"
        
        # Create repository manager
        repo_manager = RepositoryManager(github_service)
        
        # Patch the get_repository_path method to use our test directory
        with patch.object(repo_manager, 'get_repository_path', return_value=test_repo_path):
            with patch.object(repo_manager, 'ensure_git_config', return_value=True):
                # Test tutorial branch setup with existing local tutorial branch
                result = repo_manager.setup_tutorial_branch(
                    participant_id="test-participant",
                    development_mode=True,
                    github_token="test-token",
                    github_org="test-org"
                )
                
                if not result:
                    print("❌ Tutorial branch setup failed")
                    return False
                
                print("✅ Tutorial branch setup successful")
                
                # Check if we're on tutorial branch
                current_branch_result = subprocess.run(['git', 'branch', '--show-current'], **kwargs)
                if current_branch_result.stdout.strip() != 'tutorial':
                    print(f"❌ Not on tutorial branch, currently on: {current_branch_result.stdout.strip()}")
                    return False
                
                print("✅ Currently on tutorial branch")
        
        print("✅ All local tutorial branch tests passed!")
        return True

if __name__ == "__main__":
    print("Testing tutorial branch functionality with various scenarios...\n")
    
    success1 = test_remote_tutorial_branch_handling()
    print()
    success2 = test_local_tutorial_branch_handling()
    
    if success1 and success2:
        print("\n🎉 All tutorial branch tests completed successfully!")
    else:
        print("\n❌ Some tutorial branch tests failed!")
        sys.exit(1)
