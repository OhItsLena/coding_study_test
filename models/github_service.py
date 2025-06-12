"""
GitHub integration for the coding study Flask application.
Handles GitHub connectivity, authentication, and repository operations.
"""

import requests
from typing import Optional


class GitHubService:
    """
    Handles GitHub connectivity and authentication.
    """
    
    @staticmethod
    def get_authenticated_repo_url(repo_name: str, github_token: Optional[str], github_org: str) -> str:
        """
        Construct the authenticated GitHub repository URL.
        If GITHUB_TOKEN is provided, includes it in the URL for authentication.
        
        Args:
            repo_name: Name of the repository
            github_token: GitHub personal access token (optional)
            github_org: GitHub organization name
        
        Returns:
            The URL for cloning/accessing the repository
        """
        if github_token:
            # Use token-based authentication with HTTPS
            return f"https://{github_token}@github.com/{github_org}/{repo_name}.git"
        else:
            # Use public HTTPS URL (for public repositories only)
            return f"https://github.com/{github_org}/{repo_name}.git"
    
    @staticmethod
    def test_github_connectivity(participant_id: str, github_token: Optional[str], github_org: str) -> bool:
        """
        Test GitHub connectivity and authentication by checking if the repository exists.
        
        Args:
            participant_id: The participant's unique identifier
            github_token: GitHub personal access token (optional)
            github_org: GitHub organization name
        
        Returns:
            True if the repository is accessible, False otherwise
        """
        try:
            repo_name = f"study-{participant_id}"
            
            if github_token:
                # Test with authenticated request
                headers = {'Authorization': f'token {github_token}'}
                response = requests.get(
                    f"https://api.github.com/repos/{github_org}/{repo_name}",
                    headers=headers,
                    timeout=10
                )
                
                if response.status_code == 200:
                    print(f"✓ GitHub repository {repo_name} is accessible with authentication")
                    return True
                elif response.status_code == 404:
                    print(f"✗ Repository {repo_name} not found or not accessible")
                    return False
                elif response.status_code == 401:
                    print(f"✗ GitHub authentication failed - check your token")
                    return False
                else:
                    print(f"✗ GitHub API returned status code: {response.status_code}")
                    return False
            else:
                # Test public access without authentication
                response = requests.get(
                    f"https://api.github.com/repos/{github_org}/{repo_name}",
                    timeout=10
                )
                
                if response.status_code == 200:
                    print(f"✓ Public repository {repo_name} is accessible")
                    return True
                else:
                    print(f"✗ Repository {repo_name} not publicly accessible (status: {response.status_code})")
                    return False
                    
        except requests.exceptions.RequestException as e:
            print(f"✗ Failed to connect to GitHub API: {str(e)}")
            return False
        except Exception as e:
            print(f"✗ Error testing GitHub connectivity: {str(e)}")
            return False
