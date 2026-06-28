# Offline RAG Laboratory - Project Structure

This document provides an overview of the directories and files within the `offline_rag` project.

## 📂 Root Directory Overview

| Folder/File | Description |
| :--- | :--- |
| `project/` | The core application code, servers, and local deployment scripts. |
| `models/` | Storage for GGUF model files (TinyLlama, Qwen, Phi-2). |
| `llama.cpp/` | Local build of the llama.cpp engine for high-performance inference. |
| `docs/` | Destination folder for raw user documents (PDFs, TXTs). |
| `venv/` | Python virtual environment containing all dependencies. |
| `scripts/` | Management scripts for cluster orchestration. |
| `wheels/` | Offline Python packages for system setup without internet. |
| `debs/` | Offline Debian packages for system dependencies. |
| `INSTALL.md` | General installation and setup instructions. |

---

## 🛠️ Project Folder (`project/`)

This is where the RAG pipeline lives.

### Core Servers (The 4 Nodes)
*   **`pc1_orchestrator.py`**: The "Brain." It handles the web UI and coordinates requests between the Embedding, Retrieval, and LLM nodes.
*   **`pc2_embed_server.py`**: The "Vector Maker." Uses SentenceTransformers to turn text into mathematical vectors.
*   **`pc3_retrieval_server.py`**: The "Librarian." Uses FAISS to search for relevant chunks based on vector similarity.
*   **`pc4_llm_server.py`**: The "Speaker." Orchestrates the `llama-server` to generate human-like answers.
*   **`pc4_mock_llm.py`**: A fallback server used for testing when real model weights are missing.

### Knowledge Base Tools
*   **`pc3_process_docs.py`**: Splits raw text and PDFs into small, readable chunks.
*   **`build_index.py`**: Creates the `docs.index` (FAISS database) from processed chunks.
*   **`chunks.txt`**: A plaintext storage of all processed document parts.
*   **`docs.index`**: The binary FAISS file used for lightning-fast retrieval.

### Frontend (ChatGPT UI)
*   **`static/`**: Contains `index.html`, `style.css`, and `script.js` for the ChatGPT-replica interface.

### Deployment & Testing
*   **`start_all_local.sh`**: One-click script to launch the full RAG system on a single machine (localhost).
*   **`tests/`**: Comprehensive `pytest` suite covering every component of the pipeline.
*   **`pc1_health_check.py`**: Monitor tool to check the UP/DOWN status of all nodes.

---

## 🚀 Key Commands

### Run Locally (Single Machine)
```bash
cd project
./start_all_local.sh
```

### Run Tests
```bash
pytest project/tests/ -v
```

### Add New Documents
1. Copy file to `project/`.
2. `python3 pc3_process_docs.py your_file.pdf`
3. `python3 build_index.py`
