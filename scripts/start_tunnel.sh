#!/bin/bash
set -e

if [ -z "$CLOUDFLARE_TUNNEL_TOKEN" ]; then
    echo "Error: CLOUDFLARE_TUNNEL_TOKEN not set in .env"
    exit 1
fi

echo "Starting Cloudflare tunnel..."
cloudflared tunnel run --token "$CLOUDFLARE_TUNNEL_TOKEN"
