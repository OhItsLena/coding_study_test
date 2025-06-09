from flask import Flask, render_template_string

app = Flask(__name__)

@app.route('/')
def home():
    return render_template_string('''
        <h1>Background Survey</h1>
        <a href="https://qualtricsxmgsl5ph9b2.qualtrics.com/jfe/form/SV_0q4OEpRIksX2pRI" target="_blank">Start Survey</a>
    ''')

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8085)