#!/usr/bin/env python3
"""
Test script to verify the simplified stage determination logic.
This script tests the get_study_stage function that now uses Azure VM tags.
"""

import os
import sys
from unittest.mock import patch, MagicMock

# Add the current directory to the path to import services
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services import get_study_stage


def test_development_mode():
    """Test stage determination in development mode"""
    print("=" * 60)
    print("TESTING DEVELOPMENT MODE STAGE DETERMINATION")
    print("=" * 60)
    
    participant_id = "test-participant"
    
    # Test with default dev_stage (should be 1)
    print("\n1. Testing: Default dev_stage")
    stage = get_study_stage(participant_id, development_mode=True)
    print(f"   Result: Stage {stage} (Expected: 1)")
    assert stage == 1, f"Expected stage 1, got {stage}"
    
    # Test with explicit dev_stage=1
    print("\n2. Testing: Explicit dev_stage=1")
    stage = get_study_stage(participant_id, development_mode=True, dev_stage=1)
    print(f"   Result: Stage {stage} (Expected: 1)")
    assert stage == 1, f"Expected stage 1, got {stage}"
    
    # Test with explicit dev_stage=2
    print("\n3. Testing: Explicit dev_stage=2")
    stage = get_study_stage(participant_id, development_mode=True, dev_stage=2)
    print(f"   Result: Stage {stage} (Expected: 2)")
    assert stage == 2, f"Expected stage 2, got {stage}"
    
    print("\n✅ All development mode tests passed!")
    return True


def test_azure_vm_tags():
    """Test stage determination using mocked Azure VM tags"""
    print("\n" + "=" * 60)
    print("TESTING AZURE VM TAGS STAGE DETERMINATION")
    print("=" * 60)
    
    participant_id = "test-participant"
    
    # Test 1: Tag returns study_stage=1
    print("\n1. Testing: Azure VM tag study_stage=1")
    with patch('services.requests.get') as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "participant_id:test-participant;study_stage:1;environment:production"
        mock_get.return_value = mock_response
        
        stage = get_study_stage(participant_id, development_mode=False)
        print(f"   Result: Stage {stage} (Expected: 1)")
        assert stage == 1, f"Expected stage 1, got {stage}"
    
    # Test 2: Tag returns study_stage=2
    print("\n2. Testing: Azure VM tag study_stage=2")
    with patch('services.requests.get') as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "participant_id:test-participant;study_stage:2;environment:production"
        mock_get.return_value = mock_response
        
        stage = get_study_stage(participant_id, development_mode=False)
        print(f"   Result: Stage {stage} (Expected: 2)")
        assert stage == 2, f"Expected stage 2, got {stage}"
    
    # Test 3: Tag with invalid study_stage value (should default to 1)
    print("\n3. Testing: Invalid study_stage tag value")
    with patch('services.requests.get') as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "participant_id:test-participant;study_stage:invalid;environment:production"
        mock_get.return_value = mock_response
        
        stage = get_study_stage(participant_id, development_mode=False)
        print(f"   Result: Stage {stage} (Expected: 1 - default)")
        assert stage == 1, f"Expected stage 1 (default), got {stage}"
    
    # Test 4: No study_stage tag (should default to 1)
    print("\n4. Testing: Missing study_stage tag")
    with patch('services.requests.get') as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "participant_id:test-participant;environment:production"
        mock_get.return_value = mock_response
        
        stage = get_study_stage(participant_id, development_mode=False)
        print(f"   Result: Stage {stage} (Expected: 1 - default)")
        assert stage == 1, f"Expected stage 1 (default), got {stage}"
    
    # Test 5: Azure metadata service error (should default to 1)
    print("\n5. Testing: Azure metadata service error")
    with patch('services.requests.get') as mock_get:
        mock_get.side_effect = Exception("Connection error")
        
        stage = get_study_stage(participant_id, development_mode=False)
        print(f"   Result: Stage {stage} (Expected: 1 - default)")
        assert stage == 1, f"Expected stage 1 (default), got {stage}"
    
    # Test 6: Azure metadata service returns non-200 status (should default to 1)
    print("\n6. Testing: Azure metadata service non-200 status")
    with patch('services.requests.get') as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response
        
        stage = get_study_stage(participant_id, development_mode=False)
        print(f"   Result: Stage {stage} (Expected: 1 - default)")
        assert stage == 1, f"Expected stage 1 (default), got {stage}"
    
    print("\n✅ All Azure VM tags tests passed!")
    return True


def test_stage_determination():
    """Run all stage determination tests"""
    try:
        success1 = test_development_mode()
        success2 = test_azure_vm_tags()
        
        if success1 and success2:
            print("\n" + "=" * 60)
            print("🎉 ALL TESTS PASSED!")
            print("The simplified stage determination logic is working correctly.")
            print("=" * 60)
            return True
        else:
            print("\n❌ Some tests failed!")
            return False
            
    except Exception as e:
        print(f"\n❌ Test execution failed with error: {str(e)}")
        return False


if __name__ == "__main__":
    print("Simplified Stage Determination Test Script")
    print("This tests the get_study_stage function that uses Azure VM tags")
    print()
    
    success = test_stage_determination()
    sys.exit(0 if success else 1)
