import os
import requests
from flask import Flask, render_template_string
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

def get_participant_id():
    """
    Get the participant_id from Azure VM tags using the Instance Metadata Service.
    Returns the participant_id if found, otherwise returns a default message.
    """
    try:
        # Azure Instance Metadata Service endpoint for tags
        metadata_url = "http://169.254.169.254/metadata/instance/compute/tags?api-version=2021-02-01&format=text"
        headers = {'Metadata': 'true'}
        
        # Set a short timeout since this is a local metadata service
        response = requests.get(metadata_url, headers=headers, timeout=5)
        
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

@app.route('/')
def home():
    participant_id = get_participant_id()
    survey_url = os.getenv('SURVEY_URL', '#')
    
    if survey_url == '#':
        return render_template_string('''
            <!DOCTYPE html>
            <html>
            <head>
                <title>{{ participant_id }} - Background Survey</title>
            </head>
            <body>
                <h1>Background Survey - {{ participant_id }}</h1>
                <p style="color: red;">Survey URL not configured. Please set the SURVEY_URL environment variable.</p>
            </body>
            </html>
        ''', participant_id=participant_id)
    
    return render_template_string('''
        <!DOCTYPE html>
        <html>
        <head>
            <title>{{ participant_id }} - Background Survey</title>
        </head>
        <body>
            <h1>Background Survey - {{ participant_id }}</h1>
            <a href="{{ url }}" target="_blank">Start Survey</a>
        </body>
        </html>
    ''', participant_id=participant_id, url=survey_url)

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8085)