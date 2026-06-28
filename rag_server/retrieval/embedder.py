import hashlib
import asyncio
import aiosqlite
import httpx
import numpy as np
from core.config import Settings


class Embedder:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = httpx.AsyncClient(timeout=60)
        self.pc2_url = settings.pc2_url

    async def embed_text(self, text: str, db: aiosqlite.Connection) -> np.ndarray:
        """Embed single text, check cache first. On miss, call PC2."""
        text_hash = hashlib.sha256(text.encode()).hexdigest()

        cursor = await db.execute(
            "SELECT embedding FROM embed_cache WHERE text_hash = ?",
            (text_hash,)
        )
        row = await cursor.fetchone()

        if row:
            embedding_bytes = row[0]
            return np.frombuffer(embedding_bytes, dtype=np.float32)

        try:
            res = await self.client.post(f"{self.pc2_url}/embed", json={"text": text})
            res.raise_for_status()
            data = res.json()
            embedding = np.array(data["vector"], dtype=np.float32)
        except Exception as e:
            raise RuntimeError(f"PC2 embed failed: {e}")

        embedding_bytes = embedding.astype(np.float32).tobytes()
        await db.execute(
            "INSERT OR IGNORE INTO embed_cache (text_hash, embedding) VALUES (?, ?)",
            (text_hash, embedding_bytes)
        )
        await db.commit()

        return embedding

    async def embed_batch(self, texts: list[str], db: aiosqlite.Connection) -> list[np.ndarray]:
        """Embed multiple texts with cache lookups."""
        embeddings = []
        for text in texts:
            emb = await self.embed_text(text, db)
            embeddings.append(emb)
        return embeddings

    async def close(self):
        await self.client.aclose()
