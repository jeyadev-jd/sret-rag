# 4-PC Offline RAG Setup Guide

## Overview
Split RAG system across 4 identical PCs on a LAN. **No internet required on target PCs.** All dependencies pre-downloaded as .whl files. Setup is completely automated — each PC runs 1 script, done.

**Hardware:** Linux Mint 22.3, Intel i3 11th Gen, 8GB RAM, 200GB HDD (per PC)
**Network:** LAN 192.168.1.x (auto-detected, no manual IP config needed)

---

## Step 0: Prepare Offline Bundle (PC1, while internet available)

Run this **once** on PC1 while connected to internet. Downloads all packages + model.

```bash
cd /path/to/offline_rag
bash scripts/prepare_offline.sh
```

**What this does:**
1. Downloads system .deb packages (python3.12, build-essential, etc) → `debs/`
2. Downloads Python wheels for PC1 → `wheels/pc1/` (FastAPI, uvicorn, etc)
3. Downloads Python wheels for PC2 → `wheels/pc2/` (core packages; torch/transformers optional)
4. Downloads Python wheels for PC3 → `wheels/pc3/` (FAISS, numpy, FastAPI)
5. Pre-downloads MiniLM model → `models/minilm/` (~88MB, 2-3 min)

**Note:** torch/transformers are large (~2GB). If download times out, they're skipped. Target PC2 will install from PyPI (requires internet on target).

**Expected output:**
```
[OK] venv activated
[OK] PC1 wheels downloaded
[OK] PC2 core wheels ready (torch may be skipped)
[OK] PC3 wheels downloaded
[OK] MiniLM model pre-downloaded to models/minilm/
```

Once done, copy entire `offline_rag/` folder to USB drive.

---

## Step 1: Copy to All 4 PCs

1. Insert USB into each PC
2. Copy `offline_rag/` folder to `/home/<user>/` (or wherever)
3. Open terminal in that directory

Example:
```bash
cp -r /media/usb/offline_rag ~/
cd ~/offline_rag
```

---

## Step 2: Run Setup Scripts (Startup Order)

Run on **each PC in this order**. Scripts auto-detect IP, scan LAN for peers, install packages, start services.

### PC4 (LLM Server) — Run First
```bash
bash scripts/setup_pc4.sh
# Waits 5s for llama-server to start
# Expected: [OK] PC4 llama-server running on port 8003
```

**Time:** ~15-20s (model loads at startup)

### PC3 (Index Server) — Run Second
```bash
bash scripts/setup_pc3.sh
# Expected: [OK] PC3 running on port 8002
```

**Time:** ~30-40s (includes LAN scan to find PC4)

### PC2 (Embedder Server) — Run Third
```bash
bash scripts/setup_pc2.sh
# Expected: [OK] PC2 running on port 8001
```

**Time:** ~30-40s (model loads from `models/minilm/`)

### PC1 (Gateway) — Run Last
```bash
bash scripts/setup_pc1.sh
# Scans LAN for PC2/PC3/PC4
# Expected: [OK] PC1 gateway running on port 8000
```

**Time:** ~40-50s (LAN scan takes ~20s)

---

## Step 3: Verify All Services Running

```bash
bash scripts/health_check.sh
```

Expected output:
```
=== Health Check ===
PC1 IP: 192.168.1.10

[✓] PC1 Gateway: http://192.168.1.10:8000
[✓] PC2 Embedder: http://192.168.1.11:8001
[✓] PC3 Index: http://192.168.1.12:8002
[✓] PC4 LLM: http://192.168.1.13:8003

Done.
```

---

## Architecture

| PC  | IP              | Port | Role              | Service        | Status File |
|-----|-----------------|------|-------------------|----------------|-------------|
| PC4 | 192.168.1.13    | 8003 | LLM (llama.cpp)   | llama-server   | /tmp/pc4.log |
| PC3 | 192.168.1.12    | 8002 | Index (FAISS)     | uvicorn        | /tmp/pc3.log |
| PC2 | 192.168.1.11    | 8001 | Embedder (MiniLM) | uvicorn        | /tmp/pc2.log |
| PC1 | 192.168.1.10    | 8000 | Gateway (FastAPI) | uvicorn + UI   | /tmp/pc1.log |

