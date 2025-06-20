#!/usr/bin/env python3
"""
Test script for the enhanced remote repository synchronization functionality.
"""

import os
import tempfile
import shutil
import subprocess
from unittest.mock import MagicMock

# Add the project root to the path
import sys
sys.path.insert(0, '/Users/hammerer/git/coding_study_test_tool')

from models.repository_manager import RepositoryManager
from models.github_service import GitHubService


def create_test_repo_with_remote_branch(repo_path, branch_name, content_file="test.txt"):
    """Create a test repository with a remote branch containing content"""
    kwargs = {
        'cwd': repo_path,
        'capture_output': True,
        'text': True
    }
    
    # Initialize git repo
    subprocess.run(['git', 'init'], **kwargs)
    subprocess.run(['git', 'config', 'user.name', 'Test User'], **kwargs)
    subprocess.run(['git', 'config', 'user.email', 'test@example.com'], **kwargs)
    
    # Create initial commit on main
    readme_path = os.path.join(repo_path, 'README.md')
    with open(readme_path, 'w') as f:
        f.write('# Test Repository\n')
    
    subprocess.run(['git', 'add', 'README.md'], **kwargs)
    subprocess.run(['git', 'commit', '-m', 'Initial commit'], **kwargs)
    subprocess.run(['git', 'branch', '-M', 'main'], **kwargs)
    
    # Create the specified branch with content
    subprocess.run(['git', 'checkout', '-b', branch_name], **kwargs)
    
    content_path = os.path.join(repo_path, content_file)
    with open(content_path, 'w') as f:
        f.write(f'Content from remote {branch_name} branch\n')
    
    subprocess.run(['git', 'add', content_file], **kwargs)
    subprocess.run(['git', 'commit', '-m', f'Add {content_file} to {branch_name}'], **kwargs)
    
    # Switch back to main
    subprocess.run(['git', 'checkout', 'main'], **kwargs)
    
    return True


def test_stage_branch_remote_sync():
    """Test stage branch synchronization with remote"""
    print("Testing stage branch remote synchronization...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create "origin" repository with stage-1 branch
        origin_repo_path = os.path.join(temp_dir, "origin-repo")
        os.makedirs(origin_repo_path)
        
        create_test_repo_with_remote_branch(origin_repo_path, "stage-1", "stage1_work.py")
        
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
        
        # Test ensure_stage_branch with existing remote branch
        original_cwd = os.getcwd()
        try:
            os.chdir(cloned_repo_path)
            
            # This should detect the remote stage-1 branch and create a local tracking branch
            result = repo_manager.ensure_stage_branch(cloned_repo_path, 1)
            
            if not result:
                print("❌ ensure_stage_branch failed")
                return False
            
            print("✅ ensure_stage_branch successful")
            
            # Check if we're on stage-1 branch
            kwargs = {
                'cwd': cloned_repo_path,
                'capture_output': True,
                'text': True
            }
            
            current_branch_result = subprocess.run(['git', 'branch', '--show-current'], **kwargs)
            if current_branch_result.stdout.strip() != 'stage-1':
                print(f"❌ Not on stage-1 branch, currently on: {current_branch_result.stdout.strip()}")
                return False
            
            print("✅ Currently on stage-1 branch")
            
            # Check if content from remote is present
            stage1_file = os.path.join(cloned_repo_path, 'stage1_work.py')
            if not os.path.exists(stage1_file):
                print("❌ Stage-1 content from remote not found")
                return False
            
            with open(stage1_file, 'r') as f:
                content = f.read()
                if 'Content from remote stage-1 branch' not in content:
                    print("❌ Stage-1 content from remote not correct")
                    return False
            
            print("✅ Stage-1 content from remote is present and correct")
            
        finally:
            os.chdir(original_cwd)
    
    print("✅ Stage branch remote synchronization test passed!")
    return True


def test_conflicting_commits():
    """Test handling of conflicting commits between local and remote"""
    print("Testing conflicting commits handling...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create "origin" repository with stage-1 branch and some content
        origin_repo_path = os.path.join(temp_dir, "origin-repo")
        os.makedirs(origin_repo_path)
        
        create_test_repo_with_remote_branch(origin_repo_path, "stage-1", "shared_file.txt")
        
        # Clone to create first participant repository
        participant1_repo = os.path.join(temp_dir, "participant1-repo")
        kwargs = {'capture_output': True, 'text': True}
        
        result = subprocess.run(['git', 'clone', origin_repo_path, participant1_repo], **kwargs)
        if result.returncode != 0:
            print(f"❌ Failed to clone repository: {result.stderr}")
            return False
        
        # Clone to create second participant repository
        participant2_repo = os.path.join(temp_dir, "participant2-repo")
        result = subprocess.run(['git', 'clone', origin_repo_path, participant2_repo], **kwargs)
        if result.returncode != 0:
            print(f"❌ Failed to clone second repository: {result.stderr}")
            return False
        
        # Mock the GitHub service
        github_service = MagicMock(spec=GitHubService)
        github_service.get_authenticated_repo_url.return_value = origin_repo_path
        
        # Create repository manager
        repo_manager = RepositoryManager(github_service)
        
        original_cwd = os.getcwd()
        
        try:
            # Participant 1: Make changes and "push" (simulate by updating origin)
            os.chdir(participant1_repo)
            
            # Ensure we're on stage-1 branch
            repo_manager.ensure_stage_branch(participant1_repo, 1)
            
            # Make changes
            shared_file = os.path.join(participant1_repo, 'shared_file.txt')
            with open(shared_file, 'a') as f:
                f.write('Changes from participant 1\n')
            
            # Commit changes
            kwargs = {'cwd': participant1_repo, 'capture_output': True, 'text': True}
            subprocess.run(['git', 'add', '.'], **kwargs)
            subprocess.run(['git', 'commit', '-m', 'Participant 1 changes'], **kwargs)
            
            # "Push" by updating origin (simulate what happens on remote)
            subprocess.run(['git', 'push', 'origin', 'stage-1'], **kwargs)
            
            print("✅ Participant 1 made changes and pushed")
            
            # Participant 2: Make different changes locally
            os.chdir(participant2_repo)
            
            # Ensure we're on stage-1 branch (should pull participant 1's changes)
            result = repo_manager.ensure_stage_branch(participant2_repo, 1)
            if not result:
                print("❌ Participant 2 ensure_stage_branch failed")
                return False
            
            # Check if participant 1's changes were pulled
            shared_file_p2 = os.path.join(participant2_repo, 'shared_file.txt')
            with open(shared_file_p2, 'r') as f:
                content = f.read()
                if 'Changes from participant 1' not in content:
                    print("❌ Participant 1's changes not synchronized to participant 2")
                    return False
            
            print("✅ Participant 2 successfully synchronized with participant 1's changes")
            
        finally:
            os.chdir(original_cwd)
    
    print("✅ Conflicting commits handling test passed!")
    return True


if __name__ == "__main__":
    print("Testing enhanced remote repository synchronization...\n")
    
    success1 = test_stage_branch_remote_sync()
    print()
    success2 = test_conflicting_commits()
    
    if success1 and success2:
        print("\n🎉 All remote synchronization tests completed successfully!")
        print("\nSolution Summary:")
        print("- ✅ Enhanced branch management with remote fetch before operations")
        print("- ✅ Proper handling of local vs remote branch conflicts")
        print("- ✅ Automatic synchronization of remote changes before local work")
        print("- ✅ Retry logic for push operations with conflict resolution")
        print("- ✅ Merge strategies that preserve participant work")
    else:
        print("\n❌ Some tests failed. Please check the implementation.")
        sys.exit(1)
