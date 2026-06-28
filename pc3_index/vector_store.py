import faiss
import numpy as np
import aiosqlite
from pathlib import Path


class VectorStore:
    def __init__(self, index_path: Path, embedding_dim: int = 384, nlist: int = 50, m: int = 8):
        self.index = None
        self.index_path = Path(index_path)
        self.embedding_dim = embedding_dim
        self.nlist = nlist
        self.m = m

    async def init(self, db: aiosqlite.Connection = None) -> None:
        """Initialize or load FAISS index."""
        if self.index_path.exists():
            self.index = faiss.read_index(str(self.index_path))
        else:
            self.index_path.parent.mkdir(parents=True, exist_ok=True)
            quantizer = faiss.IndexFlatL2(self.embedding_dim)
            self.index = faiss.IndexIVFPQ(quantizer, self.embedding_dim, self.nlist, self.m, 8)
            self.index.train(
                np.random.rand(self.nlist * 100, self.embedding_dim).astype(np.float32)
            )

    async def add_vectors(self, embeddings: list[list], chunk_ids: list[int], db: aiosqlite.Connection) -> None:
        """Add embeddings to FAISS, store faiss_id in SQLite."""
        if not embeddings or not self.index:
            return

        vectors = np.array(embeddings, dtype=np.float32)
        start_id = self.index.ntotal
        self.index.add(vectors)

        for i, chunk_id in enumerate(chunk_ids):
            faiss_id = start_id + i
            await db.execute(
                "UPDATE chunks SET faiss_id = ? WHERE id = ?",
                (faiss_id, chunk_id)
            )

        await db.commit()
        self.save()

    async def search(self, query_embedding: list, k: int = 5, db: aiosqlite.Connection = None) -> list[dict]:
        """Search FAISS, retrieve metadata from SQLite."""
        if not self.index:
            return []

        query = np.array(query_embedding, dtype=np.float32).reshape(1, -1)
        distances, faiss_ids = self.index.search(query, k)

        results = []
        for idx, faiss_id in enumerate(faiss_ids[0]):
            if faiss_id == -1:
                continue

            if db:
                cursor = await db.execute(
                    "SELECT id, text, source_url, page_num FROM chunks WHERE faiss_id = ?",
                    (int(faiss_id),)
                )
                row = await cursor.fetchone()
                if row:
                    results.append({
                        "faiss_id": int(faiss_id),
                        "chunk_id": row[0],
                        "text": row[1],
                        "source_url": row[2],
                        "page_num": row[3],
                        "distance": float(distances[0][idx]),
                        "number": len(results) + 1
                    })

        return results

    def save(self) -> None:
        """Persist FAISS index to disk."""
        if self.index:
            faiss.write_index(self.index, str(self.index_path))
