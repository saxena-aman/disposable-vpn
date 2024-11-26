
import time
import digitalocean
import requests
import os
from dotenv import load_dotenv
load_dotenv()

def ssh_execute_script(host, username, script):
    # Retrieve the private key from the environment variable
    private_key = os.getenv("SSH_PRIVATE_KEY")
    if not private_key:
        raise EnvironmentError("SSH_PRIVATE_KEY environment variable is not set.")
    
    function_url = os.getenv("CLOUD_FUNCTION_URL")
    if not function_url:
        raise EnvironmentError("CLOUD_FUNCTION_URL environment variable is not set.")
    
    # Prepare the payload
    payload = {
        "host": host,
        "username": username,
        "script_content": script,
        "private_key": private_key  # SSH Private Key from environment or passed in
    }

    # Define the Cloud Function endpoint
    api_url = function_url  # Replace with your actual URL

    try:
        # Make a POST request to the Cloud Function
        response = requests.post(api_url, json=payload)
        
        
        # Handle the response
        if response.status_code == 200:
            print("Script executed successfully.")
            response_data = response.json()  # Assuming the response is in JSON format
            # Assuming the response contains 'CLIENT_PRIVATE_KEY', 'SERVER_IP', 'SERVER_PUBLIC_KEY', and 'status'
            return response_data, response.status_code
        else:
            print("Error executing script.")
            print("Status Code:", response.status_code)
            print("Response:", response.text)
            return None, response.status_code
    except requests.exceptions.RequestException as e:
        print("Failed to make the API call.")
        print("Error:", str(e))
        return None, 500  # Return a 500 status code for request exceptions
    

def move_droplet_to_project(api_token, droplet_id, project_id):
    url = f"https://api.digitalocean.com/v2/projects/{project_id}/resources"
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json"
    }
    data = {
        "resources": [f"do:droplet:{droplet_id}"]
    }

    # Make the API request to move the droplet to the project
    response = requests.post(url, headers=headers, json=data)
    
    if response.status_code == 200:
        print("Droplet successfully moved to the project.")
        return True
    else:
        print("Failed to move droplet:", response.json())
        return False

def get_project_id(api_token, project_name):
    # Initialize the manager with the API token
    manager = digitalocean.Manager(token=api_token)
    
    try:
        # Get the list of all projects
        projects = manager.get_all_projects()
        # Iterate through the projects and find the one with the matching name
        for project in projects:
            if project.name == project_name:
                return project.id
        
        # If the project is not found
        print(f"Project with name '{project_name}' not found.")
        return None
    except Exception as e:
        print("An error occurred:", str(e))
        return None

def get_ssh_key_id(api_token):
    """
    Retrieve the ID of an SSH key by name.
    """
    ssh_key_name = os.getenv("DIGITALOCEAN_SSH_KEY_NAME")
    manager = digitalocean.Manager(token=api_token)
    keys = manager.get_all_sshkeys()
    for key in keys:
        if key.name == ssh_key_name:
            return key.id
    raise ValueError(f"SSH key '{ssh_key_name}' not found.")

def create_droplet(api_token, project_id, droplet_name="my-droplet", region="sgp1", size="s-1vcpu-512mb-10gb", image="ubuntu-20-04-x64"):
    # Get SSH key ID by name
    ssh_key_id = get_ssh_key_id(api_token)

    # Step 1: Create a new Droplet with SSH key
    droplet = digitalocean.Droplet(
        token=api_token,
        name=droplet_name,
        region=region,
        size_slug=size,
        image=image,
        ssh_keys=[ssh_key_id]  # Add the SSH key ID
    )
    droplet.create()

    # Wait for the droplet to be active and get its ID
    while True:
        droplet.load()
        if droplet.status == "active" and droplet.ip_address:
            print("Droplet is fully deployed.")
            break
        # Wait before checking again
        print("Waiting for droplet to be fully deployed...")
        time.sleep(5)

    # Step 2: Move the droplet to the specified project
    droplet_id = droplet.id
    move_droplet_to_project(api_token, droplet_id, project_id)

    # Return the IPv4 address of the newly created droplet
    return droplet.ip_address

def read_bash_script(script_path):
    with open(script_path, 'r') as file:
        script_content = file.read()
    return script_content

def escape_script_for_json(script_content):
    # Escape the script for JSON (handling special characters like newline, quotes, etc.)
    escaped_script = script_content.replace("\r", "")
    return escaped_script
