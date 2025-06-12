"""
Tests for GitHub service functionality.
"""
import pytest
from unittest.mock import patch, Mock
import requests

from models.github_service import GitHubService


class TestGitHubService:
    """Test cases for GitHubService class."""
    
    def test_get_authenticated_repo_url(self):
        """Test construction of authenticated repository URL."""
        service = GitHubService()
        
        url = service.get_authenticated_repo_url(
            "test-repo", 
            "test-token",
            "test-org"
        )
        
        expected = "https://test-token@github.com/test-org/test-repo.git"
        assert url == expected
    
    def test_get_authenticated_repo_url_no_token(self):
        """Test repository URL construction without token."""
        service = GitHubService()
        
        url = service.get_authenticated_repo_url(
            "test-repo", 
            "",
            "test-org"
        )
        
        expected = "https://github.com/test-org/test-repo.git"
        assert url == expected
    
    @patch('models.github_service.requests.get')
    def test_test_github_connectivity_success(self, mock_get):
        """Test successful GitHub connectivity test."""
        # Mock successful repo API call
        mock_repo_response = Mock()
        mock_repo_response.status_code = 200
        mock_repo_response.json.return_value = {
            "full_name": "test-org/study-test-participant",
            "private": True
        }
        
        mock_get.return_value = mock_repo_response
        
        service = GitHubService()
        result = service.test_github_connectivity(
            "test-participant",
            "test-token", 
            "test-org"
        )
        
        assert result is True
        assert mock_get.call_count == 1  # Only one API call needed
    
    @patch('models.github_service.requests.get')
    def test_test_github_connectivity_auth_failure(self, mock_get):
        """Test GitHub connectivity with authentication failure."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_get.return_value = mock_response
        
        service = GitHubService()
        result = service.test_github_connectivity(
            "test-participant",
            "invalid-token",
            "test-org"
        )
        
        assert result is False
    
    @patch('models.github_service.requests.get')
    def test_test_github_connectivity_repo_not_found(self, mock_get):
        """Test GitHub connectivity when repository doesn't exist."""
        # Mock repo not found
        mock_repo_response = Mock()
        mock_repo_response.status_code = 404
        
        mock_get.return_value = mock_repo_response
        
        service = GitHubService()
        result = service.test_github_connectivity(
            "test-participant",
            "test-token",
            "test-org"
        )
        
        assert result is False
    
    @patch('models.github_service.requests.get')
    def test_test_github_connectivity_network_error(self, mock_get):
        """Test GitHub connectivity with network error."""
        mock_get.side_effect = requests.RequestException("Network error")
        
        service = GitHubService()
        result = service.test_github_connectivity(
            "test-participant",
            "test-token",
            "test-org" 
        )
        
        assert result is False
    
    def test_test_github_connectivity_no_token(self):
        """Test GitHub connectivity without token."""
        service = GitHubService()
        result = service.test_github_connectivity(
            "test-participant",
            "",
            "test-org"
        )
        
        assert result is False
