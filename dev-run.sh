#!/bin/bash

# Development script for running the Flask app in development mode
# This script sets the necessary environment variables and starts the app

echo "Setting up development environment..."

# Export development mode environment variables
export DEVELOPMENT_MODE=true
export DEV_PARTICIPANT_ID=dev-participant
export DEV_STAGE=2
export SURVEY_URL=https://example.com/dev-survey
export UX_SURVEY_URL=https://example.com/dev-ux-survey
export GITHUB_ORG=LMU-Vibe-Coding-Study
export ASYNC_GITHUB_MODE=true
# Note: Set GITHUB_TOKEN in your .env file or export it manually for authentication

echo "Starting Flask app in development mode..."
echo "Participant ID will be mocked as: $DEV_PARTICIPANT_ID"
echo "Study stage will be mocked as: $DEV_STAGE"
echo "Repository will be cloned to current directory"
echo "Async GitHub mode: ${ASYNC_GITHUB_MODE:-enabled}"
if [ -z "$GITHUB_TOKEN" ]; then
    echo "Warning: GITHUB_TOKEN not set - will use public repository access only"
else
    echo "GitHub authentication configured for CodingStudyBot"
fi
echo ""

# Start the Flask application
python app.py
