from flask import Flask, send_from_directory
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(BASE_DIR)

app = Flask(__name__)

def serve_html(filename):
    filepath = os.path.join(PARENT_DIR, filename)
    if os.path.exists(filepath):
        return send_from_directory(PARENT_DIR, filename)
    return send_from_directory(BASE_DIR, filename)

# ─── HTML Page Routes ──────────────────────────────────────────────────────────

@app.route('/')
def index():
    return serve_html('final.html')

@app.route('/legacy')
def legacy():
    return serve_html('problem_blueprint_2898.html')

@app.route('/interactive')
def interactive():
    return serve_html('problem_blueprint_2898_inter.html')

@app.route('/interactive_2')
@app.route('/interactive2')
@app.route('/inter_2')
def interactive_2():
    return serve_html('problem_blueprint_2898_inter_2.html')

@app.route('/admin')
def admin():
    return serve_html('admin.html')

@app.route('/problem.html')
def problem():
    return serve_html('problem.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
