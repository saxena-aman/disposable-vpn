
import time
import digitalocean
import paramiko
import requests
import os
from dotenv import load_dotenv
load_dotenv()

def ssh_execute_script(host, username, ssh_key_path, local_script_path, remote_script_path):
    import paramiko
    try:
        # Set up SSH connection
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(hostname=host, username=username, key_filename=ssh_key_path)

        # Upload the script to the remote server
        sftp = ssh.open_sftp()
        sftp.put(local_script_path, remote_script_path)
        sftp.close()

        # Ensure the script is executable
        ssh.exec_command(f"chmod +x {remote_script_path}")

        # Run the bash script with the proper environment
        stdin, stdout, stderr = ssh.exec_command(f"sudo bash {remote_script_path}")
        output = stdout.read().decode()
        error = stderr.read().decode()

        # Log full output for debugging
        # print("Full Script Output:", output + "\n" + error)

        # Parse the output for expected keys
        result = {}
        for line in output.splitlines():
            if "CLIENT_PRIVATE_KEY=" in line:
                result["CLIENT_PRIVATE_KEY"] = line.split("=", 1)[1].strip('"\'')
            elif "SERVER_PUBLIC_KEY=" in line:
                result["SERVER_PUBLIC_KEY"] = line.split("=", 1)[1].strip('"\'')
            elif "SERVER_IP=" in line:
                result["SERVER_IP"] = line.split("=", 1)[1].strip('"\'')
        
        ssh.close()

        if result:
            return {"status": "success", **result}, 200
        else:
            return {"status": "error", "message": "Script did not produce expected output."}, 500

    except Exception as e:
        return {"status": "error", "message": str(e)}, 500

    finally:
        ssh.close()


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
