# Vibe Coding vs. AI-Assisted Coding Study Tool

This project is a Flask web application designed to guide participants through a longitudinal study comparing "vibe coding" (intuitive programming) with AI-assisted coding approaches. The tool manages participant flow, handles study materials, and provides survey links throughout the study process.

## Study Design

This tool implements a virtual longitudinal between-subject (2 x 1h) study design that includes:

- **Background questionnaire**: Collects participant demographics and programming experience
- **Coding condition tutorial**: Provides an introduction to the assigned coding condition
- **Coding tasks**: Two separate coding sessions with different methodologies
- **Experience questionnaires**: Post-task feedback collection

The study flow is carefully orchestrated to ensure consistent participant experience while collecting both quantitative performance data and qualitative feedback.

## Features

- **Participant identification**: Automatically retrieves participant IDs from Azure VM metadata
- **Repository management**: Clones participant-specific GitHub repositories for coding tasks
- **Survey integration**: Provides seamless links to Qualtrics background surveys
- **Study flow guidance**: Ensures participants follow the correct sequence of activities

## Setup

1. **Install dependencies:**
   ```sh
   pip install -r requirements.txt
   ```

2. **Configure environment variables:**
   ```sh
   cp .env.example .env
   ```
   Then edit `.env` and configure your settings:
   ```
   SURVEY_URL=https://your-qualtrics-survey-url.com
   DEVELOPMENT_MODE=false
   DEV_PARTICIPANT_ID=dev-participant-001
   ```

## Development Mode

For local development and testing, you can enable development mode by setting environment variables:

1. **Enable development mode in your `.env` file:**
   ```
   DEVELOPMENT_MODE=true
   DEV_PARTICIPANT_ID=dev-participant-001
   ```

2. **In development mode, the application will:**
   - Use a mocked participant ID instead of querying Azure metadata
   - Clone repositories to the current project directory instead of `~/workspace/`
   - Display clear indicators that development mode is active

3. **Run the app in development mode:**
   ```sh
   # Option 1: Use the development script
   ./dev-run.sh
   
   # Option 2: Set environment variables manually and run
   export DEVELOPMENT_MODE=true
   export DEV_PARTICIPANT_ID=dev-participant-001
   python app.py
   ```
   You'll see development mode indicators in the console output.

## How to Run

1. **Start the Flask app:**
   ```sh
   python app.py
   ```
2. **Open your browser and go to:**
   [http://127.0.0.1:8085/](http://127.0.0.1:8085/)

The application will:
- Automatically detect the participant ID from Azure VM metadata
- Clone the participant's study repository to `~/workspace/study-{participant_id}`
- Display a personalized page with the background survey link
- Guide the participant through the study flow

## Technical Details

### Participant Management
- Participant IDs are retrieved from Azure VM instance metadata tags
- Each participant gets a dedicated GitHub repository: `study-{participant_id}`
- Repositories are automatically cloned to the participant's workspace

### Study Repository Structure
The tool expects participant repositories to follow the naming convention:
```
https://github.com/LMU-Vibe-Coding-Study/study-{participant_id}
```

## Development

This is a minimal Flask application following best practices:
- Simple, readable code structure
- Environment variable configuration
- Cross-platform compatibility
- Robust error handling
