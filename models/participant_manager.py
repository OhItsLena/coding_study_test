"""
Participant management for the coding study Flask application.
Handles participant identification, coding conditions, and study stages.
"""

import hashlib
from typing import Optional
from .azure_service import AzureMetadataService


class ParticipantManager:
    """
    Manages participant identification and coding conditions.
    """
    
    @staticmethod
    def get_coding_condition(participant_id: str, development_mode: bool = False, 
                           dev_coding_condition: str = "vibe") -> str:
        """
        Determine the coding condition from Azure VM tags.
        
        Args:
            participant_id: The participant's unique identifier
            development_mode: Whether running in development mode
            dev_coding_condition: Coding condition to use in development mode
            
        Returns:
            Either 'vibe' for vibe coding or 'ai-assisted' for AI-assisted coding
        """
        # Get coding condition from Azure VM tags
        return AzureMetadataService.get_coding_condition(development_mode, dev_coding_condition)
