import hashlib
import aiosqlite
import httpx
from pathlib import Path
from core.config import Settings
from core.database import get_db
from retrieval.vector_store import VectorStore


class IngestWorker:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = httpx.AsyncClient(timeout=120)
        self.vector_store = None
        self.pc2_url = settings.pc2_url

    async def init(self) -> None:
        """Initialize vector store (PC3)."""
        self.vector_store = VectorStore(self.settings)
        await self.vector_store.init()

    async def ingest_file(self, file_path: Path) -> dict:
        """Full pipeline: POST file to PC2 → get chunks+embeddings → index on PC3."""
        db = await get_db(self.settings)

        try:
            # Compute file hash for dedup
            with open(file_path, "rb") as f:
                file_hash = hashlib.sha256(f.read()).hexdigest()

            cursor = await db.execute(
                "SELECT id FROM documents WHERE id = ? AND status = ?",
                (file_hash, "indexed")
            )
            if await cursor.fetchone():
                return {"doc_id": file_hash, "status": "already_indexed"}

            # Step 1: POST file to PC2 for parse + chunk + embed
            with open(file_path, "rb") as f:
                files = {"file": (file_path.name, f)}
                res = await self.client.post(f"{self.pc2_url}/ingest/file", files=files)
                res.raise_for_status()
                data = res.json()
                chunks_with_embeddings = data.get("chunks", [])

            if not chunks_with_embeddings:
                return {"doc_id": file_hash, "status": "no_chunks"}

            # Step 2: Create document record
            await db.execute(
                "INSERT OR REPLACE INTO documents (id, filename, status, chunk_count) VALUES (?, ?, ?, ?)",
                (file_hash, file_path.name, "ingesting", len(chunks_with_embeddings))
            )
            await db.commit()

            # Step 3: Save chunks to local SQLite + collect embeddings
            embeddings = []
            chunks = []
            for chunk in chunks_with_embeddings:
                chunk_text = chunk.get("text", "")
                embedding = chunk.get("embedding", [])
                page_num = chunk.get("page_num")
                source_url = chunk.get("source_url", file_path.name)
                chunk_index = chunk.get("chunk_index", 0)

                cursor = await db.execute(
                    "INSERT INTO chunks (doc_id, chunk_index, text, page_num, source_url, token_count) VALUES (?, ?, ?, ?, ?, ?)",
                    (file_hash, chunk_index, chunk_text, page_num, source_url, len(chunk_text.split()))
                )
                await db.commit()

                embeddings.append(embedding)
                chunks.append({
                    "text": chunk_text,
                    "doc_id": file_hash,
                    "page_num": page_num,
                    "source_url": source_url,
                    "chunk_index": chunk_index
                })

            # Step 4: POST chunks + embeddings to PC3 for indexing
            await self.vector_store.add_vectors(embeddings, list(range(len(embeddings))), db, chunks)

            # Step 5: Mark complete
            await db.execute(
                "UPDATE documents SET status = ? WHERE id = ?",
                ("indexed", file_hash)
            )
            await db.commit()

            return {
                "doc_id": file_hash,
                "status": "indexed",
                "chunks": len(chunks_with_embeddings)
            }

        except Exception as e:
            await db.execute(
                "UPDATE documents SET status = ? WHERE id = ?",
                ("failed", hashlib.sha256(open(file_path, "rb").read()).hexdigest())
            )
            await db.commit()
            raise

        finally:
            await db.close()
            await self.client.aclose()
