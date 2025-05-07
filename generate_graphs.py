import git
import math
import networkx as nx
import tempfile
import shutil
import re
from collections import defaultdict
from datetime import datetime, timedelta
from github import Github
import numpy as np
import community as community_louvain  # For community detection (pip install python-louvain)
from networkx.algorithms import community as nx_community
from concurrent.futures import ThreadPoolExecutor, as_completed
import os
import time
from dotenv import load_dotenv
import requests
import logging
import random

from graph_to_json import graph_to_json

# --- Set Up Logging ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("jira_activity.log"),  # Logs written to file.
        logging.StreamHandler()  # Also log to console.
    ]
)

# --- Jira Integration Helper Functions ---

# Original function . 

# def fetch_jira_issues(jira_server, project_key, auth):
#     """
#     Fetches issues from Jira for a given project updated in the last 1.5 years.
#     """
#     cutoff_date = (datetime.utcnow() - timedelta(days=547)).strftime("%Y-%m-%d")
#     jql = f"project = {project_key} AND updated >= '{cutoff_date}'"
#     url = f"{jira_server}/rest/api/2/search"
#     params = {
#         "jql": jql,
#         "fields": "reporter,assignee,comment"
#     }
#     response = requests.get(url, auth=auth, params=params)
#     response.raise_for_status()
#     data = response.json()
#     return data.get("issues", [])



# # Simulated function for testing purposes -equal contribution test
def fetch_jira_issues(jira_server, project_key, auth):
    """
    Simulated Jira Issues for 7 Contributors (Equal Contributions Scenario)
    """
    contributors = ["Alice", "Bob", "Charlie", "Dana", "Eve", "Frank", "Grace"]
    simulated_issues = []

    # Each contributor reports and assigns issues
    for reporter in contributors:
        for assignee in contributors:
            if reporter != assignee:
                simulated_issues.append({
                    "fields": {
                        "reporter": {"displayName": reporter},
                        "assignee": {"displayName": assignee},
                        "comment": {
                            "comments": [
                                {"author": {"displayName": random.choice(contributors)}},
                                {"author": {"displayName": random.choice(contributors)}},
                                {"author": {"displayName": random.choice(contributors)}},
                            ]
                        }
                    }
                })

    return simulated_issues

# #  skewed # --- Jira Integration ---
# def fetch_jira_issues(jira_server, project_key, auth):
#     """
#     Hardcoded Jira Simulation for Skewed Contributions (7 Contributors, Charlie 9 issues)
#     """

