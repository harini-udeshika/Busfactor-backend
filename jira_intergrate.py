from jira import JIRA
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# JIRA credentials
JIRA_SERVER = os.getenv("JIRA_SERVER")
JIRA_EMAIL = os.getenv("JIRA_EMAIL")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")

# Authenticate with JIRA
jira = JIRA(server=JIRA_SERVER, basic_auth=(JIRA_EMAIL, JIRA_API_TOKEN))

# Specify your project key
PROJECT_KEY = "TH"  # Replace with your JIRA project key

# JQL query to get all issues in the project that have an assignee
JQL_QUERY = f'project = "{PROJECT_KEY}" AND assignee IS NOT EMPTY ORDER BY updated DESC'

# Fetch assigned issues
issues = jira.search_issues(JQL_QUERY, maxResults=1000)  # Adjust maxResults if needed

# Create a dictionary to store contributors and their assigned tasks
contributors = {}

# Iterate through issues
for issue in issues:
    assignee = issue.fields.assignee.displayName
    issue_key = issue.key
    issue_summary = issue.fields.summary
    issue_status = issue.fields.status.name  # Get issue status (To Do, In Progress, Done)
    issue_labels = issue.fields.labels  # Get issue labels

    # Store the issue under the contributor
    if assignee not in contributors:
        contributors[assignee] = []
    contributors[assignee].append({
        "Issue Key": issue_key,
        "Summary": issue_summary,
        "Status": issue_status,
        "Labels": issue_labels if issue_labels else ["No Labels"]  # Handle empty labels
    })

# Print contributors and their tasks
for contributor, tasks in contributors.items():
    print(f"\nContributor: {contributor}")
    for task in tasks:
        labels = ", ".join(task['Labels'])  # Convert list to comma-separated string
        print(f"  - {task['Issue Key']}: {task['Summary']} [{task['Status']}] | Labels: {labels}")
