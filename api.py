import os
from dotenv import load_dotenv
from flask import Flask, jsonify, request
import time
import uuid
from file_handler import handle_ssh_response
from handlers import create_droplet, escape_script_for_json, get_project_id, read_bash_script, ssh_execute_script
load_dotenv()

# Mapping of region full names to DigitalOcean region codes
REGION_MAPPING = {
    "San Francisco": "sfo3",
    "Amsterdam": "ams3",
    "Singapore": "sgp1",
    "Frankfurt": "fra1",
    "Sydney": "syd1"
}



app = Flask(__name__)

@app.route('/create_vpn', methods=['POST'])
def create_vpn():
    
    # Parse JSON payload and default to "Singapore" if no region is provided
    data = request.get_json()
    region_name = data.get("region", "Singapore").strip()  # Default to "Singapore"
    
    # Map the full region name to the corresponding code
    region_code = REGION_MAPPING.get(region_name)

    if not region_code:
        return jsonify({
            "error": f"Invalid region '{region_name}'. Valid options are: {', '.join(REGION_MAPPING.keys())}"
        }), 400

    # If 'name' is provided in the body, format it as "droplet-{user-provider-name}",
    # otherwise, generate a default name with a UUID
    droplet_name = f"droplet-{data.get('name', uuid.uuid4())}"

    # Use droplet_name for your droplet creation logic
    print(f"Droplet name: {droplet_name}")
    
    # Load DigitalOcean VM credentials and paths from environment variables
    username = os.getenv("DIGITALOCEAN_SSH_USERNAME")
    local_script_path = os.getenv("SCRIPT_LOCAL_PATH")
    remote_script_path = os.getenv("SCRIPT_REMOTE_PATH")
    digital_ocean_api_key = os.getenv("DIGITALOCEAN_API_KEY")
    digital_ocean_project = os.getenv("DIGITAL_OCEAN_PROJECT")
    project_id = get_project_id(digital_ocean_api_key, digital_ocean_project)
    ipv4_address = create_droplet(digital_ocean_api_key, project_id, droplet_name=droplet_name, region=region_code)
    
    time.sleep(20)
    # DigitalOcean VM credentials
    host = ipv4_address
    script_content = read_bash_script(local_script_path)
    escaped_script = escape_script_for_json(script_content)
    # Call the SSH function
    response, status_code = ssh_execute_script(host, username, escaped_script)
    # Handle the response
    if status_code == 200:
    # Pass the response to handle the validation and further actions
        return handle_ssh_response(response,droplet_name)

if __name__ == '__main__':
#     # This is needed to run the Flask app when the script is executed directly
    app.run(debug=True, host="0.0.0.0", port=8080)

