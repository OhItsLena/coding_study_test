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
   GITHUB_TOKEN=your-github-personal-access-token
   GITHUB_ORG=LMU-Vibe-Coding-Study
   ```

3. **Set up GitHub authentication (recommended):**
   - Create a GitHub Personal Access Token for your CodingStudyBot account
   - Grant the token `repo` permissions for accessing private repositories
   - Add the token to your `.env` file as `GITHUB_TOKEN`
   - This enables automatic pushing of participant code changes to remote repositories

## Development Mode

For local development and testing, you can enable development mode by setting environment variables:

1. **Enable development mode in your `.env` file:**
   ```
   DEVELOPMENT_MODE=true
   DEV_PARTICIPANT_ID=dev-participant-001
   DEV_STAGE=1
   ```

2. **In development mode, the application will:**
   - Use a mocked participant ID instead of querying Azure metadata
   - Use a mocked study stage instead of querying Azure VM tags
   - Clone repositories to the current project directory instead of `~/workspace/`
   - Display clear indicators that development mode is active

3. **Run the app in development mode:**
   ```sh
   # Option 1: Use the development script
   ./dev-run.sh
   
   # Option 2: Set environment variables manually and run
   export DEVELOPMENT_MODE=true
   export DEV_PARTICIPANT_ID=dev-participant-001
   export DEV_STAGE=1
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
- Automatically commit and push code changes using GitHub authentication
- Display a personalized page with the background survey link
- Guide the participant through the study flow

## GitHub Authentication

The tool supports GitHub authentication via HTTPS URLs with embedded tokens. This enables:

- **Automatic repository cloning**: Private repositories can be cloned using the CodingStudyBot account
- **Automatic code pushing**: Participant code changes are automatically committed and pushed to the remote repository
- **Secure authentication**: Uses GitHub Personal Access Tokens for secure, token-based authentication

### Setting up GitHub Authentication

1. Create a GitHub Personal Access Token for your CodingStudyBot account:
   - Go to GitHub Settings > Developer settings > Personal access tokens
   - Generate a new token with `repo` scope for full repository access
   - Copy the token (you won't be able to see it again)

2. Add the token to your `.env` file:
   ```
   GITHUB_TOKEN=ghp_your_token_here
   GITHUB_ORG=LMU-Vibe-Coding-Study
   ```

3. The application will automatically use authenticated URLs like:
   ```
   https://ghp_your_token_here@github.com/LMU-Vibe-Coding-Study/study-participant-001.git
   ```

4. **Test your authentication** (optional but recommended):
   ```sh
   python test_github_auth.py
   ```
   This script will verify that your token works and can access the expected repositories.

**Note**: If no token is provided, the application will fall back to public HTTPS URLs and only perform local commits without pushing to remote repositories.

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
