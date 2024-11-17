from datetime import timedelta
import uuid
from dotenv import load_dotenv
from flask import jsonify
from google.cloud import storage
import os
load_dotenv()
# Ensure the environment variable for GCP credentials is set (for local development)
def setup_gcp_client():
    # Check if the GOOGLE_APPLICATION_CREDENTIALS environment variable is set
    if 'GOOGLE_APPLICATION_CREDENTIALS' not in os.environ:
        raise EnvironmentError("GCP credentials not found. Set GOOGLE_APPLICATION_CREDENTIALS environment variable.")

    # Initialize the GCP Storage Client
    client = storage.Client()
    return client

# Create the client.conf file content
def create_client_conf(client_private_key, server_ip, server_public_key):
    client_conf_content = f"""[Interface]
PrivateKey = {client_private_key}
Address = 10.0.0.2/24
DNS = 1.1.1.1

[Peer]
PublicKey = {server_public_key}
Endpoint = {server_ip}:51820
AllowedIPs = 0.0.0.0/0
PersistentKeepalive = 25
"""
    return client_conf_content


# Main function to create the file and upload it
def create_and_upload_client_conf(client_private_key, server_ip, server_public_key, bucket_name,droplet_name):
    # Step 1: Create the client.conf content
    client_conf_content = create_client_conf(client_private_key, server_ip, server_public_key)

    # Initialize GCP Storage client
    storage_client = storage.Client()

    # Define folder structure inside GCP bucket
    folder_name = os.getenv("CONFIG_FOLDER")  # You can modify this folder name as needed
    file_name = f"{droplet_name}/client.conf"  # Path within the folder: droplet_name/client.conf

    # Upload the file content to the bucket
    bucket = storage_client.get_bucket(bucket_name)
    blob = bucket.blob(f"{folder_name}/{file_name}")  # Full object path including folder

    # Upload the client.conf file content
    blob.upload_from_string(client_conf_content)

        # Generate a signed URL with the Content-Disposition header to force download
    signed_url = blob.generate_signed_url(
        version="v4", 
        expiration=timedelta(hours=1),  # Signed URL valid for 1 hour
        method="GET",
        query_parameters={
            "response-content-disposition": "attachment; filename=client.conf"
        }
    )

    # Return the signed URL (this URL will trigger the download dialog box)
    return signed_url

def handle_ssh_response(response,droplet_name):
    # Extract required fields from the SSH response
    client_private_key = response.get("CLIENT_PRIVATE_KEY", "").strip()
    server_ip = response.get("SERVER_IP", "").strip()
    server_public_key = response.get("SERVER_PUBLIC_KEY", "").strip()
    
    # Validate that all attributes are present and not empty
    if client_private_key and server_ip and server_public_key:
        # All fields are valid, so call the function to create and upload the client.conf file
        bucket_name = os.getenv("GCP_BUCKET_NAME")  # Replace with your actual GCP bucket name

        # Call the function to create and upload client.conf
        public_url = create_and_upload_client_conf(client_private_key, server_ip, server_public_key, bucket_name, droplet_name)
        
        # Return success response with public URL
        return jsonify({"status": "success", "public_url": public_url}), 200
    else:
        # If any of the attributes are missing or empty, return an error response
        return jsonify({
            "status": "error",
            "message": "Missing or invalid attributes in response. Ensure CLIENT_PRIVATE_KEY, SERVER_IP, and SERVER_PUBLIC_KEY are provided."
        }), 400



# Example usage:
if __name__ == "__main__":
    client_private_key = "mNZmGfg0WRJaTdFM7OxdszuwxCfpyGVIugeE2ZNPrnY="
    server_ip = "159.223.231.69"
    server_public_key = "bhZSoK08C1kD9lmgcCwG2t2Cc/6DvcqVnui1V283bVs="
    bucket_name = "disposable-vpn"
    droplet_name = "testing"
    # Call the function to create and upload the client.conf file
    public_url = create_and_upload_client_conf(client_private_key, server_ip, server_public_key, bucket_name,droplet_name)
    
    print(f"Client configuration uploaded! Public URL: {public_url}")
