import httpx
import numpy as np
import aiosqlite
from core.config import Settings


class VectorStore:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = httpx.AsyncClient(timeout=60)
        self.pc3_url = settings.pc3_url

    async def init(self) -> None:
        """Initialize connection to PC3 index."""
        try:
            res = await self.client.get(f"{self.pc3_url}/health")
            res.raise_for_status()
            print(f"✓ Connected to PC3 at {self.pc3_url}")
        except Exception as e:
            print(f"✗ Failed to connect to PC3: {e}")
            raise

    async def add_vectors(
        self,
        embeddings: list[np.ndarray],
        chunk_ids: list[int],
        db: aiosqlite.Connection,
        chunks: list[dict] = None
    ) -> None:
        """Send embeddings + chunks to PC3 for indexing."""
        if not embeddings or not chunks:
            return

        try:
            payload = {
                "chunks": [
                    {
                        "text": chunk.get("text", ""),
                        "embedding": emb.tolist() if isinstance(emb, np.ndarray) else emb,
                        "doc_id": chunk.get("doc_id", "unknown"),
                        "page_num": chunk.get("page_num"),
                        "source_url": chunk.get("source_url", ""),
                        "chunk_index": chunk.get("chunk_index", i)
                    }
                    for i, (emb, chunk) in enumerate(zip(embeddings, chunks))
                ]
            }

            res = await self.client.post(f"{self.pc3_url}/add", json=payload)
            res.raise_for_status()
            data = res.json()
            print(f"✓ PC3 indexed {data['added']} chunks")
        except Exception as e:
            raise RuntimeError(f"PC3 add_vectors failed: {e}")

    async def search(
        self,
        query_embedding: np.ndarray,
        k: int = 5,
        db: aiosqlite.Connection = None
    ) -> list[dict]:
        """Search PC3 index."""
        try:
            vector = query_embedding.astype(np.float32).tolist() if isinstance(query_embedding, np.ndarray) else query_embedding
            res = await self.client.post(
                f"{self.pc3_url}/search",
                json={"vector": vector, "top_k": k}
            )
            res.raise_for_status()
            data = res.json()
            return data.get("chunks", [])
        except Exception as e:
            raise RuntimeError(f"PC3 search failed: {e}")

    async def close(self):
        await self.client.aclose()
