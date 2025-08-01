"""
Azure VM integration for the coding study Flask application.
Handles Azure Instance Metadata Service queries for participant information.
"""

import requests
import logging
from typing import Optional

# Get logger for this module
logger = logging.getLogger(__name__)


class AzureMetadataService:
    """
    Handles interaction with Azure Instance Metadata Service.
    """
    
    METADATA_URL_TAGS = "http://169.254.169.254/metadata/instance/compute/tags?api-version=2021-02-01&format=text"
    HEADERS = {'Metadata': 'true'}
    TIMEOUT = 5
    
    @classmethod
    def get_study_stage(cls, participant_id: str, development_mode: bool, dev_stage: int = 1) -> int:
        """
        Determine if the participant is in stage 1 or stage 2 of the study.
        
        Gets the study_stage from Azure VM tags using the Instance Metadata Service.
        In development mode, returns the dev_stage parameter.
        Returns 1 if the tag cannot be found.
        
        Args:
            participant_id: The participant's unique identifier
            development_mode: Whether running in development mode
            dev_stage: Stage to use in development mode
        
        Returns:
            Study stage (1 or 2)
        """
        if development_mode:
            logger.info(f"Development mode: Using mocked study stage: {dev_stage}")
            return dev_stage
        
        try:
            response = requests.get(cls.METADATA_URL_TAGS, headers=cls.HEADERS, timeout=cls.TIMEOUT)
            
            if response.status_code == 200:
                tags_text = response.text
                # Tags are returned as semicolon-separated key:value pairs
                for tag in tags_text.split(';'):
                    if ':' in tag:
                        key, value = tag.split(':', 1)
                        if key.strip().lower() == 'study_stage':
                            try:
                                stage = int(value.strip())
                                if stage in [1, 2]:
                                    return stage
                            except ValueError:
                                logger.info(f"Invalid study_stage tag value: {value.strip()}")
            
            # Default to stage 1 if tag not found or invalid
            return 1
        except Exception as e:
            logger.info(f"Error getting study stage from Azure VM tags: {str(e)}")
            # Default to stage 1 if we can't reach the metadata service or any other error occurs
            return 1
    
    @classmethod
    def get_participant_id(cls, development_mode: bool, dev_participant_id: str) -> str:
        """
        Get the participant_id from Azure VM tags using the Instance Metadata Service.
        In development mode, returns a mocked participant ID.
        
        Args:
            development_mode: Whether running in development mode
            dev_participant_id: Participant ID to use in development mode
        
        Returns:
            The participant_id if found, otherwise returns a default message
        """
        if development_mode:
            logger.info(f"Development mode: Using mocked participant ID: {dev_participant_id}")
            return dev_participant_id
        
        try:
            response = requests.get(cls.METADATA_URL_TAGS, headers=cls.HEADERS, timeout=cls.TIMEOUT)
            
            if response.status_code == 200:
                tags_text = response.text
                # Tags are returned as semicolon-separated key:value pairs
                for tag in tags_text.split(';'):
                    if ':' in tag:
                        key, value = tag.split(':', 1)
                        if key.strip().lower() == 'participant_id':
                            return value.strip()
            
            return "Study Participant"
        except Exception:
            # If we can't reach the metadata service or any other error occurs
            return "Study Participant"
    
    @classmethod
    def get_coding_condition(cls, development_mode: bool, dev_coding_condition: str = "vibe") -> str:
        """
        Get the coding_condition from Azure VM tags using the Instance Metadata Service.
        In development mode, returns the dev_coding_condition parameter.
        
        Args:
            development_mode: Whether running in development mode
            dev_coding_condition: Coding condition to use in development mode
        
        Returns:
            The coding condition ('vibe' or 'ai-assisted'), defaults to 'vibe' if not found
        """
        if development_mode:
            logger.info(f"Development mode: Using mocked coding condition: {dev_coding_condition}")
            return dev_coding_condition
        
        try:
            response = requests.get(cls.METADATA_URL_TAGS, headers=cls.HEADERS, timeout=cls.TIMEOUT)
            
            if response.status_code == 200:
                tags_text = response.text
                # Tags are returned as semicolon-separated key:value pairs
                for tag in tags_text.split(';'):
                    if ':' in tag:
                        key, value = tag.split(':', 1)
                        if key.strip().lower() == 'coding_condition':
                            condition = value.strip().lower()
                            if condition in ['vibe', 'ai-assisted']:
                                return condition
                            else:
                                logger.info(f"Invalid coding_condition tag value: {value.strip()}")
            
            # Default to 'vibe' if tag not found or invalid
            return "vibe"
        except Exception as e:
            logger.info(f"Error getting coding condition from Azure VM tags: {str(e)}")
            # Default to 'vibe' if we can't reach the metadata service or any other error occurs
            return "vibe"
    
    @classmethod
    def get_prolific_code(cls, development_mode: bool, dev_prolific_code: str = "ABCDEFG") -> str:
        """
        Get the prolific_code from Azure VM tags using the Instance Metadata Service.
        In development mode, returns the dev_prolific_code parameter.
        
        Args:
            development_mode: Whether running in development mode
            dev_prolific_code: Prolific code to use in development mode
        
        Returns:
            The prolific completion code, defaults to 'ABCDEFG' if not found
        """
        if development_mode:
            logger.info(f"Development mode: Using mocked prolific code: {dev_prolific_code}")
            return dev_prolific_code
        
        try:
            response = requests.get(cls.METADATA_URL_TAGS, headers=cls.HEADERS, timeout=cls.TIMEOUT)
            
            if response.status_code == 200:
                tags_text = response.text
                # Tags are returned as semicolon-separated key:value pairs
                for tag in tags_text.split(';'):
                    if ':' in tag:
                        key, value = tag.split(':', 1)
                        if key.strip().lower() == 'prolific_code':
                            return value.strip()
            
            # Default to 'ABCDEFG' if tag not found
            return None
        except Exception as e:
            logger.info(f"Error getting prolific code from Azure VM tags: {str(e)}")
            # Default to 'ABCDEFG' if we can't reach the metadata service or any other error occurs
            return None

    @classmethod
    def get_noconsent_code(cls, development_mode: bool, dev_noconsent_code: str = "NOCONSENT") -> str:
        """
        Get the noconsent_code from Azure VM tags using the Instance Metadata Service.
        In development mode, returns the dev_noconsent_code parameter.
        
        Args:
            development_mode: Whether running in development mode
            dev_noconsent_code: No consent code to use in development mode
        
        Returns:
            The no consent completion code, defaults to 'NOCONSENT' if not found
        """
        if development_mode:
            logger.info(f"Development mode: Using mocked no consent code: {dev_noconsent_code}")
            return dev_noconsent_code
        
        try:
            response = requests.get(cls.METADATA_URL_TAGS, headers=cls.HEADERS, timeout=cls.TIMEOUT)
            
            if response.status_code == 200:
                tags_text = response.text
                # Tags are returned as semicolon-separated key:value pairs
                for tag in tags_text.split(';'):
                    if ':' in tag:
                        key, value = tag.split(':', 1)
                        if key.strip().lower() == 'noconsent_code':
                            return value.strip()
            
            # Default to 'NOCONSENT' if tag not found
            return None
        except Exception as e:
            logger.info(f"Error getting no consent code from Azure VM tags: {str(e)}")
            # Default to 'NOCONSENT' if we can't reach the metadata service or any other error occurs
            return None
