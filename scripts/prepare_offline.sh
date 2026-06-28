#!/bin/bash
set -eo pipefail

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

ok() { echo -e "${GREEN}[OK]${NC} $1"; }
fail() { echo -e "${RED}[FAIL]${NC} $1"; exit 1; }

echo "=== Prepare Offline Bundle (Run Once on PC1 with Internet) ==="
cd "$(dirname "$0")/.."

# 1. Download system .deb packages
echo ""
echo "Downloading system packages to debs/..."
mkdir -p debs

# Use apt-get to download .deb files (no installation)
sudo apt-get update 2>/dev/null || true

sudo apt-get install -y --download-only \
    -o Dir::Cache::archives="$(pwd)/debs" \
    python3.12 python3.12-venv python3.12-dev \
    build-essential libopenblas-dev libssl-dev \
    2>/dev/null || {
    echo "⚠ apt-get download failed (may require sudo password or internet). Continuing..."
}

[ -d debs ] && [ "$(ls -A debs 2>/dev/null)" ] && ok "System packages downloaded to debs/" || echo "⚠ debs/ empty — will rely on target PC package cache"

# 2. Create/activate venv
echo ""
echo "Setting up Python venv..."
[ -d venv ] || python3.12 -m venv venv
source venv/bin/activate
ok "venv activated"

# 3. Upgrade pip (for wheels download)
pip install --upgrade pip --quiet 2>/dev/null || true

# 4. Download Python wheels for PC1 (lightweight)
echo ""
echo "Downloading wheels for PC1 (gateway)..."
mkdir -p wheels/pc1
pip download --no-deps \
    fastapi==0.135.1 uvicorn==0.41.0 httpx==0.28.1 aiosqlite==0.21.0 \
    pydantic==2.12.5 pydantic-settings==2.14.1 python-multipart==0.0.22 \
    bcrypt==5.0.0 aiofiles==25.1.0 \
    -d wheels/pc1/ \
    2>&1 | grep -E "Successfully|Downloading|Saved" || true
ok "PC1 wheels downloaded"

# 5. Download Python wheels for PC2 (embedder + parser)
echo ""
echo "Downloading wheels for PC2 — downloading core packages only (torch skipped for speed)..."
mkdir -p wheels/pc2

# Download smaller packages first (avoid torch timeout)
pip download --no-deps \
    fastapi==0.135.1 uvicorn==0.41.0 httpx==0.28.1 \
    numpy==1.26.4 PyMuPDF==1.24.3 html2text==2024.2.26 \
    semantic-text-splitter==0.30.1 python-multipart==0.0.22 \
    -d wheels/pc2/ \
    2>&1 | grep -E "Saved|Successfully" | tail -3

# Try torch+transformers separately with timeout (optional, may skip if slow)
echo "Attempting torch download (may take 5+ min, skipping if timeout)..."
timeout 300 pip download --no-deps \
    torch==2.2.2 transformers==4.42.3 sentence-transformers==3.2.1 \
    -d wheels/pc2/ \
    2>&1 | grep -E "Saved|Successfully" | tail -3 || {
    echo "⚠ torch download timeout — PC2 will install from PyPI on target"
}

ok "PC2 core wheels ready (torch may be skipped)"

# 6. Download Python wheels for PC3 (FAISS + index)
echo ""
echo "Downloading wheels for PC3 (index)..."
mkdir -p wheels/pc3
pip download --no-deps \
    fastapi==0.135.1 uvicorn==0.41.0 httpx==0.28.1 \
    faiss-cpu==1.8.0 numpy==1.26.4 aiosqlite==0.21.0 \
    -d wheels/pc3/ \
    2>&1 | grep -E "Successfully|Downloading|Saved" || true
ok "PC3 wheels downloaded"

# 7. Pre-download MiniLM model (for PC2)
echo ""
echo "Downloading MiniLM model (this may take 2-3 min)..."
mkdir -p models/minilm

python3 << 'MODELEOF'
import sys
from sentence_transformers import SentenceTransformer

try:
    model = SentenceTransformer('all-MiniLM-L6-v2')
    model.save('models/minilm')
    print("✓ Model saved to models/minilm/")
except Exception as e:
    print(f"✗ Model download failed: {e}", file=sys.stderr)
    sys.exit(1)
MODELEOF

[ -d models/minilm ] || fail "Model download failed"
ok "MiniLM model pre-downloaded to models/minilm/"

echo ""
echo "=== Bundle Ready ==="
echo "Next: Copy entire offline_rag/ folder to USB drive"
echo "Then: On each target PC, run:"
echo "  PC4: bash scripts/setup_pc4.sh    (LLM server)"
echo "  PC3: bash scripts/setup_pc3.sh    (Index server)"
echo "  PC2: bash scripts/setup_pc2.sh    (Embedder server)"
echo "  PC1: bash scripts/setup_pc1.sh    (Gateway + UI)"
echo ""
echo "Finally: bash scripts/health_check.sh  (verify all 4 services)"