#     simulated_issues = [
#         # --- Alice-heavy activity ---
#         {"fields": {
#             "reporter": {"displayName": "Alice"},
#             "assignee": {"displayName": "Bob"},
#             "comment": {"comments": [
#                 {"author": {"displayName": "Alice"}},
#                 {"author": {"displayName": "Alice"}},
#                 {"author": {"displayName": "Bob"}},
#             ]}
#         }},
#         {"fields": {
#             "reporter": {"displayName": "Alice"},
#             "assignee": {"displayName": "Charlie"},
#             "comment": {"comments": [
#                 {"author": {"displayName": "Alice"}},
#                 {"author": {"displayName": "Dana"}},
#             ]}
#         }},
#         {"fields": {
#             "reporter": {"displayName": "Alice"},
#             "assignee": {"displayName": "Eve"},
#             "comment": {"comments": [
#                 {"author": {"displayName": "Alice"}},
#             ]}
#         }},
#         {"fields": {
#             "reporter": {"displayName": "Alice"},
#             "assignee": {"displayName": "Frank"},
#             "comment": {"comments": [
#                 {"author": {"displayName": "Alice"}},
#                 {"author": {"displayName": "Grace"}},
#             ]}
#         }},
#         # --- Bob moderate activity ---
#         {"fields": {
#             "reporter": {"displayName": "Bob"},
#             "assignee": {"displayName": "Charlie"},
#             "comment": {"comments": [
#                 {"author": {"displayName": "Bob"}},
#                 {"author": {"displayName": "Alice"}},
#             ]}
#         }},
#         {"fields": {
#             "reporter": {"displayName": "Bob"},
#             "assignee": {"displayName": "Dana"},
#             "comment": {"comments": [
#                 {"author": {"displayName": "Bob"}},
#             ]}
#         }},
#         # --- Charlie 9 issues ---
#         {"fields": {
#             "reporter": {"displayName": "Charlie"},
#             "assignee": {"displayName": "Dana"},
#             "comment": {"comments": [
#                 {"author": {"displayName": "Charlie"}},
#             ]}
#         }},
#         {"fields": {
#             "reporter": {"displayName": "Charlie"},
#             "assignee": {"displayName": "Eve"},
#             "comment": {"comments": [
#                 {"author": {"displayName": "Charlie"}},
#             ]}
#         }},
#         {"fields": {
#             "reporter": {"displayName": "Charlie"},
#             "assignee": {"displayName": "Frank"},
#             "comment": {"comments": [
#                 {"author": {"displayName": "Charlie"}},
#             ]}
#         }},
#         {"fields": {
#             "reporter": {"displayName": "Charlie"},
#             "assignee": {"displayName": "Grace"},
#             "comment": {"comments": [
#                 {"author": {"displayName": "Charlie"}},
#             ]}
#         }},
#         {"fields": {
#             "reporter": {"displayName": "Charlie"},
#             "assignee": {"displayName": "Alice"},
#             "comment": {"comments": [
#                 {"author": {"displayName": "Charlie"}},
#             ]}
#         }},
#         {"fields": {
#             "reporter": {"displayName": "Charlie"},
#             "assignee": {"displayName": "Bob"},
#             "comment": {"comments": [
#                 {"author": {"displayName": "Charlie"}},
#             ]}
#         }},
#         {"fields": {
#             "reporter": {"displayName": "Charlie"},
#             "assignee": {"displayName": "Dana"},
#             "comment": {"comments": [
#                 {"author": {"displayName": "Charlie"}},
#             ]}
#         }},
#         {"fields": {
#             "reporter": {"displayName": "Charlie"},
#             "assignee": {"displayName": "Eve"},
#             "comment": {"comments": [
#                 {"author": {"displayName": "Charlie"}},
#             ]}
#         }},
#         {"fields": {
#             "reporter": {"displayName": "Charlie"},
#             "assignee": {"displayName": "Frank"},
#             "comment": {"comments": [
#                 {"author": {"displayName": "Charlie"}},
#             ]}
#         }},
#         # --- Very light activity by others ---
#         {"fields": {
#             "reporter": {"displayName": "Dana"},
#             "assignee": {"displayName": "Frank"},
#             "comment": {"comments": [
#                 {"author": {"displayName": "Dana"}},
#             ]}
#         }},
#         {"fields": {
#             "reporter": {"displayName": "Eve"},
#             "assignee": {"displayName": "Grace"},
#             "comment": {"comments": [
#                 {"author": {"displayName": "Eve"}},
#             ]}
#         }},
#         {"fields": {
#             "reporter": {"displayName": "Frank"},
#             "assignee": {"displayName": "Alice"},
#             "comment": {"comments": [
#                 {"author": {"displayName": "Frank"}},
#             ]}
#         }},
#         {"fields": {
#             "reporter": {"displayName": "Grace"},
#             "assignee": {"displayName": "Bob"},
#             "comment": {"comments": [
#                 {"author": {"displayName": "Grace"}},
#             ]}
#         }},
#     ]

#     return simulated_issues

# # Mixed activity jira
# def fetch_jira_issues(jira_server, project_key, auth):
#     """
#     Hardcoded Jira Simulation for Mixed Activity (7 Contributors)
#     Alice and Eve have 5 issues each, equal contributions
#     """

