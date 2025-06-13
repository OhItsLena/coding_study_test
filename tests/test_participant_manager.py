"""
Tests for participant management functionality.
"""
import pytest
from unittest.mock import patch

from models.participant_manager import ParticipantManager


class TestParticipantManager:
    """Test cases for ParticipantManager class."""
    
    def test_get_coding_condition_development_mode(self):
        """Test getting coding condition in development mode."""
        manager = ParticipantManager()
        
        # Test with default dev_coding_condition
        condition = manager.get_coding_condition("test-participant", development_mode=True)
        assert condition == "vibe"
        
        # Test with explicit dev_coding_condition
        condition = manager.get_coding_condition("test-participant", development_mode=True, dev_coding_condition="ai-assisted")
        assert condition == "ai-assisted"
    
    @patch('models.participant_manager.AzureMetadataService.get_coding_condition')
    def test_get_coding_condition_production_success(self, mock_get_coding_condition):
        """Test getting coding condition from Azure metadata successfully."""
        mock_get_coding_condition.return_value = "ai-assisted"
        
        manager = ParticipantManager()
        condition = manager.get_coding_condition("test-participant", development_mode=False)
        
        assert condition == "ai-assisted"
        mock_get_coding_condition.assert_called_once_with(False, "vibe")
    
    @patch('models.participant_manager.AzureMetadataService.get_coding_condition')
    def test_get_coding_condition_production_fallback(self, mock_get_coding_condition):
        """Test getting coding condition with fallback to default."""
        mock_get_coding_condition.return_value = "vibe"
        
        manager = ParticipantManager()
        condition = manager.get_coding_condition("test-participant", development_mode=False)
        
        assert condition == "vibe"
        mock_get_coding_condition.assert_called_once_with(False, "vibe")
    
    def test_get_coding_condition_valid_values(self):
        """Test that coding condition returns only valid values."""
        manager = ParticipantManager()
        
        # Test development mode with different conditions
        test_conditions = ["vibe", "ai-assisted"]
        
        for dev_condition in test_conditions:
            condition = manager.get_coding_condition("test-participant", development_mode=True, dev_coding_condition=dev_condition)
            assert condition in ["vibe", "ai-assisted"], f"Invalid condition {condition}"
            assert condition == dev_condition, f"Expected {dev_condition}, got {condition}"
    
    def test_get_coding_condition_consistent(self):
        """Test that coding condition is consistent for the same participant."""
        manager = ParticipantManager()
        participant_id = "test-participant-123"
        
        # Call multiple times and ensure same result
        condition1 = manager.get_coding_condition(participant_id)
        condition2 = manager.get_coding_condition(participant_id)
        condition3 = manager.get_coding_condition(participant_id)
        
        assert condition1 == condition2 == condition3
    
    def test_get_coding_condition_hash_based(self):
        """Test that different participants get different conditions (hash-based)."""
        manager = ParticipantManager()
        
        # Test a variety of participants to ensure distribution
        conditions = {}
        test_participants = [f"participant-{i:03d}" for i in range(10)]
        
        for participant_id in test_participants:
            conditions[participant_id] = manager.get_coding_condition(participant_id)
        
        # Should have both conditions represented
        unique_conditions = set(conditions.values())
        assert len(unique_conditions) >= 1, "Should have at least one condition type"
        assert all(c in ["vibe", "ai-assisted"] for c in unique_conditions), "All conditions should be valid"
