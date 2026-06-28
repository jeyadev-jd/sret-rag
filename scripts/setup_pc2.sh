#!/bin/bash
set -eo pipefail

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

ok() { echo -e "${GREEN}[OK]${NC} $1"; }
fail() { echo -e "${RED}[FAIL]${NC} $1"; exit 1; }

echo "=== PC2: Embedder Setup ==="
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
pip install --upgrade pip --quiet --no-index --find-links wheels/pc2/ 2>/dev/null || true

# 4. Install packages (wheels first, then PyPI for missing)
ok "Installing packages..."
if [ "$(ls wheels/pc2/*.whl 2>/dev/null | wc -l)" -gt 0 ]; then
    pip install --no-index --find-links wheels/pc2/ -q -r pc2_embed/requirements.txt 2>/dev/null || true
fi

# Install any missing packages from PyPI (torch, transformers, sentence-transformers)
pip install -q -r pc2_embed/requirements.txt || fail "pip install failed"
ok "Packages installed (wheels + PyPI fallback)"

# 5. Setup MINILM model path
export MINILM_PATH="$(pwd)/models/minilm"
if [ ! -d "$MINILM_PATH" ]; then
    fail "Model not found at $MINILM_PATH — run prepare_offline.sh on PC1 first"
fi
ok "Model path: $MINILM_PATH"

# 6. Start service
ok "Starting PC2 embedder on port 8001..."
cd pc2_embed
MINILM_PATH="$MINILM_PATH" nohup python3 main.py > /tmp/pc2.log 2>&1 &
sleep 4

# 7. Health check
curl -sf http://localhost:8001/health &>/dev/null && ok "PC2 running on port 8001" || fail "PC2 failed — check /tmp/pc2.log"
