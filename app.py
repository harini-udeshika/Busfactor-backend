from flask import Flask, jsonify, request
from flask_cors import CORS
from flask import send_from_directory
import requests
import os
import time
from dotenv import load_dotenv

from flask_socketio import SocketIO, emit  # Don't rename SocketIO
from generate_graphs import generateGraphSet
# from optimised_app import generateGraphSet
from rapidfuzz import fuzz



app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'

# Enable CORS
CORS(app, resources={r"/*": {"origins": "*"}})

# Initialize SocketIO
socketio = SocketIO(app, cors_allowed_origins="*")

# GitHub token and base directory

load_dotenv()
token =os.getenv('GITHUB_TOKEN')

@app.route("/repo_data", methods=["POST"])
def get_repo_data():
    data = request.get_json()  # Parse JSON body
    url = data.get("url", "").strip() if data else ""
    print(f"Received URL: {url}")
    
    # Validate the URL
    if not url:
        return jsonify({"error": "URL is required"}), 400
    
    if not url.startswith("https://github.com/"):
        return jsonify({"error": "Invalid URL. It must start with 'https://github.com/'."}), 400

    # Convert GitHub URL to API URL
    repo_api_url = url.replace('https://github.com/', 'https://api.github.com/repos/')
    print(f"Repo API URL: {repo_api_url}")
    
    headers = {
        'Authorization': f'token {token}'
    }
    
    try:
        response = requests.get(repo_api_url, headers=headers)
        response.raise_for_status()  # Raise an HTTPError for bad responses (4xx and 5xx)
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
        return jsonify({"error": str(e)}), 500
    repo = response.json()
    extracted_data = []
    extracted_data.append({
        "full_name": repo["full_name"],
        "url": repo["html_url"],
        "topics": repo.get("topics", []),  # Use `.get()` to avoid KeyError if "topics" is missing
        "forks_count": repo["forks_count"],
        "stargazers_count": repo["stargazers_count"],
        "description": repo["description"],
        "language": repo["language"],
        "avatar_url": repo.get("owner", {}).get("avatar_url"),  # Safely access nested keys
    })

    # Return the list as JSON
    return jsonify(extracted_data)

    # If the request is successful, return the repository data
    return jsonify(response.json())



@app.route("/search", methods=["GET"])
def search_repositories():
    value = request.args.get("value", "").strip().lower()
    if not value:
        return jsonify([])

    response = requests.get(
        "https://api.github.com/search/repositories",
        headers={"Authorization": f"token {token}"},
        params={"q": value},
    )

    if response.status_code != 200:
        return jsonify({"error": "Failed to fetch data from GitHub"}), response.status_code

    repos = response.json().get("items", [])
    filtered_repos = []

    for repo in repos:
        full_name = repo["full_name"].lower()
        # Fuzzy match using a threshold
        match_score = fuzz.partial_ratio(value, full_name)
        if match_score >= 80:  # Set a threshold for match quality
            filtered_repos.append(
                {
                    "full_name": repo["full_name"],
                    "url": repo["html_url"],
                    "topics": repo["topics"],
                    "forks_count": repo["forks_count"],
                    "stargazers_count": repo["stargazers_count"],
                    "description": repo["description"],
                    "language": repo["language"],
                    "avatar_url": repo.get("owner", {}).get('avatar_url'),
                    "match_score": match_score,  # Optionally include the score for debugging
                }
            )

    # Sort by match quality (optional)
    filtered_repos.sort(key=lambda x: x["match_score"], reverse=True)

    return jsonify(filtered_repos)

@socketio.on('connect', namespace='/progress')
def handle_connect():
    print("Client connected to /progress namespace")

@app.route("/generate_graphs", methods=["POST"])
def generate_graphs():
    data = request.get_json()
    repo_url = data.get("url", "").strip()

    if not repo_url:
        return jsonify({"error": "Repository URL required"}), 400

    def send_progress(message):
        print(f"Emitting progress: {message}")
        socketio.emit('progress', {'message': message}, namespace='/progress')
        socketio.sleep(0)  # Allow event loop to process


    try:
        send_progress("Starting graph generation...")
        graphs = generateGraphSet(repo_url, send_progress)
        send_progress("Graph generation complete!")
        print('graphs')
        print(graphs)
        return jsonify(graphs)
    except Exception as e:
        send_progress(f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    socketio.run(app, debug=True)
