#!/bin/bash
sudo apt update

# Install WireGuard
sudo apt install -y wireguard-tools wireguard

# Ensure the /etc/wireguard directory exists
mkdir -p /etc/wireguard
chmod 700 /etc/wireguard

# Enable IP forwarding
echo "net.ipv4.ip_forward=1" >> /etc/sysctl.conf
sysctl -p

# Generate server and client keys
umask 077
wg genkey | tee /etc/wireguard/server_private.key | wg pubkey > /etc/wireguard/server_public.key
wg genkey | tee /etc/wireguard/client_private.key | wg pubkey > /etc/wireguard/client_public.key

# Get server private and client public keys
SERVER_PRIVATE_KEY=$(cat /etc/wireguard/server_private.key)
CLIENT_PUBLIC_KEY=$(cat /etc/wireguard/client_public.key)

# Create WireGuard server configuration
cat > /etc/wireguard/wg0.conf << EOF
[Interface]
PrivateKey = ${SERVER_PRIVATE_KEY}
Address = 10.0.0.1/24
ListenPort = 51820
PostUp = iptables -A FORWARD -i wg0 -j ACCEPT; iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
PostDown = iptables -D FORWARD -i wg0 -j ACCEPT; iptables -t nat -D POSTROUTING -o eth0 -j MASQUERADE

[Peer]
PublicKey = ${CLIENT_PUBLIC_KEY}
AllowedIPs = 10.0.0.2/32
EOF

# Enable and start WireGuard
systemctl enable wg-quick@wg0
systemctl start wg-quick@wg0

# Generate client configuration
CLIENT_PRIVATE_KEY=$(cat /etc/wireguard/client_private.key)
SERVER_PUBLIC_KEY=$(cat /etc/wireguard/server_public.key)
SERVER_IP=$(curl -s ifconfig.me)

cat > /root/client.conf << EOF
[Interface]
PrivateKey = ${CLIENT_PRIVATE_KEY}
Address = 10.0.0.2/24
DNS = 1.1.1.1

[Peer]
PublicKey = ${SERVER_PUBLIC_KEY}
Endpoint = ${SERVER_IP}:51820
AllowedIPs = 0.0.0.0/0
PersistentKeepalive = 25
EOF

echo "WireGuard installation completed!"
echo "Client configuration is saved in /root/client.conf"
echo "CLIENT_PRIVATE_KEY=${CLIENT_PRIVATE_KEY}"
echo "SERVER_PUBLIC_KEY=${SERVER_PUBLIC_KEY}"
echo "SERVER_IP=${SERVER_IP}"
