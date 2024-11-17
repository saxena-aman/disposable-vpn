#!/bin/bash

# Install qrencode if not already installed
apt update
apt install -y qrencode

# Generate QR code in terminal
echo "Terminal QR Code:"
qrencode -t ansiutf8 < /root/client.conf

# Generate QR code as PNG file
qrencode -t png -o wireguard-config.png < /root/client.conf

echo "QR code has been saved as wireguard-config.png"
