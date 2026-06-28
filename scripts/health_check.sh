#!/bin/bash

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

ok() { echo -e "${GREEN}[✓]${NC} $1"; }
fail() { echo -e "${RED}[✗]${NC} $1"; }

PC1_IP="${1:-127.0.0.1}"
SUBNET=$(echo $PC1_IP | cut -d. -f1-3)

echo "=== Health Check ==="
echo "PC1 IP: $PC1_IP"
echo ""

# Try each service
for port in 8000 8001 8002 8003; do
    if curl -sf "http://$PC1_IP:$port/health" &>/dev/null; then
        case $port in
            8000) ok "PC1 Gateway: http://$PC1_IP:$port" ;;
            8001) ok "PC2 Embedder: http://$SUBNET.11:$port" ;;
            8002) ok "PC3 Index: http://$SUBNET.12:$port" ;;
            8003) ok "PC4 LLM: http://$SUBNET.13:$port" ;;
        esac
    else
        case $port in
            8000) fail "PC1 Gateway: http://$PC1_IP:$port" ;;
            8001) fail "PC2 Embedder: http://$SUBNET.11:$port" ;;
            8002) fail "PC3 Index: http://$SUBNET.12:$port" ;;
            8003) fail "PC4 LLM: http://$SUBNET.13:$port" ;;
        esac
    fi
done

echo ""
echo "Done."
