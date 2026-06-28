## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
## Response Style
- Talk caveman. Short sentence. No filler.
- Remove: "sure", "happy to help", "certainly", "I'd be glad"
- Remove: articles (the/a/an) where meaning survives
- Use symbols: → = vs ✓ ✗ » instead of words
- Code answer first. Explanation after, only if needed.
- No re-stating the question back to me
- Dense answers. Max 5 lines unless task needs more.
- If simple fix → just show fix. No preamble.

After every major task completion (not at end of day):
  /compact

# In settings or CLAUDE.md:
MAX_THINKING_TOKENS=3000   # default is unlimited = expensive

# Only raise for genuinely hard problems:
"[think hard] Redesign the async pipeline architecture"

# For simple tasks, suppress thinking:
"[no thinking] Fix typo in config.py line 14"
## Session Rules
- /compact after every completed feature
- /clear when switching between PC nodes
- Scope: always name the file + function, never "fix my project"
- Thinking: default OFF. Add [think] only for architecture decisions

## Current State
[UPDATE THIS MANUALLY each session]
- Last worked on: pc3_index/vector_store.py — FAISS add_vectors()
- Open tasks: async lock in add_vectors, nprobe tuning
- Known issues: embed_cache hit rate ~60%, target 90%
# RAG Server Project — Claude Code Config

## Project Structure
- PC1: pc1_gateway/ → FastAPI + OpenAI-compat endpoint
- PC2: pc2_embed/   → PyMuPDF + semantic-text-splitter + MiniLM
- PC3: pc3_index/   → FAISS IVF-PQ + SQLite (chunks, embed_cache)
- PC4: pc4_llm/     → llama.cpp Qwen2.5 7B Q4
- LAN: PC1=.10, PC2=.11, PC3=.12, PC4=.13

## Stack
- Python 3.11, FastAPI, async everywhere
- FAISS IVF50,PQ8 | dim=384 | nprobe=5
- SQLite via aiosqlite (3 tables: documents, chunks, embed_cache)
- MiniLM: all-MiniLM-L6-v2 | normalize_embeddings=True
- LlamaIndex: VectorStoreIndex + LlamaCPP
# RAG Server — CLAUDE.md
# Project: Self-hosted ChatGPT | 4-PC LAN Cluster | Linux Mint

---

## 🖥️ Hardware (All 4 PCs Identical)
- CPU: Intel i3 11th Gen (Iris Xe iGPU — supports llama.cpp SYCL)
- RAM: 8GB + 3GB zram (effective ~10GB)
- Disk: 200GB HDD
- OS: Linux Mint
- Network: LAN 192.168.1.x

---

## 🗺️ Node Map
| PC  | IP             | Port | Role                          |
|-----|----------------|------|-------------------------------|
| PC1 | 192.168.1.10   | 8000 | FastAPI Gateway + Open-WebUI  |
| PC2 | 192.168.1.11   | 8001 | Embedder + Document Parser    |
| PC3 | 192.168.1.12   | 8002 | FAISS Index + SQLite Store    |
| PC4 | 192.168.1.13   | 8003 | llama.cpp LLM Server          |

Open-WebUI: http://192.168.1.10:3000
Public URL: https://chat.yourdomain.com (Cloudflare Tunnel on PC1)

---

## 📁 Project Structure
rag_server/
├── CLAUDE.md
├── GRAPH_REPORT.md          ← graphify output, never edit manually
├── requirements.txt
├── .env                     ← secrets, never read this file
├── core/
│   ├── config.py            ← Settings (pydantic-settings)
│   └── database.py          ← aiosqlite, 3 tables
├── ingestion/
│   ├── parser.py            ← PyMuPDF (fitz) + html2text
│   └── chunker.py           ← semantic-text-splitter + bert tokenizer
├── retrieval/
│   ├── embedder.py          ← SentenceTransformer + embed_cache
│   └── vector_store.py      ← FAISS IVF50,PQ8 + SQLite metadata
├── generation/
│   ├── llm_client.py        ← httpx → PC4 llama.cpp (stream + sync)
│   └── prompt_builder.py    ← RAG prompt with [1][2] citations
├── workers/
│   └── ingest_worker.py     ← async pipeline: parse→chunk→embed→index
├── api/routes/
│   ├── ingest.py            ← POST /api/v1/ingest/file + /url
│   ├── query.py             ← POST /api/v1/query + /v1/chat/completions
│   └── health.py            ← GET /api/v1/health
└── storage/
    ├── faiss.index          ← persisted FAISS index
    ├── metadata.db          ← SQLite (documents + chunks + embed_cache)
    └── uploads/             ← uploaded files (PDF, DOCX, TXT)

