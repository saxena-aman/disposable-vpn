
from io import StringIO
import time
import digitalocean
import paramiko
import requests
import logging
import os
from dotenv import load_dotenv
load_dotenv()

def ssh_execute_script(host, username, local_script_path, remote_script_path):
    # Set up logging
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger(__name__)
    
    ssh = None
    try:
        # Get private key from environment
        private_key_string = os.getenv("SSH_PRIVATE_KEY")
        if not private_key_string:
            raise ValueError("SSH_PRIVATE_KEY environment variable is not set.")

        # Clean up the private key string
        private_key_string = private_key_string.strip()
        if "\\n" in private_key_string:
            private_key_string = private_key_string.replace("\\n", "\n")
        
        # Ensure the key has proper line endings
        if not private_key_string.endswith('\n'):
            private_key_string += '\n'

        logger.debug("Private key format check:")
        # logger.debug(f"Key starts with: {private_key_string[:40]}...")
        # logger.debug(f"Key ends with: ...{private_key_string[-40:]}")

        # Create a file-like object from the private key string
        key_stream = StringIO(private_key_string)

        try:
            # Try ED25519 key first (based on your key format)
            private_key = paramiko.Ed25519Key.from_private_key(key_stream)
            logger.info("Successfully loaded ED25519 key")
        except paramiko.ssh_exception.SSHException:
            # If ED25519 fails, try RSA
            key_stream.seek(0)  # Reset stream position
            try:
                private_key = paramiko.RSAKey.from_private_key(key_stream)
                logger.info("Successfully loaded RSA key")
            except paramiko.ssh_exception.SSHException as e:
                logger.error(f"Failed to load private key: {str(e)}")
                raise ValueError(f"Invalid private key format: {str(e)}")

        # Set up SSH connection with more verbose error handling
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        logger.info(f"Attempting to connect to {host} with username {username}")
        try:
            ssh.connect(
                hostname=host,
                username=username,
                pkey=private_key,
                timeout=10,
                allow_agent=False,
                look_for_keys=False
            )
            logger.info("SSH Connection established successfully")
        except paramiko.AuthenticationException:
            raise Exception("Authentication failed. Please check your credentials.")
        except paramiko.SSHException as ssh_exception:
            raise Exception(f"SSH exception occurred: {str(ssh_exception)}")
        except Exception as e:
            raise Exception(f"Connection failed: {str(e)}")

        # Upload and execute script with better error handling
        try:
            # Upload script
            sftp = ssh.open_sftp()
            logger.info(f"Uploading script from {local_script_path} to {remote_script_path}")
            sftp.put(local_script_path, remote_script_path)
            sftp.close()

            # Make script executable
            logger.info(f"Setting execute permissions on {remote_script_path}")
            ssh.exec_command(f"chmod +x {remote_script_path}")

            # Execute script
            logger.info("Executing script")
            stdin, stdout, stderr = ssh.exec_command(f"sudo bash {remote_script_path}")
            
            # Read output with timeout
            output = stdout.read().decode('utf-8', errors='ignore')
            error = stderr.read().decode('utf-8', errors='ignore')

            # Log complete output
            logger.debug(f"Script output: {output}")
            if error:
                logger.warning(f"Script stderr: {error}")

            # Parse output
            result = {}
            for line in output.splitlines():
                for key in ['CLIENT_PRIVATE_KEY', 'SERVER_PUBLIC_KEY', 'SERVER_IP']:
                    if f"{key}=" in line:
                        result[key] = line.split("=", 1)[1].strip('"\'')

            if result:
                return {"status": "success", **result}, 200
            else:
                return {
                    "status": "error",
                    "message": "Script did not produce expected output.",
                    "output": output,
                    "error": error
                }, 500

        except Exception as e:
            logger.error(f"Error during script execution: {str(e)}")
            return {"status": "error", "message": str(e)}, 500

    except Exception as e:
        logger.error(f"Error in ssh_execute_script: {str(e)}")
        return {"status": "error", "message": str(e)}, 500

    finally:
        if ssh:
            ssh.close()
            logger.info("SSH connection closed")

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
