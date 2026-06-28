#!/bin/bash
set -e

cd /home/jeyadev/offline_rag

MODEL="${1:-phi-2}"
PORT="${2:-8003}"

case "$MODEL" in
    "phi-2")
        MODEL_PATH="./models/phi-2.Q4_K_M.gguf"
        echo "Starting phi-2 (1.7GB, best quality)"
        ;;
    "qwen2.5-1.5b"|"qwen")
        MODEL_PATH="./models/qwen2.5-1.5b-instruct-q4_k_m.gguf"
        echo "Starting qwen2.5-1.5b (1.1GB, faster)"
        ;;
    "tinyllama"|"tiny")
        MODEL_PATH="./models/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf"
        echo "Starting tinyllama-1.1b (638MB, fastest)"
        ;;
    *)
        echo "Unknown model: $MODEL"
        echo "Usage: $0 {phi-2|qwen|tinyllama} [port]"
        exit 1
        ;;
esac

if [ ! -f "$MODEL_PATH" ]; then
    echo "Error: Model not found at $MODEL_PATH"
    exit 1
fi

echo "Port: $PORT"
echo ""

./llama.cpp/build/bin/llama-server \
    -m "$MODEL_PATH" \
    --port "$PORT" \
    --host 0.0.0.0 \
    -t 4 \
    -c 2048 \
    -n 512 \
    2>&1
