# Minimal Flask App for Qualtrics Survey Link

This project is a simple Flask web application that displays a link to a Qualtrics survey.

## Setup

1. **Install dependencies:**
   ```sh
   pip install -r requirements.txt
   ```

2. **Configure environment variables:**
   ```sh
   cp .env.example .env
   ```
   Then edit `.env` and set your survey URL:
   ```
   SURVEY_URL=https://your-actual-survey-url.com
   ```

## How to Run

1. **Start the Flask app:**
   ```sh
   python app.py
   ```
2. **Open your browser and go to:**
   [http://127.0.0.1:8085/](http://127.0.0.1:8085/)

You will see a page with a link to the Qualtrics survey.