#     simulated_issues = [
#         # --- Alice steady activity (5 issues) ---
#         {"fields": {
#             "reporter": {"displayName": "Alice"},
#             "assignee": {"displayName": "Bob"},
#             "comment": {"comments": [
#                 {"author": {"displayName": "Alice"}},
#                 {"author": {"displayName": "Eve"}},
#             ]}
#         }},
#         {"fields": {
#             "reporter": {"displayName": "Alice"},
#             "assignee": {"displayName": "Charlie"},
#             "comment": {"comments": [
#                 {"author": {"displayName": "Alice"}},
#             ]}
#         }},
#         {"fields": {
#             "reporter": {"displayName": "Alice"},
#             "assignee": {"displayName": "Dana"},
#             "comment": {"comments": [
#                 {"author": {"displayName": "Eve"}},
#             ]}
#         }},
#         {"fields": {
#             "reporter": {"displayName": "Alice"},
#             "assignee": {"displayName": "Frank"},
#             "comment": {"comments": [
#                 {"author": {"displayName": "Alice"}},
#             ]}
#         }},
#         {"fields": {
#             "reporter": {"displayName": "Alice"},
#             "assignee": {"displayName": "Grace"},
#             "comment": {"comments": [
#                 {"author": {"displayName": "Eve"}},
#             ]}
#         }},
        
#         # --- Eve steady activity (5 issues) ---
#         {"fields": {
#             "reporter": {"displayName": "Eve"},
#             "assignee": {"displayName": "Frank"},
#             "comment": {"comments": [
#                 {"author": {"displayName": "Eve"}},
#                 {"author": {"displayName": "Alice"}},
#             ]}
#         }},
#         {"fields": {
#             "reporter": {"displayName": "Eve"},
#             "assignee": {"displayName": "Grace"},
#             "comment": {"comments": [
#                 {"author": {"displayName": "Eve"}},
#             ]}
#         }},
#         {"fields": {
#             "reporter": {"displayName": "Eve"},
#             "assignee": {"displayName": "Bob"},
#             "comment": {"comments": [
#                 {"author": {"displayName": "Alice"}},
#             ]}
#         }},
#         {"fields": {
#             "reporter": {"displayName": "Eve"},
#             "assignee": {"displayName": "Charlie"},
#             "comment": {"comments": [
#                 {"author": {"displayName": "Eve"}},
#             ]}
#         }},
#         {"fields": {
#             "reporter": {"displayName": "Eve"},
#             "assignee": {"displayName": "Dana"},
#             "comment": {"comments": [
#                 {"author": {"displayName": "Alice"}},
#             ]}
#         }},
        
#         # --- Bob bursty activity ---
#         {"fields": {
#             "reporter": {"displayName": "Bob"},
#             "assignee": {"displayName": "Alice"},
#             "comment": {"comments": [
#                 {"author": {"displayName": "Bob"}},
#                 {"author": {"displayName": "Frank"}},
#                 {"author": {"displayName": "Bob"}},
#             ]}
#         }},
#         {"fields": {
#             "reporter": {"displayName": "Bob"},
#             "assignee": {"displayName": "Grace"},
#             "comment": {"comments": [
#                 {"author": {"displayName": "Bob"}},
#                 {"author": {"displayName": "Charlie"}},
#             ]}
#         }},
        
#         # --- Charlie occasional large activity ---
#         {"fields": {
#             "reporter": {"displayName": "Charlie"},
#             "assignee": {"displayName": "Frank"},
#             "comment": {"comments": [
#                 {"author": {"displayName": "Charlie"}},
#             ]}
#         }},
#         {"fields": {
#             "reporter": {"displayName": "Charlie"},
#             "assignee": {"displayName": "Bob"},
#             "comment": {"comments": [
#                 {"author": {"displayName": "Charlie"}},
#             ]}
#         }},
        
#         # --- Dana irregular activity ---
#         {"fields": {
#             "reporter": {"displayName": "Dana"},
#             "assignee": {"displayName": "Grace"},
#             "comment": {"comments": [
#                 {"author": {"displayName": "Dana"}},
#             ]}
#         }},
        
#         # --- Frank bursty issues ---
#         {"fields": {
#             "reporter": {"displayName": "Frank"},
#             "assignee": {"displayName": "Charlie"},
#             "comment": {"comments": [
#                 {"author": {"displayName": "Frank"}},
#             ]}
#         }},
#         {"fields": {
#             "reporter": {"displayName": "Frank"},
#             "assignee": {"displayName": "Eve"},
#             "comment": {"comments": [
#                 {"author": {"displayName": "Frank"}},
#             ]}
#         }},
        
