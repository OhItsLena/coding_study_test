#!/bin/bash

# Development script for running the Flask app in development mode
# This script sets the necessary environment variables and starts the app

echo "Setting up development environment..."

# Export development mode environment variables
export DEVELOPMENT_MODE=true
export DEV_PARTICIPANT_ID=dev-participant
export SURVEY_URL=https://example.com/dev-survey
export UX_SURVEY_URL=https://example.com/dev-ux-survey

echo "Starting Flask app in development mode..."
echo "Participant ID will be mocked as: $DEV_PARTICIPANT_ID"
echo "Repository will be cloned to current directory"
echo ""

# Start the Flask application
python app.py
