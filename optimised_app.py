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

from graph_to_json import graph_to_json


def generateGraphSet(repo_url, send_progress):
    # Set the local save directory for generated images
    base_save_dir = "C:/Users/DELL/Documents/bus_factor_graph/backend/graphs"

    # Extract repository name from URL
    repo_name = (
            repo_url.split("/")[-2] + "/" + repo_url.split("/")[-1].replace(".git", "")
    )

    repo_dir = os.path.join(base_save_dir, repo_name.replace("/", "_"))
    os.makedirs(repo_dir, exist_ok=True)

    load_dotenv()
    GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')

    if GITHUB_TOKEN:
        print("Token fetched successfully.")
    else:
        print("Token not found. Ensure it's set as an environment variable.")

    g = Github(GITHUB_TOKEN)

    # Step 1: Clone the repository into a temporary directory
    send_progress("Cloning repository...")
    temp_dir = tempfile.mkdtemp()

    auth_repo_url = repo_url.replace("https://", f"https://{GITHUB_TOKEN}@")
    repo = git.Repo.clone_from(auth_repo_url, temp_dir, bare=True)

    send_progress("Repository cloned!")

    # Step 2: Fetch all contributors for the project
    send_progress("Fetch all contributors for the project...")
    github_repo = g.get_repo(repo_name)

    # Convert contributors to a list to know the total
    contributors_list = list(github_repo.get_contributors())
    total_contributors = len(contributors_list)

    contributor_data = {}
    email_to_username = {}
    name_to_username = {}

    # Precompute bot logic later
    bot_candidates = set()

    for i, contributor in enumerate(contributors_list, start=1):
        percentage = math.ceil((i / total_contributors) * 100)
        send_progress(f"Fetch all contributors for the project...{percentage}%")

        username = contributor.login
        ctype = contributor.type
        normalized_name = re.sub(r"[^a-zA-Z0-9]", "", username).lower()

        contributor_data[username] = {
            "type": ctype,
            "normalized_name": normalized_name
        }

        if contributor.email:
            email_to_username[contributor.email] = username
        elif contributor.name:
            name_to_username[contributor.name] = username

        # Identify bots
        if ctype == "Bot" or "bot" in username.lower():
            bot_candidates.add(username)

    # Helper function to normalize usernames
    normalization_cache = {}

    def get_normalized_username(username):
        if username not in normalization_cache:
            normalization_cache[username] = re.sub(r"[^a-zA-Z0-9]", "", (username or "")).lower()
        return normalization_cache[username]

    def is_bot(username):
        return username in bot_candidates

    # Step 3: Determine cutoff date (1.5 years before the most recent commit)
    # Assuming the default branch is the correct reference for most recent commit
    # This picks the most recent commit across all refs by default
    most_recent_commit = next(repo.iter_commits())
    cutoff_date = most_recent_commit.committed_datetime - timedelta(days=547)

    send_progress("Calculate LOC and file diversity...")

    # Step 4: Process commits without loading all into a list if possible
    loc_per_contributor = defaultdict(int)  # Lines of code changed by each contributor
    unique_files_per_contributor = defaultdict(set)  # Unique files each contributor has modified

    # We'll store commit data only as needed
    commits_data = []
    commit_count = 0

    # Instead of converting to a list first, we just iterate
    # Counting commits for progress estimate: we can do a rough progress by increments
    # If this is still slow, consider removing or reducing progress calls
    # Just do progress every N commits to reduce overhead
    N = 100  # Update progress every 100 commits

    for c, commit in enumerate(repo.iter_commits(), start=1):
        if c % N == 0:
            send_progress(f"Processing commits... approx {c} processed")

        if commit.committed_datetime < cutoff_date:
            break

        author_username = email_to_username.get(commit.author.email) or name_to_username.get(
            commit.author.name) or commit.author.name

        # Exclude bots early
        if is_bot(author_username):
            continue

        norm_user = get_normalized_username(author_username)

        commit_stats = commit.stats.total
        total_lines_changed = commit_stats['insertions'] + commit_stats['deletions']
        loc_per_contributor[norm_user] += total_lines_changed

        file_list = list(commit.stats.files.keys())
        unique_files_per_contributor[norm_user].update(file_list)

        commits_data.append({
            "datetime": commit.committed_datetime,
            "author_name": author_username,
            "author_email": commit.author.email,
            "files": file_list
        })
        commit_count += 1

    send_progress("Generating graphs")

    G = nx.Graph()
    contributor_map = defaultdict(set)  # Maps normalized usernames to sets of (username, email)
    file_contributors = defaultdict(set)

    send_progress("Processing commits for graph building...")

    # Step 5: Process commits to form contributor groups and track file contributions
    for idx, commit in enumerate(commits_data, start=1):
        if idx % N == 0:
            send_progress(f"Processing commits for graph building... {idx}/{commit_count}")

        username = commit["author_name"]
        email = commit["author_email"]

        # Normalize username to group duplicates
        normalized_username = get_normalized_username(username)
        contributor_map[normalized_username].add((username, email))

        # Track contributors who modified each file
        for file in commit["files"]:
            file_contributors[file].add(normalized_username)

    send_progress("Creating graph nodes...")

    # Step 6: Create graph nodes for each unique contributor group
    unique_contributors = {}
    for norm_name, variations in contributor_map.items():
        representative = next(iter(variations))[0]
        unique_contributors[norm_name] = representative
        G.add_node(representative)

    send_progress("Adding edges based on shared file contributions...")

    # Step 7: Add edges
    # We'll build a temporary structure to avoid repeated checks:
    edge_weights = defaultdict(int)
    for file, cset in file_contributors.items():
        clist = list(cset)
        length = len(clist)
        for i in range(length):
            for j in range(i + 1, length):
                c1 = unique_contributors[clist[i]]
                c2 = unique_contributors[clist[j]]
                if c1 > c2:
                    c1, c2 = c2, c1
                edge_weights[(c1, c2)] += 1

    for (c1, c2), w in edge_weights.items():
        G.add_edge(c1, c2, weight=w)

    send_progress("Calculating custom centrality scores...")

    # Step 8: Calculate custom centrality
    degree_centrality = nx.degree_centrality(G)

    # Precompute max loc and file counts once
    if loc_per_contributor:
        max_loc = max(loc_per_contributor.values())
    else:
        max_loc = 1  # Avoid division by zero if empty

    if unique_files_per_contributor:
        max_files = max(len(files) for files in unique_files_per_contributor.values())
    else:
        max_files = 1

    custom_centrality = {}
    for contributor in G.nodes():
        norm_name = get_normalized_username(contributor)
        total_loc = loc_per_contributor[norm_name]
        file_count = len(unique_files_per_contributor[norm_name])

        custom_centrality[contributor] = (degree_centrality[contributor] +
                                          0.5 * (total_loc / max_loc) +
                                          0.5 * (file_count / max_files))

    # Identify key developers
    sorted_nodes = sorted(custom_centrality.items(), key=lambda item: item[1], reverse=True)
    threshold_percentage = 0.3
    total_centrality_sum = sum(custom_centrality.values())
    cumulative_sum = 0
    top_k_nodes = []

    for node, val in sorted_nodes:
        cumulative_sum += val
        top_k_nodes.append(node)
        if cumulative_sum >= threshold_percentage * total_centrality_sum:
            break

    send_progress("Graphs ready!")

    # Add class attribute to graph nodes
    for node in G.nodes():
        G.nodes[node]['class'] = 1 if node in top_k_nodes else 2

    full_network_data = graph_to_json(G, custom_centrality)
    key_collab_data = graph_to_json(G, custom_centrality)

    graphs = {
        "network_graph": full_network_data,
        "key_collab": key_collab_data,
    }
    print(graphs)

    repo.close()
    repo = None

    # Retry function for handling PermissionError
    def remove_readonly(func, path, _):
        os.chmod(path, 0o777)
        func(path)

    # Attempt to delete the temporary directory with retries
    try:
        shutil.rmtree(temp_dir, onerror=remove_readonly)
    except PermissionError:
        time.sleep(0.5)
        shutil.rmtree(temp_dir, onerror=remove_readonly)

    return graphs
