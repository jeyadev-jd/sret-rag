# Offline RAG Lab — Install Guide

---

## Step 1 — Do this on EVERY PC (one time only)

```bash
# 1. Copy files from USB
sudo mkdir -p ~/rag
sudo rsync -avh /media/$USER/*/offline_rag/ ~/rag/

# 2. Create Python environment
cd ~/rag
python3 -m venv venv
source venv/bin/activate
pip install --no-index --find-links=./wheels \
    torch sentence-transformers faiss-cpu \
    fastapi uvicorn httpx python-multipart PyMuPDF tqdm

# 3. Set up SSH key
mkdir -p ~/.ssh
cp ~/rag/ssh_keys/id_rsa ~/.ssh/
cp ~/rag/ssh_keys/authorized_keys ~/.ssh/
chmod 700 ~/.ssh && chmod 600 ~/.ssh/id_rsa ~/.ssh/authorized_keys
```

> ⚠️ Change `/media/$USER/*/offline_rag/` to your actual USB path if needed.
> Find it with: `ls /media/$USER/`

---

## Step 2 — Start each PC (one command each)

### PC1 (Orchestrator — runs the whole cluster)
```bash
bash ~/rag/project/start_cluster.sh
```
> This starts PC2, PC3, PC4 remotely via SSH, then starts PC1 itself.
> **Open browser at:** `http://192.168.1.10`

---

### PC2 (Embedding) — only if starting manually
```bash
bash ~/rag/project/start_pc2.sh
```

### PC3 (Retrieval) — only if starting manually
```bash
bash ~/rag/project/start_pc3.sh
```

### PC4 (LLM Server) — only if starting manually
```bash
bash ~/rag/project/start_pc4.sh
```

---

## Step 3 — First time on PC3 only (index your PDFs)

```bash
# Copy your PDFs into docs/
mkdir -p ~/rag/docs
cp /path/to/your/*.pdf ~/rag/docs/

# Process and index them
cd ~/rag/project
source ../venv/bin/activate
python3 pc3_process_docs.py --input ~/rag/docs --output chunks.txt
python3 build_index.py
# Done — creates docs.index
```

---

## Stop everything

```bash
bash ~/rag/project/stop_cluster.sh
```

## Check status

```bash
bash ~/rag/project/status_cluster.sh
```

---

## PC IP Addresses (fill in yours)

| PC | Role | IP |
|----|------|----|
| PC1 | Orchestrator | `192.168.1.___` |
| PC2 | Embedding | `192.168.1.___` |
| PC3 | Retrieval | `192.168.1.___` |
| PC4 | LLM Inference | `192.168.1.___` |

> Find IP: `hostname -I | awk '{print $1}'`

---

## Something broken?

| Problem | Fix |
|---------|-----|
| SSH asks for password | `chmod 600 ~/.ssh/id_rsa` |
| pip can't find a package | `ls ~/rag/wheels/` to check it's there |
| Port already in use | `sudo lsof -i :8000` then `sudo kill -9 <PID>` |
| llama-server missing | See PC4 note below |

### PC4 only — if `llama-server` is missing, rebuild it:
```bash
cd ~/rag/llama.cpp
cmake -B build -DGGML_BLAS=OFF -DCMAKE_BUILD_TYPE=Release
cmake --build build --config Release -j$(nproc)
# Takes ~10 min
```
