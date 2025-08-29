# Coding Study Tool

A Flask-based web application for orchestrating coding studies. This includes data management and guiding participants through the study flow. 

## Project Structure

- `app.py` - Main Flask application
- `services.py` - Core business logic and services
- `models/` - Data models and service classes
- `templates/` - Jinja2 HTML templates
- `static/` - Static assets (CSS, JS, images)
- `logs/` - Application logs
- `vm-tools/` - Scripts that are copied to and run on the VM instances
- `task_requirements.json` - Task definitions and requirements
- `tutorials.json` - Tutorial content and configurations
- `exportInformedConsent.json` - Informed consent configuration

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/OhItsLena/coding_study_test.git
   cd coding_study_test_tool
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Development

To run the application in development mode:

```bash
./dev-run.sh
```

This script will:
- Set up development environment variables. *Change the configuration as needed for your local setup.*
- Mock participant data for testing
- Start the Flask development server with debug mode enabled
- Make the app available at `http://localhost:39765`

## Production

To run the application in production:
1. Create a `.env` file in the project root with the following variables:
   ```env
   GITHUB_TOKEN=your_github_personal_access_token
   GITHUB_ORG=your_github_organization
   SURVEY_URL=https://your-survey-platform.com/survey
   UX_SURVEY_URL=https://your-survey-platform.com/ux-survey
   ```
Use the `.env.example` file as a reference to create your own `.env` file.

2. Start the application:
   ```bash
   python app.py
   ```

For production deployment, consider using a WSGI server like Gunicorn:
```bash
gunicorn -w 4 -b 0.0.0.0:39765 app:app
```

## Functionality
The app provides the following key functionalities:
- Guide participants through the study flow (welcome, background survey, tutorial, task, post-coding survey, goodbye)
- Handle different study stages and coding conditions
- Read participant configuration from Azure VM tags
- Start screen recording (OBS Studio integration) on startup and stop on goodbye. Push to Azure Blob Storage.
- Record clipboard content and focus switches
- Extract GitHub Copilot logs from VSC telemetry data
- Save all tutorial code, task code, and logs to individual GitHub repository of the participant (needs to be set up beforehand)