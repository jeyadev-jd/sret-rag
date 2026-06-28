#!/bin/bash
set -eo pipefail

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

ok() { echo -e "${GREEN}[OK]${NC} $1"; }
fail() { echo -e "${RED}[FAIL]${NC} $1"; exit 1; }

echo "=== PC3: Index Setup ==="
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
pip install --upgrade pip --quiet --no-index --find-links wheels/pc3/ 2>/dev/null || true

# 4. Install packages (wheels first, then PyPI for missing)
ok "Installing packages..."
if [ "$(ls wheels/pc3/*.whl 2>/dev/null | wc -l)" -gt 0 ]; then
    pip install --no-index --find-links wheels/pc3/ -q -r pc3_index/requirements.txt 2>/dev/null || true
fi
pip install -q -r pc3_index/requirements.txt || fail "pip install failed"

# 5. Create storage dir
mkdir -p pc3_index/storage
ok "Storage dir ready"

# 6. Start service
ok "Starting PC3 index on port 8002..."
cd pc3_index
nohup python3 main.py > /tmp/pc3.log 2>&1 &
sleep 4

# 7. Health check
curl -sf http://localhost:8002/health &>/dev/null && ok "PC3 running on port 8002" || fail "PC3 failed — check /tmp/pc3.log"
