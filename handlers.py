
import time
import digitalocean
import requests
import os
from dotenv import load_dotenv
from flask import Flask, json, jsonify
import logging
load_dotenv()
app = Flask(__name__)
# Set up logging for Docker visibility
logging.basicConfig(level=logging.DEBUG)  # Log level set to DEBUG
logger = logging.getLogger()
handler = logging.StreamHandler()  # Logs to console (stdout)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
app.logger.handlers = []  # Clear Flask's default handlers
app.logger.addHandler(handler)



def ssh_execute_script(host, username, script):
    """
    Executes an SSH script by making an API call to a cloud function.
    """
    app.logger.debug("Fetching environment variables.")
    private_key = os.getenv("SSH_PRIVATE_KEY")
    if not private_key:
        app.logger.error("SSH_PRIVATE_KEY environment variable is not set.")
        raise EnvironmentError("SSH_PRIVATE_KEY environment variable is not set.")
    
    function_url = os.getenv("CLOUD_FUNCTION_URL")
    if not function_url:
        app.logger.error("CLOUD_FUNCTION_URL environment variable is not set.")
        raise EnvironmentError("CLOUD_FUNCTION_URL environment variable is not set.")
    
    private_key = private_key.replace('\\n', '\n')
    script = script.replace('\\n', '\n')
    # Prepare the payload
    payload = {
        "host": host,
        "username": username,
        "script_content": script,
        "private_key": private_key
    }
    app.logger.debug(f"Prepared payload: {json.dumps(payload)}")
    
    # Make the API call
    try:
        app.logger.info(f"Calling cloud function at {function_url}")
        response = requests.post(function_url, json=payload)
        
        # Handle the response
        if response.status_code == 200:
            app.logger.info("Script executed successfully via cloud function.")
            return response.json(), response.status_code
        else:
            app.logger.warning(f"Cloud function returned an error: {response.text}")
            return {"error": response.text}, response.status_code
    except requests.exceptions.RequestException as e:
        app.logger.error(f"Failed to make the API call: {e}")
        return {"error": str(e)}, 500
    

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

def delete_droplet(api_token, droplet_name="my-droplet"):
    # Check if required parameters are provided
    if not droplet_name or not api_token:
        return jsonify({"status": "error", "message": "Missing required parameters: droplet_name or api_token"}), 400
    
    # URL for listing droplets
    url = 'https://api.digitalocean.com/v2/droplets'
    
    # Set up the headers for authentication
    headers = {
        'Authorization': f'Bearer {api_token}'
    }
    
    # Make the request to get the list of droplets
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        return jsonify({"status": "error", "message": "Failed to retrieve droplet list", "details": response.json()}), 500
    
    droplets = response.json().get('droplets', [])
    droplet_id = None
    
    # Find the droplet ID by name
    for droplet in droplets:
        if droplet['name'] == droplet_name:
            droplet_id = droplet['id']
            break
    
    if not droplet_id:
        return jsonify({"status": "error", "message": f"Droplet with name '{droplet_name}' not found."}), 404
    
    # URL for deleting the droplet
    delete_url = f'https://api.digitalocean.com/v2/droplets/{droplet_id}'
    
    # Make the DELETE request to delete the droplet
    delete_response = requests.delete(delete_url, headers=headers)
    
    if delete_response.status_code == 204:
        return {"status": "success", "message": f"Droplet '{droplet_name}' (ID: {droplet_id}) deleted successfully"}
    else:
        return {"status": "error", "message": f"Failed to delete droplet '{droplet_name}'", "details": delete_response.json()}



def read_bash_script(script_path):
    with open(script_path, 'r') as file:
        script_content = file.read()
    return script_content

def escape_script_for_json(script_content):
    # Escape the script for JSON (handling special characters like newline, quotes, etc.)
    escaped_script = script_content.replace("\r", "")
    return escaped_script