---

## Data Flow

```
User Query (PC1)
  ↓
[PC1] Embed query text → [PC2] /embed → cache in SQLite
  ↓
[PC1] Search vectors → [PC3] /search → find similar chunks
  ↓
[PC1] Prompt LLM → [PC4] /v1/chat/completions → stream response
  ↓
[PC1] Return answer + sources
```

---

## Troubleshooting

### "PC4 failed to start — check /tmp/pc4.log"
```bash
tail -f /tmp/pc4.log
```
Likely: No llama.cpp binary. Verify:
```bash
ls -la llama.cpp/build/bin/llama-server
```

### "PC3 failed to start — check /tmp/pc3.log"
```bash
tail -f /tmp/pc3.log
```
Common issues: missing FAISS library. Verify pip install:
```bash
pip list | grep faiss
```

### "PC2 failed to start — check /tmp/pc2.log"
```bash
tail -f /tmp/pc2.log
```
Common issues: model not found at `models/minilm/`. Verify:
```bash
ls -la models/minilm/
```

### "PC1 failed to start — check /tmp/pc1.log"
```bash
tail -f /tmp/pc1.log
```
PC1 tries to find PC2/PC3/PC4 via LAN scan. Make sure they're running first:
```bash
bash scripts/health_check.sh
```

### LAN Scan Fails / Wrong IPs
Scripts auto-detect IP and scan 192.168.1.1-254 for open ports 8001/8002/8003.

If your network uses a different subnet (e.g., 10.x.x.x):
1. Check your IP: `ip route get 1`
2. Edit `setup_pc1.sh` line ~45 to change SUBNET extraction if needed
3. Or manually set `PC2_URL`, `PC3_URL`, `PC4_URL` in `rag_server/.env`

---

## Access

Once PC1 gateway is running:

- **API endpoint:** `http://192.168.1.10:8000/api/v1/query`
- **Health check:** `http://192.168.1.10:8000/api/v1/health`
- **Upload document:** `POST http://192.168.1.10:8000/api/v1/ingest/file`

Example query:
```bash
curl -X POST http://192.168.1.10:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query":"What is machine learning?"}'
```

---

## Offline Installation Notes

✓ **Core dependencies pre-downloaded:**
  - `.deb` system packages → `debs/`
  - `.whl` Python packages → `wheels/pc1/`, `wheels/pc2/`, `wheels/pc3/`
  - MiniLM model → `models/minilm/` (ALWAYS downloaded, required for PC2)

✓ **Hybrid approach:**
  - Setup scripts try wheels first: `pip install --no-index --find-links wheels/pcX/`
  - Fallback to PyPI automatically if wheels missing or incomplete
  - Tolerates both fully offline (wheels complete) and semi-offline (PyPI + wheels) scenarios

⚠ **Requirements:**
  - PC1: internet available for `prepare_offline.sh` (5-10 min, one-time)
  - Target PCs: can work offline IF wheels complete; falls back to PyPI if needed

---

## FAQ

**Q: Can I run setup scripts in parallel?**
A: No. Run them in order (PC4 → PC3 → PC2 → PC1). Each depends on previous.

**Q: What if IP detection fails?**
A: Edit `rag_server/.env` manually and set:
```
PC2_URL=http://192.168.1.11:8001
PC3_URL=http://192.168.1.12:8002
PC4_URL=http://192.168.1.13:8003
```

**Q: Can I use different models on PC4?**
A: Yes. `setup_pc4.sh` auto-selects best `.gguf` model from `models/` dir.
Priority: qwen2.5-1.5b > qwen2.5 → phi-2 → tinyllama

**Q: How much disk space do I need?**
A: ~1.5GB per PC after installation:
  - PC1: 300MB (FastAPI gateway only)
  - PC2: 500MB (MiniLM model)
  - PC3: 300MB (FAISS index, grows with data)
  - PC4: 400MB (LLM model)

**Q: How to stop all services?**
A: Kill nohup processes:
```bash
killall llama-server  # PC4
killall python3       # PC1/PC2/PC3
```

Or: `pkill -f "python.*main.py"`