#         # --- Grace minimal activity ---
#         {"fields": {
#             "reporter": {"displayName": "Grace"},
#             "assignee": {"displayName": "Dana"},
#             "comment": {"comments": [
#                 {"author": {"displayName": "Grace"}},
#             ]}
#         }},
#     ]

#     return simulated_issues



def calculate_jira_activity(issues):
    """
    Calculates a simple Jira activity score for each user:
      - +1 for being the reporter
      - +1 for being the assignee
      - +1 for each comment made
    Usernames are normalized for consistency.
    """
    jira_activity = defaultdict(int)

    def normalize(name):
        return re.sub(r"[^a-zA-Z0-9]", "", name).lower()

    for issue in issues:
        fields = issue.get("fields", {})
        # Reporter
        reporter = fields.get("reporter")
        if reporter and reporter.get("displayName"):
            jira_activity[normalize(reporter["displayName"])] += 1
        # Assignee
        assignee = fields.get("assignee")
        if assignee and assignee.get("displayName"):
            jira_activity[normalize(assignee["displayName"])] += 1
        # Comments
        comments = fields.get("comment", {}).get("comments", [])
        for comment in comments:
            author = comment.get("author")
            if author and author.get("displayName"):
                jira_activity[normalize(author["displayName"])] += 1

    logging.info("Calculated Jira Activity Data: %s", dict(jira_activity))
    return jira_activity


def add_file_sizes(repo, filtered_unique_files):
    file_sizes = {}

    for contributor, files in filtered_unique_files.items():
        contributor_files = {}
        for file in files:
            try:
                file_blob = repo.tree()[file]
                content = file_blob.data_stream.read().decode("utf-8")
                loc = content.count("\n") + 1  # Count lines
                contributor_files[file] = loc
            except Exception as e:
                logging.error("Error processing file %s: %s", file, e)
                contributor_files[file] = None
        file_sizes[contributor] = contributor_files

    return file_sizes

def calculate_contribution_percentages(all_files_with_sizes, files_per_contributor_with_sizes):
    for contributor, files in files_per_contributor_with_sizes.items():
        for file_path, lines_changed in files.items():
            total_size = all_files_with_sizes.get(file_path, 0)
            if total_size > 0:
                contribution_percentage = (lines_changed / total_size) * 100
            else:
                contribution_percentage = 0
            files_per_contributor_with_sizes[contributor][file_path] = round(contribution_percentage, 2)


