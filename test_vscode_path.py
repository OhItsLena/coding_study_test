#!/usr/bin/env python3
"""
Test script to verify VS Code workspace storage path detection.
"""

import os
import platform
from models.study_logger import StudyLogger
from models.github_service import GitHubService

def test_vscode_path_detection():
    """Test the VS Code workspace storage path detection."""
    print("Testing VS Code workspace storage path detection...")
    print(f"Platform: {platform.system()}")
    
    # Create instances
    github_service = GitHubService()
    study_logger = StudyLogger(github_service)
    
    # Get the VS Code workspace storage path
    vscode_path = study_logger.get_vscode_workspace_storage_path()
    
    if vscode_path:
        print(f"VS Code workspace storage path: {vscode_path}")
        print(f"Path exists: {os.path.exists(vscode_path)}")
        
        if os.path.exists(vscode_path):
            try:
                # List some contents (first 5 items)
                contents = os.listdir(vscode_path)
                print(f"Number of workspace directories: {len(contents)}")
                if contents:
                    print("First 5 workspace directories:")
                    for item in contents[:5]:
                        print(f"  - {item}")
            except PermissionError:
                print("Permission denied when trying to list contents")
        else:
            print("Path does not exist - VS Code might not be installed or never used")
    else:
        print("Could not determine VS Code workspace storage path for this platform")

if __name__ == "__main__":
    test_vscode_path_detection()
