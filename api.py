import os
from dotenv import load_dotenv
from flask import Flask, jsonify, request
import time
import uuid
from file_handler import handle_ssh_response
from handlers import create_droplet, escape_script_for_json, get_project_id, read_bash_script, ssh_execute_script
load_dotenv()
import logging

# Mapping of region full names to DigitalOcean region codes
REGION_MAPPING = {
    "San Francisco": "sfo3",
    "Amsterdam": "ams3",
    "Singapore": "sgp1",
    "Frankfurt": "fra1",
    "Sydney": "syd1"
}



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

@app.route('/create_vpn', methods=['GET'])
def create_vpn():
    
    region_name = request.args.get("region", "Singapore").strip()  # Default to "Singapore"
    
    # Map the full region name to the corresponding code
    region_code = REGION_MAPPING.get(region_name)

    if not region_code:
        return jsonify({
            "error": f"Invalid region '{region_name}'. Valid options are: {', '.join(REGION_MAPPING.keys())}"
        }), 400

    # If 'name' is provided in the body, format it as "droplet-{user-provider-name}",
        # Get 'name' from query params, default to a UUID if not provided
    droplet_name = f"droplet-{request.args.get('name', str(uuid.uuid4()))}"

    # Use droplet_name for your droplet creation logic
    print(f"Droplet name: {droplet_name}")
    
    # Load DigitalOcean VM credentials and paths from environment variables
    username = os.getenv("DIGITALOCEAN_SSH_USERNAME")
    local_script_path = os.getenv("SCRIPT_LOCAL_PATH")
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

    app.logger.debug(f"Response from ssh_execute_script_function: {response}")
    # Handle the response
    if status_code == 200:
    # Pass the response to handle the validation and further actions
        return handle_ssh_response(response,droplet_name)
    else:
        return jsonify({
            "status": "error",
            "message": "Handle SSH Response Function Not Working"
        }), 400
        
@app.route('/execute_script', methods=['POST'])
def execute_script():
    """
    Flask endpoint to execute a script on a remote host.

    Expects a JSON payload with:
    - host: The target host
    - username: The SSH username
    - script: The script content to execute
    """
    try:
        app.logger.info("Received a request to execute a script.")

        # Parse request data
        data = request.get_json()
        if not data:
            app.logger.error("Invalid or missing JSON payload.")
            return jsonify({"error": "Invalid or missing JSON payload"}), 400
        
        host = data.get("host")
        username = data.get("username")
        script = data.get("script")
        
        if not all([host, username, script]):
            app.logger.error("Missing required fields: host, username, or script.")
            return jsonify({"error": "Missing required fields: host, username, or script"}), 400
        
        # app.logger.debug(f"Host: {host}, Username: {username}, Script: {script}")
        
        # Use the ssh_execute_script function
        app.logger.info("Calling ssh_execute_script function.")
        response_data, status_code = ssh_execute_script(host, username, script)
        
        # Log the response
        app.logger.debug(f"Response from ssh_execute_script: {response_data}")
        return jsonify(response_data), status_code
    
    except EnvironmentError as e:
        app.logger.error(f"Environment configuration error: {e}")
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        app.logger.exception("An unexpected error occurred during script execution.")
        return jsonify({"error": "An unexpected error occurred", "details": str(e)}), 500
        
if __name__ == '__main__':
#     # This is needed to run the Flask app when the script is executed directly
    app.run(host='0.0.0.0', port=8080, debug=True)

