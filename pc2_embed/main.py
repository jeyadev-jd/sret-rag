import os
import tempfile
from pathlib import Path
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
import uvicorn
from embedder import Embedder
from parser import parse_document
from chunker import chunk_pages, chunk_text

app = FastAPI(title="PC2 Embedder Service")
embedder = None


@app.on_event("startup")
async def startup():
    global embedder
    model_path = os.getenv("MINILM_PATH", "../models/minilm")
    print(f"Loading model from: {model_path}")
    try:
        embedder = Embedder(model_path=model_path, normalize=True)
        print("✓ Embedder loaded")
    except Exception as e:
        print(f"✗ Failed to load model: {e}")
        raise


@app.get("/health")
async def health():
    return {"status": "ok", "model": "all-MiniLM-L6-v2", "embedder_ready": embedder is not None}


@app.post("/embed")
async def embed(body: dict):
    """Embed single text → [384 floats]"""
    if not embedder:
        return JSONResponse({"error": "Embedder not initialized"}, status_code=503)

    text = body.get("text", "")
    if not text:
        return JSONResponse({"error": "Missing 'text' field"}, status_code=400)

    try:
        vector = await embedder.embed_text(text)
        return {"vector": vector}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/ingest/file")
async def ingest_file(file: UploadFile = File(...)):
    """Parse file → chunk → embed each chunk → return chunks + embeddings"""
    if not embedder:
        return JSONResponse({"error": "Embedder not initialized"}, status_code=503)

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = Path(tmp.name)

        full_text, pages = await parse_document(tmp_path)

        if pages:
            chunks_list = await chunk_pages(pages, chunk_size=512, overlap=64)
        else:
            chunks_list_raw = await chunk_text(full_text, chunk_size=512, overlap=64)
            chunks_list = [{"text": c, "page_num": None, "chunk_index": i} for i, c in enumerate(chunks_list_raw)]

        embeddings = await embedder.embed_batch([c["text"] for c in chunks_list])

        result_chunks = []
        for i, chunk in enumerate(chunks_list):
            result_chunks.append({
                "text": chunk["text"],
                "embedding": embeddings[i],
                "page_num": chunk.get("page_num"),
                "source_url": file.filename,
                "chunk_index": chunk.get("chunk_index", i)
            })

        tmp_path.unlink()
        return {"chunks": result_chunks}

    except Exception as e:
        return JSONResponse({"error": str(e), "type": type(e).__name__}, status_code=500)


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8001))
    uvicorn.run(app, host="0.0.0.0", port=port, workers=1)