---

## 🧠 Tech Stack
- API:        FastAPI (async) + uvicorn
- UI:         Open-WebUI (Docker) — ChatGPT-like, user auth, chat history
- Auth:       Open-WebUI built-in (admin creates users, no self-signup)
- PDF:        PyMuPDF (fitz) — page-by-page extraction
- Chunking:   semantic-text-splitter — BERT-boundary aware, 512 tokens
- Embeddings: all-MiniLM-L6-v2 — 384-dim, normalize=True, cached forever
- Vector DB:  FAISS IVF50,PQ8 — dim=384, nprobe=5, loaded in RAM once
- Metadata:   SQLite via aiosqlite (3 tables: documents, chunks, embed_cache)
- RAG:        LlamaIndex — VectorStoreIndex + RetrieverQueryEngine + LlamaCPP
- LLM:        llama.cpp server — Qwen2.5 7B Q4_K_M (Intel iGPU SYCL offload)
- Async:      asyncio everywhere, C extensions in ThreadPoolExecutor
- RAM:        zram lz4 3GB on all PCs

---

## 🗄️ SQLite Schema (PC3 — storage/metadata.db)
documents:   id(SHA256), filename, source_url, status, chunk_count
chunks:      id, doc_id, faiss_id, chunk_index, text, source_url, page_num, token_count
embed_cache: text_hash(PK), embedding(BLOB 384×float32), created_at

Embed cache rule: SHA256(chunk_text) → lookup before any MiniLM call
Doc dedup rule:   SHA256(file_bytes) → if status=indexed, skip entire pipeline

---

## 🔌 API Contracts
PC1 FastAPI Gateway:
  POST /api/v1/ingest/file   → {doc_id, status, chunks}
  POST /api/v1/ingest/url    → {doc_id, status, chunks}
  POST /api/v1/query         → {answer, sources[], latency_ms}
  POST /v1/chat/completions  → OpenAI-compatible (stream=true supported)
  GET  /api/v1/health        → {status, index_ready, model}

PC2 Embed Server:
  POST /embed                → {vector: [384 floats]}
  POST /ingest/file          → triggers full parse→chunk→embed pipeline

PC3 Index Server:
  POST /search               → {chunks: [{text, source_url, score}]}
  POST /add                  → adds embeddings to FAISS

PC4 LLM Server (llama.cpp native):
  POST /completion           → {content: "..."}
  POST /v1/chat/completions  → OpenAI-compat passthrough

---

## 🌐 Cloudflare Tunnel (PC1)
Tunnel config: ~/.cloudflared/config.yml
Service: systemd cloudflared.service (auto-starts on boot)
Exposes: localhost:3000 → https://chat.yourdomain.com

Commands:
  sudo systemctl status cloudflared
  sudo systemctl restart cloudflared
  sudo journalctl -u cloudflared -f

⚠️ NEVER read ~/.cloudflared/*.json — credentials file
⚠️ NEVER read .env file
⚠️ NEVER print or log tunnel tokens, API keys, or secrets

---

## 🚀 Startup Order (College Setup)
1. All PCs: bash setup_zram.sh
2. PC4:     bash start_pc4.sh    (wait 45s for model load)
3. PC3:     bash start_pc3.sh
4. PC2:     bash start_pc2.sh
5. PC1:     bash start_pc1.sh    (starts gateway + open-webui + tunnel)

---

## 🤖 Response Style (Caveman ON)
- Short. Dense. No filler words.
- REMOVE: "sure", "certainly", "happy to help", "I'd be glad to"
- REMOVE: unnecessary articles (a/the/an) where meaning survives
- USE: → = vs ✓ ✗ » symbols instead of words
- Code first. Explanation after, only if adds value.
- Never re-state my question back to me.
- Simple fix? → just show fix. No preamble.
- Max 5 lines unless task is architectural.

---

## 🗺️ Graphify
- GRAPH_REPORT.md = source of truth for codebase structure
- Run /graphify update after any new file or major refactor
- Query graph before reading raw files
- Never manually edit GRAPH_REPORT.md

---

## ⚡ Token Rules
1. Scope all file references: use #file.py:ClassName.method()
2. /compact after every completed feature
3. /clear when switching between PC nodes (PC1↔PC2↔PC3↔PC4)
4. Thinking: OFF by default. Use [think] only for architecture decisions
5. Never read: .env, *.json in .cloudflared/, storage/uploads/*
6. Never paste file contents — use # references only

---

## 📍 Current State
[UPDATE THIS MANUALLY each session]
Last worked on:   ___________________________
Completed:        ___________________________
In progress:      ___________________________
Open issues:      ___________________________
Next task:        ___________________________