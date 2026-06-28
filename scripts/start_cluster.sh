#!/bin/bash
# start_cluster.sh
# This script starts the full multi-node RAG cluster locally for simulation.

cd ../project

echo "========================================="
echo " Starting Multi-Node RAG Cluster..."
echo "========================================="

echo "[1/4] Starting PC4 (LLM Server) on 8003..."
bash start_pc4.sh > /tmp/pc4.log 2>&1 &
sleep 5

echo "[2/4] Starting PC3 (Index Server) on 8002..."
bash start_pc3.sh > /tmp/pc3.log 2>&1 &
sleep 2

echo "[3/4] Starting PC2 (Embed Server) on 8001..."
bash start_pc2.sh > /tmp/pc2.log 2>&1 &
sleep 5

echo "[4/4] Starting PC1 (Gateway & Open-WebUI) on 8000/3000..."
bash start_pc1.sh > /tmp/pc1.log 2>&1 &

echo "========================================="
echo " Cluster started successfully!"
echo " Access the Chat UI at http://127.0.0.1:3000"
echo " Monitoring logs in /tmp/pc*.log..."
echo "========================================="
wait
