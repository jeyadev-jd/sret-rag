#!/bin/bash
set -e

cd /home/jeyadev/offline_rag

MODEL_PATH="./models/phi-2.Q4_K_M.gguf"
LLAMA_BIN="./llama.cpp/build/bin/llama-server"
PORT="${1:-8003}"
THREADS="${2:-4}"
CONTEXT="${3:-2048}"

if [ ! -f "$MODEL_PATH" ]; then
    echo "Error: Model not found at $MODEL_PATH"
    exit 1
fi

if [ ! -x "$LLAMA_BIN" ]; then
    echo "Error: llama.cpp binary not found at $LLAMA_BIN"
    exit 1
fi

echo "Starting llama.cpp server..."
echo "Model: $MODEL_PATH"
echo "Port: $PORT"
echo "Threads: $THREADS"
echo "Context: $CONTEXT"

$LLAMA_BIN \
    -m "$MODEL_PATH" \
    -t "$THREADS" \
    -c "$CONTEXT" \
    -n 512 \
    --port "$PORT" \
    --host 0.0.0.0 \
    2>&1
