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

def generateGraphSet(repo_url,send_progress):
    # Set the local save directory for generated images
    base_save_dir = "C:/Users/DELL/Documents/bus_factor_graph/backend/graphs"
   
    # Extract repository name from URL
    repo_name = (
        repo_url.split("/")[-2] + "/" + repo_url.split("/")[-1].replace(".git", "")
    )

    repo_dir = os.path.join(base_save_dir, repo_name.replace("/", "_"))
    os.makedirs(repo_dir, exist_ok=True)

    # GitHub access token (replace with your token)
    GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')

    if GITHUB_TOKEN:
        print("Token fetched successfully.")
    else:
        print("Token not found. Ensure it's set as an environment variable.")
  
    load_dotenv()
    g = Github(GITHUB_TOKEN)

    # Step 1: Clone the repository into a temporary directory
    send_progress("Cloning repository...")
    temp_dir = tempfile.mkdtemp()
    
    auth_repo_url = repo_url.replace("https://", f"https://{GITHUB_TOKEN}@")
    repo = git.Repo.clone_from(auth_repo_url, temp_dir, bare=True)
    
    send_progress("Repository cloned!")
    # Step 2: Fetch all contributors for the project
    github_repo = g.get_repo(repo_name)
    contributor_data = {}
    email_to_username = {}
    name_to_username = {}

    send_progress("Fetch all contributors for the project...")
    # Populate a dictionary with all contributors, storing their type and normalizing their username
    
    contributors = github_repo.get_contributors()
    contributors_list = list(contributors) 
    i=0
    tot=len(contributors_list)
    for contributor in contributors:
        i+=1
        percentage=math.ceil((i/tot)*100)
        send_progress(f"Fetch all contributors for the project...{percentage}%")
        username = contributor.login
        contributor_data[username] = {
            "type": contributor.type,
            "normalized_name": re.sub(r"[^a-zA-Z0-9]", "", username).lower()
        }

        # Map email/name to username if email/name is available
        if contributor.email:
            email_to_username[contributor.email] = username
        elif contributor.name:
            name_to_username[contributor.name] = username
   
    
    # Helper function to normalize usernames and check if a user is a bot
    def get_normalized_username(username):
        return re.sub(r"[^a-zA-Z0-9]", "", username).lower()

    def is_bot(username):
        user_info = contributor_data.get(username)
        # Check if the user is a bot based on user_info or username
        if user_info:
            if user_info["type"] == "Bot":
                return True
        # Check if 'bot' is in the username (case-insensitive)
        if "bot" in username.lower():
            return True
        return False
  
    
    # Step 3: Determine cutoff date (1.5 years before the most recent commit)
    most_recent_commit = next(repo.iter_commits())
    cutoff_date = most_recent_commit.committed_datetime - timedelta(days=547)

    send_progress("Calculate LOC and file diversity...")
    # Step 4: Load all commits in memory for faster processing and calculate LOC and file diversity
    commits_data = []
    loc_per_contributor = defaultdict(int)  # Lines of code changed by each contributor
    unique_files_per_contributor = defaultdict(set)  # Unique files each contributor has modified
    commits_list = list(repo.iter_commits())
    tot = len(commits_list)
    j = 0
    for commit in commits_list:
        j+=1
        percentage=math.ceil((j/tot)*100)
        send_progress(f"Calculate LOC and file diversity...{percentage}%")
        if commit.committed_datetime < cutoff_date:
            break  # Only consider recent commits

        author_username = email_to_username.get(commit.author.email) if email_to_username.get(commit.author.email) else name_to_username.get(commit.author.name)

        if not author_username:
            author_username = commit.author.name

        # Normalize username
        normalized_username = get_normalized_username(author_username)
        
        # Track lines of code changed and unique files modified
        total_lines_changed = commit.stats.total['insertions'] + commit.stats.total['deletions']  # Total lines changed (insertions + deletions)
        loc_per_contributor[normalized_username] += total_lines_changed
        unique_files_per_contributor[normalized_username].update(commit.stats.files.keys())
        
        commits_data.append({
            "datetime": commit.committed_datetime,
            "author_name": author_username,
            "author_email": commit.author.email,
            "files": list(commit.stats.files.keys())
        })
    send_progress("Generating graphs")    
    
    # Initialize the network and contributor tracking
    G = nx.Graph()
    contributor_map = defaultdict(set)  # Map normalized usernames to actual usernames
    file_contributors = defaultdict(set)  # Track contributors per file for edge creation
   
    send_progress("Processing commits...")
    # Step 5: Process commits to identify contributors and group duplicates
    for commit in commits_data:
        username = commit["author_name"]
        email = commit["author_email"]

        # Exclude bot accounts using cached data
        if is_bot(username):
            continue

        # Normalize username to group duplicates
        normalized_username = get_normalized_username(username)
        contributor_map[normalized_username].add((username, email))  # Track all variations of each contributor

        # Track contributors who modified each file
        for file in commit["files"]:
            file_contributors[file].add(normalized_username)

    send_progress("Creating graph nodes for each unique contributor group...")
    # Step 6: Create graph nodes for each unique contributor group
    unique_contributors = {}
    for norm_name, variations in contributor_map.items():
        representative = next(iter(variations))[0]
        unique_contributors[norm_name] = representative
        G.add_node(representative)

    send_progress("Adding edges based on shared file contributions...")
    # Step 7: Add edges based on shared file contributions
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
    # Step 8: Calculate custom centrality scores for each contributor
    custom_centrality = {}
    degree_centrality = nx.degree_centrality(G)

    for contributor in G.nodes():
        norm_name = get_normalized_username(contributor)
        
        # Get the total LOC and unique file count for this contributor
        total_loc = loc_per_contributor[norm_name]
        file_count = len(unique_files_per_contributor[norm_name])

        # Calculate custom centrality (adjust weighting as needed)
        custom_centrality[contributor] = degree_centrality[contributor] + \
                                        (0.5 * total_loc / max(loc_per_contributor.values())) + \
                                        (0.5 * file_count / max(len(files) for files in unique_files_per_contributor.values()))   
    
    
    # >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>[Key Developers]>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>


    # Use custom centrality calculated earlier
    sorted_nodes = sorted(custom_centrality.items(), key=lambda item: item[1], reverse=True)

    # Define the threshold percentage for top contributors
    threshold_percentage = 0.3
    total_centrality_sum = sum(custom_centrality.values())
    cumulative_sum = 0
    top_k_nodes = []

    # Select top nodes until the cumulative sum reaches the threshold
    for node, centrality_value in sorted_nodes:
        cumulative_sum += centrality_value
        top_k_nodes.append(node)
        if cumulative_sum >= threshold_percentage * total_centrality_sum:
            break
        
    send_progress("Graphs ready!")    
    # Create JSON for full network and key collaborators network
    full_network_data = graph_to_json(G, custom_centrality)
    
    # Add a 'class' attribute to nodes in the full network graph
    for node in G.nodes():
        if node in top_k_nodes:
            G.nodes[node]['class'] = 1  # Top collaborators
        else:
            G.nodes[node]['class'] = 2  # Others
    
    key_collab_data = graph_to_json(G, custom_centrality)

    # Save data to file or return it directly
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
        time.sleep(0.5)  # Wait a bit and try again
        shutil.rmtree(temp_dir, onerror=remove_readonly)
    # os.remove(temp_dir)
    return graphs

