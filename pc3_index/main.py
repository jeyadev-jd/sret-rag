import os
import asyncio
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import aiosqlite
import uvicorn
from vector_store import VectorStore

app = FastAPI(title="PC3 Index Service")
vector_store = None
db = None
db_path = Path("./storage/metadata.db")


@app.on_event("startup")
async def startup():
    global vector_store, db

    db_path.parent.mkdir(parents=True, exist_ok=True)
    db = await aiosqlite.connect(str(db_path))
    await db.execute("PRAGMA journal_mode=WAL")

    await db.executescript("""
        CREATE TABLE IF NOT EXISTS chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            doc_id TEXT NOT NULL,
            text TEXT NOT NULL,
            source_url TEXT,
            page_num INTEGER,
            faiss_id INTEGER,
            chunk_index INTEGER,
            token_count INTEGER
        );
        CREATE INDEX IF NOT EXISTS idx_chunks_doc ON chunks(doc_id);
        CREATE INDEX IF NOT EXISTS idx_chunks_faiss ON chunks(faiss_id);
    """)
    await db.commit()

    vector_store = VectorStore(
        index_path=Path("./storage/faiss.index"),
        embedding_dim=384,
        nlist=50,
        m=8
    )
    await vector_store.init(db)
    print("✓ Vector store initialized")


@app.get("/health")
async def health():
    if not vector_store or not vector_store.index:
        return JSONResponse({"status": "error"}, status_code=503)
    return {
        "status": "ok",
        "total_vectors": vector_store.index.ntotal if vector_store.index else 0,
        "db_ready": db is not None
    }


@app.post("/search")
async def search(body: dict):
    """Search FAISS for similar vectors"""
    if not vector_store or not db:
        return JSONResponse({"error": "Service not ready"}, status_code=503)

    vector = body.get("vector", [])
    top_k = body.get("top_k", 5)

    if not vector or len(vector) != 384:
        return JSONResponse({"error": "Invalid vector (must be 384 dims)"}, status_code=400)

    try:
        chunks = await vector_store.search(vector, top_k, db)
        return {"chunks": chunks}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/add")
async def add_vectors(body: dict):
    """Add chunks + embeddings to index"""
    if not vector_store or not db:
        return JSONResponse({"error": "Service not ready"}, status_code=503)

    chunks = body.get("chunks", [])
    if not chunks:
        return JSONResponse({"error": "No chunks provided"}, status_code=400)

    try:
        embeddings = []
        chunk_ids = []

        for i, chunk in enumerate(chunks):
            chunk_text = chunk.get("text", "")
            embedding = chunk.get("embedding", [])
            doc_id = chunk.get("doc_id", "unknown")
            page_num = chunk.get("page_num")
            source_url = chunk.get("source_url", "")
            chunk_index = chunk.get("chunk_index", i)

            cursor = await db.execute(
                "INSERT INTO chunks (doc_id, text, source_url, page_num, chunk_index, token_count) VALUES (?, ?, ?, ?, ?, ?)",
                (doc_id, chunk_text, source_url, page_num, chunk_index, len(chunk_text.split()))
            )
            chunk_id = cursor.lastrowid
            chunk_ids.append(chunk_id)
            embeddings.append(embedding)

        await db.commit()
        await vector_store.add_vectors(embeddings, chunk_ids, db)

        return {"added": len(chunks), "total_vectors": vector_store.index.ntotal}
    except Exception as e:
        await db.rollback()
        return JSONResponse({"error": str(e), "type": type(e).__name__}, status_code=500)


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8002))
    uvicorn.run(app, host="0.0.0.0", port=port, workers=1)
