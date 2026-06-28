#!/bin/bash
set -eo pipefail

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

ok() { echo -e "${GREEN}[OK]${NC} $1"; }
fail() { echo -e "${RED}[FAIL]${NC} $1"; exit 1; }

echo "=== PC4: LLM Server Setup ==="
cd "$(dirname "$0")/.."

# Check for llama.cpp binary
if [ ! -f "llama.cpp/build/bin/llama-server" ]; then
    fail "llama-server binary not found at llama.cpp/build/bin/llama-server"
fi
ok "llama-server binary found"

# Find best model
MODEL=""
for m in models/qwen2.5-1.5b-instruct-q4_k_m.gguf models/qwen2.5-1.5b-instruct*.gguf models/phi-2*.gguf models/tinyllama*.gguf; do
    if [ -f "$m" ]; then
        MODEL="$m"
        break
    fi
done

[ -n "$MODEL" ] || fail "No GGUF model found in models/"
ok "Using model: $MODEL"

# Kill existing llama-server on 8003
lsof -ti:8003 2>/dev/null | xargs kill -9 2>/dev/null || true
sleep 1

# Start llama.cpp server
ok "Starting llama-server on port 8003..."
nohup ./llama.cpp/build/bin/llama-server \
    -m "$MODEL" \
    --port 8003 \
    --host 0.0.0.0 \
    -t 4 \
    -c 2048 \
    -n 512 \
    > /tmp/pc4.log 2>&1 &

sleep 5

# Health check
if curl -sf http://localhost:8003/health &>/dev/null; then
    ok "PC4 llama-server running on port 8003"
else
    fail "PC4 failed to start — check /tmp/pc4.log"
fi
