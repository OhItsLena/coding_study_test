#!/usr/bin/env python3
"""
Test script for ClipboardTracker functionality
"""

import os
import time
import tempfile
import json
from models.screen_recorder import ClipboardTracker

def test_clipboard_tracker():
    """Test ClipboardTracker functionality."""
    print("Testing ClipboardTracker...")
    
    # Create a temporary directory for logs
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"Using temporary directory: {temp_dir}")
        
        # Initialize ClipboardTracker
        tracker = ClipboardTracker(temp_dir, study_stage=1, poll_interval=0.5)
        
        # Start tracking
        tracker.start()
        print("Started clipboard tracking...")
        
        # Wait a moment for tracking to start
        time.sleep(1)
        
        # Simulate some clipboard changes by setting some text
        import pyperclip
        
        test_texts = [
            "Hello, World!",
            "This is a test clipboard content",
            "def hello():\n    print('Hello from code!')",
            "Another clipboard entry"
        ]
        
        for i, text in enumerate(test_texts):
            print(f"Setting clipboard text {i+1}: {text[:30]}...")
            pyperclip.copy(text)
            time.sleep(2)  # Wait for tracker to detect change
        
        # Stop tracking
        print("Stopping clipboard tracking...")
        tracker.stop()
        
        # Check if log file was created
        log_file = tracker.clipboard_log_path
        if os.path.exists(log_file):
            print(f"✅ Log file created: {log_file}")
            
            # Read and display the logged events
            with open(log_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            events = data.get('clipboard_events', [])
            print(f"✅ Logged {len(events)} clipboard events:")
            
            for i, event in enumerate(events):
                timestamp = event.get('timestamp', 'N/A')
                content_length = event.get('content_length', 0)
                content_preview = event.get('content', '')[:50]
                print(f"  Event {i+1}: {timestamp} - {content_length} chars - '{content_preview}...'")
        else:
            print("❌ Log file was not created")

if __name__ == "__main__":
    test_clipboard_tracker()
