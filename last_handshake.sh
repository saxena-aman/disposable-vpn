#!/bin/bash
set -e

# Ensure WireGuard tools are installed
if ! command -v wg > /dev/null; then
  echo '{"status": "error", "message": "WireGuard is not installed."}'
  exit 1
fi

# Extract information from `wg` command
WG_INTERFACE="wg0"

# Check if the interface exists
if ! wg show $WG_INTERFACE > /dev/null 2>&1; then
  echo "{\"status\": \"error\", \"message\": \"WireGuard interface $WG_INTERFACE does not exist.\"}"
  exit 1
fi

# Extract relevant keys
CLIENT_PRIVATE_KEY=$(cat /etc/wireguard/client_private.key 2>/dev/null || echo "N/A")
SERVER_PUBLIC_KEY=$(cat /etc/wireguard/server_public.key 2>/dev/null || echo "N/A")
SERVER_IP=$(curl -s ifconfig.me || echo "N/A")

# Extract last handshake time for the peer
LAST_HANDSHAKE_RAW=$(wg show $WG_INTERFACE latest-handshakes)
CURRENT_TIME=$(date +%s) # Get current Unix timestamp
LAST_HANDSHAKE="No handshake data available"

# Parse handshake timestamp if available
if [ -n "$LAST_HANDSHAKE_RAW" ]; then
  LAST_HANDSHAKE_TIME=$(echo "$LAST_HANDSHAKE_RAW" | awk '{print $2}')
  if [ "$LAST_HANDSHAKE_TIME" != "0" ]; then
    LAST_HANDSHAKE=$((CURRENT_TIME - LAST_HANDSHAKE_TIME))
  fi
fi

# Format as JSON
cat <<EOF
{
  "ip": "${SERVER_IP}",
  "last_handshake_seconds": "${LAST_HANDSHAKE}"
}
EOF
