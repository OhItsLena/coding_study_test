"""
Tests for Azure service functionality.
"""
import pytest
from unittest.mock import patch, Mock
import requests

from models.azure_service import AzureMetadataService


class TestAzureMetadataService:
    """Test cases for AzureMetadataService class."""
    
    def test_get_participant_id_development_mode(self):
        """Test getting participant ID in development mode."""
        service = AzureMetadataService()
        participant_id = service.get_participant_id(True, "dev-test-participant")
        
        assert participant_id == "dev-test-participant"
    
    @patch('models.azure_service.requests.get')
    def test_get_participant_id_production_success(self, mock_get):
        """Test getting participant ID from Azure metadata successfully."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "participant_id:prod-participant-123;study_stage:1"
        mock_get.return_value = mock_response
        
        service = AzureMetadataService()
        participant_id = service.get_participant_id(False, "dev-fallback")
        
        assert participant_id == "prod-participant-123"
        mock_get.assert_called_once()
    
    @patch('models.azure_service.requests.get')
    def test_get_participant_id_production_failure(self, mock_get):
        """Test getting participant ID when Azure metadata fails."""
        mock_get.side_effect = requests.RequestException("Connection failed")
        
        service = AzureMetadataService()
        participant_id = service.get_participant_id(False, "dev-fallback")
        
        assert participant_id == "Study Participant"  # Actual fallback value
    
    @patch('models.azure_service.requests.get')
    def test_get_participant_id_malformed_response(self, mock_get):
        """Test getting participant ID with malformed Azure response."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "invalid_format_no_participant_id"
        mock_get.return_value = mock_response
        
        service = AzureMetadataService()
        participant_id = service.get_participant_id(False, "dev-fallback")
        
        assert participant_id == "Study Participant"  # Actual fallback value
    
    def test_get_study_stage_development_mode(self):
        """Test getting study stage in development mode."""
        service = AzureMetadataService()
        
        # Test default dev_stage
        stage = service.get_study_stage("test-participant", True, 1)
        assert stage == 1
        
        # Test explicit dev_stage
        stage = service.get_study_stage("test-participant", True, 2)
        assert stage == 2
    
    @patch('models.azure_service.requests.get')
    def test_get_study_stage_production_success(self, mock_get):
        """Test getting study stage from Azure metadata successfully."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "participant_id:test-participant;study_stage:2;environment:production"
        mock_get.return_value = mock_response
        
        service = AzureMetadataService()
        stage = service.get_study_stage("test-participant", False, 1)
        
        assert stage == 2
        mock_get.assert_called_once()
    
    @patch('models.azure_service.requests.get')
    def test_get_study_stage_production_failure(self, mock_get):
        """Test getting study stage when Azure metadata fails."""
        mock_get.side_effect = requests.RequestException("Connection failed")
        
        service = AzureMetadataService()
        stage = service.get_study_stage("test-participant", False, 2)
        
        assert stage == 1  # Default fallback
    
    @patch('models.azure_service.requests.get')
    def test_get_study_stage_invalid_value(self, mock_get):
        """Test getting study stage with invalid stage value in metadata."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "participant_id:test-participant;study_stage:invalid;environment:production"
        mock_get.return_value = mock_response
        
        service = AzureMetadataService()
        stage = service.get_study_stage("test-participant", False, 2)
        
        assert stage == 1  # Default fallback
    
    @patch('models.azure_service.requests.get')
    def test_get_study_stage_missing_tag(self, mock_get):
        """Test getting study stage when study_stage tag is missing."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "participant_id:test-participant;environment:production"
        mock_get.return_value = mock_response
        
        service = AzureMetadataService()
        stage = service.get_study_stage("test-participant", False, 2)
        
        assert stage == 1  # Default fallback
    
    def test_get_coding_condition_development_mode(self):
        """Test getting coding condition in development mode."""
        service = AzureMetadataService()
        
        # Test default dev_coding_condition
        condition = service.get_coding_condition(True, "vibe")
        assert condition == "vibe"
        
        # Test explicit dev_coding_condition
        condition = service.get_coding_condition(True, "ai-assisted")
        assert condition == "ai-assisted"
    
    @patch('models.azure_service.requests.get')
    def test_get_coding_condition_production_success(self, mock_get):
        """Test getting coding condition from Azure metadata successfully."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "participant_id:test-participant;coding_condition:ai-assisted;environment:production"
        mock_get.return_value = mock_response
        
        service = AzureMetadataService()
        condition = service.get_coding_condition(False, "vibe")
        
        assert condition == "ai-assisted"
        mock_get.assert_called_once()
    
    @patch('models.azure_service.requests.get')
    def test_get_coding_condition_production_failure(self, mock_get):
        """Test getting coding condition when Azure metadata fails."""
        mock_get.side_effect = requests.RequestException("Connection failed")
        
        service = AzureMetadataService()
        condition = service.get_coding_condition(False, "ai-assisted")
        
        assert condition == "vibe"  # Default fallback
    
    @patch('models.azure_service.requests.get')
    def test_get_coding_condition_invalid_value(self, mock_get):
        """Test getting coding condition with invalid value in metadata."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "participant_id:test-participant;coding_condition:invalid-condition;environment:production"
        mock_get.return_value = mock_response
        
        service = AzureMetadataService()
        condition = service.get_coding_condition(False, "ai-assisted")
        
        assert condition == "vibe"  # Default fallback
    
    @patch('models.azure_service.requests.get')
    def test_get_coding_condition_missing_tag(self, mock_get):
        """Test getting coding condition when coding_condition tag is missing."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "participant_id:test-participant;study_stage:1;environment:production"
        mock_get.return_value = mock_response
        
        service = AzureMetadataService()
        condition = service.get_coding_condition(False, "ai-assisted")
        
        assert condition == "vibe"  # Default fallback