def generateGraphSet(repo_url, send_progress):


    # Extract repository name from URL
    repo_name = repo_url.split("/")[-2] + "/" + repo_url.split("/")[-1].replace(".git", "")
    GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
    if GITHUB_TOKEN:
        logging.info("GitHub token fetched successfully.")
    else:
        logging.error("GitHub token not found. Ensure it's set as an environment variable.")

    load_dotenv()
    g = Github(GITHUB_TOKEN)

    send_progress("Cloning repository...")
    temp_dir = tempfile.mkdtemp()
    auth_repo_url = repo_url.replace("https://", f"https://{GITHUB_TOKEN}@")
    repo = git.Repo.clone_from(auth_repo_url, temp_dir, bare=True)
    send_progress("Repository cloned!")

    github_repo = g.get_repo(repo_name)
    contributor_data = {}
    email_to_username = {}
    name_to_username = {}

    send_progress("Fetch all contributors for the project...")
    contributors = github_repo.get_contributors()
    contributors_list = list(contributors)
    i = 0
    tot = len(contributors_list)
    for contributor in contributors:
        i += 1
        percentage = math.ceil((i / tot) * 100)
        send_progress(f"Fetch all contributors...{percentage}%")
        username = contributor.login
        contributor_data[username] = {
            "type": contributor.type,
            "normalized_name": re.sub(r"[^a-zA-Z0-9]", "", username).lower(),
        }
        if contributor.email:
            email_to_username[contributor.email] = username
        elif contributor.name:
            name_to_username[contributor.name] = username

    def get_normalized_username(username):
        return re.sub(r"[^a-zA-Z0-9]", "", username).lower()

    def is_bot(username):
        user_info = contributor_data.get(username)
        if user_info and user_info["type"] == "Bot":
            return True
        if "bot" in username.lower():
            return True
        return False

    most_recent_commit = next(repo.iter_commits())
    cutoff_date = most_recent_commit.committed_datetime - timedelta(days=547)

    send_progress("Calculate LOC and file diversity...")
    commits_data = []
    loc_per_contributor = defaultdict(int)
    unique_files_per_contributor = defaultdict(set)
    files_per_contributor_with_sizes = defaultdict(lambda: defaultdict(int))
    all_files_with_sizes = {}
    commits_list = list(repo.iter_commits())
    tot = len(commits_list)
    j = 0
    for commit in commits_list:
        j += 1
        percentage = math.ceil((j / tot) * 100)
        send_progress(f"Calculate LOC and file diversity...{percentage}%")
        if commit.committed_datetime < cutoff_date:
            break

        author_username = (email_to_username.get(commit.author.email)
                           or name_to_username.get(commit.author.name)
                           or commit.author.name)
        normalized_username = get_normalized_username(author_username)
        total_lines_changed = commit.stats.total["insertions"] + commit.stats.total["deletions"]
        loc_per_contributor[normalized_username] += total_lines_changed
        unique_files_per_contributor[normalized_username].update(commit.stats.files.keys())
        for file_path, file_stats in commit.stats.files.items():
            file_size = file_stats.get("lines", 0)
            all_files_with_sizes[file_path] = all_files_with_sizes.get(file_path, 0) + file_size
            files_per_contributor_with_sizes[normalized_username][file_path] += file_size
        commits_data.append({
            "datetime": commit.committed_datetime,
            "author_name": author_username,
            "author_email": commit.author.email,
            "files": list(commit.stats.files.keys()),
        })

    send_progress("Generating graphs")
    G = nx.Graph()
    contributor_map = defaultdict(set)
    file_contributors = defaultdict(set)

    send_progress("Processing commits...")
    for commit in commits_data:
        username = commit["author_name"]
        if is_bot(username):
            continue
        normalized_username = get_normalized_username(username)
        contributor_map[normalized_username].add((username, commit["author_email"]))
        for file in commit["files"]:
            file_contributors[file].add(normalized_username)

    send_progress("Creating graph nodes for each unique contributor group...")
    unique_contributors = {}
    for norm_name, variations in contributor_map.items():
        representative = next(iter(variations))[0]
        unique_contributors[norm_name] = representative
        G.add_node(representative)

    send_progress("Adding edges based on shared file contributions...")
    for file, contributors in file_contributors.items():
        contributors_list = list(contributors)
        for i in range(len(contributors_list)):
            for j in range(i + 1, len(contributors_list)):
                contributor_1 = unique_contributors[contributors_list[i]]
                contributor_2 = unique_contributors[contributors_list[j]]
                if G.has_edge(contributor_1, contributor_2):
                    G[contributor_1][contributor_2]["weight"] += 1
                else:
                    G.add_edge(contributor_1, contributor_2, weight=1)

    send_progress("Calculating custom centrality scores for each contributor...")
    custom_centrality = {}
    degree_centrality = nx.degree_centrality(G)
    for contributor in G.nodes():
        norm_name = get_normalized_username(contributor)
        total_loc = loc_per_contributor[norm_name]
        file_count = len(unique_files_per_contributor[norm_name])
        custom_centrality[contributor] = (
            degree_centrality[contributor]
            + (0.5 * total_loc / max(loc_per_contributor.values()))
            + (0.5 * file_count / max(len(files) for files in unique_files_per_contributor.values()))
        )

    # --- Jira Integration ---
    send_progress("Fetching Jira issues...")
    # Using environment variables from your test sample
    jira_server = os.getenv("JIRA_SERVER")
    jira_project_key = os.getenv("JIRA_PROJECT_KEY")
    jira_email = os.getenv("JIRA_EMAIL")
    jira_api_token = os.getenv("JIRA_API_TOKEN")
    jira_auth = (jira_email, jira_api_token)
    
    try:
        issues = fetch_jira_issues(jira_server, jira_project_key, jira_auth)
        jira_activity = calculate_jira_activity(issues)
        send_progress("Jira data fetched and processed!")
    except Exception as e:
        send_progress(f"Error fetching Jira data: {e}")
        logging.error("Error fetching Jira data: %s", e)
        jira_activity = {}

    # Define separate weights
    jira_weight = 0.2       # for GitHub contributors that have Jira activity
    jira_only_weight = 0.1  # for contributors that exist only in Jira

    # Update centrality for GitHub contributors (nodes already in the graph)
    for contributor in G.nodes():
        norm_name = get_normalized_username(contributor)
        jira_score = jira_activity.get(norm_name, 0)
        custom_centrality[contributor] += jira_weight * jira_score
        logging.info("Contributor: %s | Normalized: %s | Jira Score: %d | Updated Centrality: %.2f",
                     contributor, norm_name, jira_score, custom_centrality[contributor])

    # Now add Jira-only contributors as new nodes
    for jira_contrib, score in jira_activity.items():
        # Check if there's any node in G whose normalized name matches jira_contrib
        exists = False
        for node in G.nodes():
            if get_normalized_username(node) == jira_contrib:
                exists = True
                break
        if not exists:
            # Add this jira-only contributor as a new node.
            # Here, we use the normalized name as the node label;
            new_node = jira_contrib
            G.add_node(new_node, jira_only=True)
            custom_centrality[new_node] = jira_only_weight * score
            logging.info("Added JIRA-only node: %s | Jira Score: %d | Custom Centrality: %.2f",
                         new_node, score, custom_centrality[new_node])

    # Determine key contributors (Key Developers)
    sorted_nodes = sorted(custom_centrality.items(), key=lambda item: item[1], reverse=True)
    threshold_percentage = 0.3
    total_centrality_sum = sum(custom_centrality.values())
    cumulative_sum = 0
    top_k_nodes = []
    for node, centrality_value in sorted_nodes:
        cumulative_sum += centrality_value
        top_k_nodes.append(node)
        if cumulative_sum >= threshold_percentage * total_centrality_sum:
            break

    send_progress("Graphs ready!")
    full_network_data = graph_to_json(G, custom_centrality)
    for node in G.nodes():
        if node in top_k_nodes:
            G.nodes[node]["class"] = 1
        else:
            G.nodes[node]["class"] = 2

    key_collab_data = graph_to_json(G, custom_centrality)
    calculate_contribution_percentages(all_files_with_sizes, files_per_contributor_with_sizes)
    unique_files_per_contributor = {key: list(value) for key, value in unique_files_per_contributor.items()}
    files_per_contributor_with_sizes = {contributor: dict(files) for contributor, files in files_per_contributor_with_sizes.items()}
    loc_per_contributor = dict(loc_per_contributor)
    filtered_unique_files = {
        node: unique_files_per_contributor[get_normalized_username(node)]
        for node in top_k_nodes
        if get_normalized_username(node) in unique_files_per_contributor
    }
    filtered_unique_files_with_file_sizes = add_file_sizes(repo, filtered_unique_files)
    files_per_contributor_with_sizes = {
        node: files_per_contributor_with_sizes.get(get_normalized_username(node), {})
        for node in top_k_nodes
        if get_normalized_username(node) in files_per_contributor_with_sizes
    }

    graphs = {
        "network_graph": full_network_data,
        "key_collab": key_collab_data,
        "unique_files_per_contributor": unique_files_per_contributor,
        "loc_per_contributor": loc_per_contributor,
        "filtered_unique_files": filtered_unique_files_with_file_sizes,
        "all_files_with_sizes": all_files_with_sizes,
        "files_per_contributor_with_percentages": files_per_contributor_with_sizes,
    }

    logging.info("Unique files per contributor: %s", unique_files_per_contributor)
    logging.info("Files per contributor (with percentages): %s", files_per_contributor_with_sizes)
    logging.info("All files with sizes: %s", all_files_with_sizes)

    repo.close()
    repo = None

    def remove_readonly(func, path, _):
        os.chmod(path, 0o777)
        func(path)

    try:
        shutil.rmtree(temp_dir, onerror=remove_readonly)
    except PermissionError:
        time.sleep(0.5)
        shutil.rmtree(temp_dir, onerror=remove_readonly)

    return graphs
