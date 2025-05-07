import subprocess
import shutil
import time
import os
import tiktoken

def count_tokens_llm(text, model="gpt-3.5-turbo"):
    encoding = tiktoken.encoding_for_model(model)
    return len(encoding.encode(text))

def remove_readonly(func, path, _):
    # Helper function to remove readonly permission and retry deletion.
    os.chmod(path, 0o777)
    func(path)
    
def generate_repomix_output(repo_url,send_progress):
    """
    Clone the repository, run Repomix with XML output, and return the XML data.
    
    :param repo_url: The URL of the Git repository.
    :return: The contents of repomix-output.xml as a string.
    
    """
    repo_name = repo_url.split("/")[-1].replace(".git", "")
    repo_dir = f"temp_repos/{repo_name}"
    
    # If the directory exists, delete it
    if os.path.exists(repo_dir):
        shutil.rmtree(repo_dir, onerror=remove_readonly)
        
    # Clone the repository
    send_progress("Getting repository data...")
    subprocess.run(["C:\\Program Files\\Git\\bin\\git.exe", "clone", repo_url, repo_dir], check=True)
    
    # Run Repomix in XML mode
    # subprocess.run(["C:\\Program Files\\nodejs\\npx.cmd", "repomix","--compress", "--style", "XML"], cwd=repo_dir, check=True)
    send_progress("Running RepoMix...")
    subprocess.run([
    "C:\\Program Files\\nodejs\\npx.cmd", "repomix",
    "--compress",
    "--remove-empty-lines",
    "--remove-comments",
    "--ignore", "**/*.jpeg,**/*.png,**/*.svg,linux/,macos/,test/,web/,windows/,**/*.json"], cwd=repo_dir, check=True)


    # Read the XML output file
    output_file = os.path.join(repo_dir, "repomix-output.xml")
    with open(output_file, "r", encoding="utf-8") as file:
        repo_data = file.read()

    # Attempt to delete the temporary directory
    try:
        shutil.rmtree(repo_dir, onerror=remove_readonly)
    except PermissionError:
        time.sleep(0.5) 
        shutil.rmtree(repo_dir, onerror=remove_readonly)

    token_count = count_tokens_llm(repo_data)

    return repo_data, token_count


