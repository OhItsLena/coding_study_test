#!/usr/bin/env python3
"""
Test script to verify GitHub authentication and repository access.
This script can be used to test your GitHub token before running the main application.
"""

import os
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

GITHUB_TOKEN = os.getenv('GITHUB_TOKEN', '')
GITHUB_ORG = os.getenv('GITHUB_ORG', 'LMU-Vibe-Coding-Study')
TEST_PARTICIPANT_ID = os.getenv('DEV_PARTICIPANT_ID', 'dev-participant')

def test_github_auth():
    """Test GitHub authentication and repository access."""
    print("GitHub Authentication Test")
    print("=" * 40)
    
    if not GITHUB_TOKEN:
        print("❌ No GITHUB_TOKEN found in environment variables")
        print("   Please set GITHUB_TOKEN in your .env file")
        return False
    
    print(f"✓ GitHub token found (length: {len(GITHUB_TOKEN)})")
    print(f"✓ GitHub organization: {GITHUB_ORG}")
    print(f"✓ Test participant ID: {TEST_PARTICIPANT_ID}")
    
    # Test GitHub API access
    try:
        headers = {'Authorization': f'token {GITHUB_TOKEN}'}
        
        # Test basic API access
        print("\nTesting GitHub API access...")
        response = requests.get('https://api.github.com/user', headers=headers, timeout=10)
        
        if response.status_code == 200:
            user_data = response.json()
            print(f"✅ Authenticated as: {user_data.get('login', 'Unknown')}")
        else:
            print(f"❌ GitHub API authentication failed (status: {response.status_code})")
            return False
        
        # Test repository access
        repo_name = f"study-{TEST_PARTICIPANT_ID}"
        print(f"\nTesting repository access: {GITHUB_ORG}/{repo_name}")
        
        response = requests.get(
            f"https://api.github.com/repos/{GITHUB_ORG}/{repo_name}",
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            repo_data = response.json()
            print(f"✅ Repository accessible: {repo_data.get('full_name')}")
            print(f"   Private: {repo_data.get('private', 'Unknown')}")
            print(f"   Clone URL: {repo_data.get('clone_url')}")
        elif response.status_code == 404:
            print(f"❌ Repository not found: {GITHUB_ORG}/{repo_name}")
            print("   Make sure the repository exists and the token has access")
            return False
        else:
            print(f"❌ Repository access failed (status: {response.status_code})")
            return False
        
        # Test authenticated clone URL construction
        print(f"\nTesting authenticated URL construction...")
        auth_url = f"https://{GITHUB_TOKEN}@github.com/{GITHUB_ORG}/{repo_name}.git"
        print(f"✅ Authenticated clone URL: https://***@github.com/{GITHUB_ORG}/{repo_name}.git")
        
        print("\n🎉 All tests passed! GitHub authentication is working correctly.")
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error: {str(e)}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_github_auth()
    exit(0 if success else 1)
