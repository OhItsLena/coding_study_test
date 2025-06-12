"""
Participant management for the coding study Flask application.
Handles participant identification, coding conditions, and study stages.
"""

import hashlib
from typing import Optional


class ParticipantManager:
    """
    Manages participant identification and coding conditions.
    """
    
    @staticmethod
    def get_coding_condition(participant_id: str) -> str:
        """
        Determine the coding condition based on participant ID.
        
        Args:
            participant_id: The participant's unique identifier
            
        Returns:
            Either 'vibe' for vibe coding or 'ai-assisted' for AI-assisted coding
        """
        # Simple hash-based assignment for consistent condition per participant
        # This ensures the same participant always gets the same condition
        if participant_id == "Study Participant":
            return "vibe"  # Default for unknown participants
        
        # Use hash of participant ID to assign condition
        hash_value = int(hashlib.md5(participant_id.encode()).hexdigest(), 16)
        return "vibe" if hash_value % 2 == 0 else "ai-assisted"
