#!/bin/bash
set -eo pipefail

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

ok() { echo -e "${GREEN}[OK]${NC} $1"; }
fail() { echo -e "${RED}[FAIL]${NC} $1"; exit 1; }

echo "=== PC1: Gateway Setup ==="
cd "$(dirname "$0")/.."

# 1. Install system deps if needed
python3.12 --version &>/dev/null || {
    ok "Installing python3.12..."
    sudo dpkg -i debs/*.deb 2>/dev/null || sudo apt-get install -f -y --no-download 2>/dev/null || true
}

# 2. Create venv
[ -d venv ] || {
    ok "Creating venv..."
    python3.12 -m venv venv
}

source venv/bin/activate

# 3. Upgrade pip
ok "Upgrading pip..."
pip install --upgrade pip --quiet --no-index --find-links wheels/common/ 2>/dev/null || true

# 4. Install packages (wheels first, then PyPI for missing)
ok "Installing packages..."
if [ "$(ls wheels/pc1/*.whl 2>/dev/null | wc -l)" -gt 0 ]; then
    pip install --no-index --find-links wheels/pc1/ -q -r rag_server/requirements_pc1.txt 2>/dev/null || true
fi
pip install -q -r rag_server/requirements_pc1.txt || fail "pip install failed"

# 5. Auto-detect own IP
MY_IP=$(ip route get 1 2>/dev/null | awk '{print $7; exit}' || echo "127.0.0.1")
ok "My IP: $MY_IP"

# 6. Scan LAN for peer services (takes ~20s)
echo "Scanning LAN for services (timeout 20s)..."
PC2_IP="192.168.140.232"
PC3_IP="192.168.140.232"
PC4_IP="192.168.140.82"
SUBNET=$(echo $MY_IP | cut -d. -f1-3)

SCAN_RESULTS=$(timeout 20 bash -c "
for i in \$(seq 1 254); do
    IP=\"$SUBNET.\$i\"
    [ \"\$IP\" = \"$MY_IP\" ] && continue
    (timeout 1 bash -c \"</dev/null >/dev/tcp/\$IP/8001\" 2>/dev/null && echo \"2 \$IP\") &
    (timeout 1 bash -c \"</dev/null >/dev/tcp/\$IP/8002\" 2>/dev/null && echo \"3 \$IP\") &
    (timeout 1 bash -c \"</dev/null >/dev/tcp/\$IP/8003\" 2>/dev/null && echo \"4 \$IP\") &
done
wait
" 2>/dev/null)

while read pc ip; do
    case $pc in
        2) PC2_IP="$ip" ;;
        3) PC3_IP="$ip" ;;
        4) PC4_IP="$ip" ;;
    esac
done <<< "$SCAN_RESULTS"

[ -n "$PC2_IP" ] && ok "PC2 found: $PC2_IP:8001" || echo "⚠ PC2 not found (start setup_pc2.sh first)"
[ -n "$PC3_IP" ] && ok "PC3 found: $PC3_IP:8002" || echo "⚠ PC3 not found (start setup_pc3.sh first)"
[ -n "$PC4_IP" ] && ok "PC4 found: $PC4_IP:8003" || echo "⚠ PC4 not found (start setup_pc4.sh first)"

# 7. Write .env (preserve existing values if LAN scan missed a peer)
mkdir -p rag_server
EXISTING_PC2=$(grep -o 'PC2_URL=.*' rag_server/.env 2>/dev/null | cut -d= -f2-)
EXISTING_PC3=$(grep -o 'PC3_URL=.*' rag_server/.env 2>/dev/null | cut -d= -f2-)
EXISTING_PC4=$(grep -o 'PC4_URL=.*' rag_server/.env 2>/dev/null | cut -d= -f2-)

FINAL_PC2=${PC2_IP:+http://$PC2_IP:8001}
FINAL_PC2=${FINAL_PC2:-${EXISTING_PC2:-http://127.0.0.1:8001}}
FINAL_PC3=${PC3_IP:+http://$PC3_IP:8002}
FINAL_PC3=${FINAL_PC3:-${EXISTING_PC3:-http://127.0.0.1:8002}}
FINAL_PC4=${PC4_IP:+http://$PC4_IP:8003}
FINAL_PC4=${FINAL_PC4:-${EXISTING_PC4:-http://127.0.0.1:8003}}

cat > rag_server/.env << EOF
PC2_URL=$FINAL_PC2
PC3_URL=$FINAL_PC3
PC4_URL=$FINAL_PC4
LLM_MODEL=qwen2.5-1.5b
EOF
ok ".env written: PC2=$FINAL_PC2 PC3=$FINAL_PC3 PC4=$FINAL_PC4"

# 8. Kill any existing process on 8000
lsof -ti:8000 2>/dev/null | xargs kill -9 2>/dev/null || true
sleep 1

# 9. Start PC1 gateway
ok "Starting PC1 gateway on port 8000..."
cd rag_server
nohup python3 main.py > /tmp/pc1.log 2>&1 &
sleep 4

# 10. Health check
if curl -sf http://localhost:8000/api/v1/health &>/dev/null; then
    ok "PC1 gateway running on port 8000"
else
    fail "PC1 failed to start — check /tmp/pc1.log"
fi
