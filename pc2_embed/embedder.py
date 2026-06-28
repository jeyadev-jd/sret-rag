import hashlib
import asyncio
import numpy as np
from sentence_transformers import SentenceTransformer
from concurrent.futures import ThreadPoolExecutor


class Embedder:
    def __init__(self, model_path: str = None, model_name: str = "all-MiniLM-L6-v2", normalize: bool = True):
        """
        model_path: path to local model dir (e.g. ../models/minilm). If set, use that instead of downloading.
        """
        if model_path:
            self.model = SentenceTransformer(model_path)
        else:
            self.model = SentenceTransformer(model_name)
        self.executor = ThreadPoolExecutor(max_workers=2)
        self.normalize = normalize

    async def embed_text(self, text: str) -> list:
        """Embed single text. Returns list of floats."""
        embedding = await self._encode(text)
        return embedding.tolist()

    async def embed_batch(self, texts: list[str]) -> list[list]:
        """Embed multiple texts. Returns list of embeddings."""
        embeddings = []
        for text in texts:
            emb = await self.embed_text(text)
            embeddings.append(emb)
        return embeddings

    async def _encode(self, text: str) -> np.ndarray:
        """Run SentenceTransformer in executor."""
        loop = asyncio.get_event_loop()
        embedding = await loop.run_in_executor(
            self.executor,
            self._encode_sync,
            text
        )
        return embedding

    def _encode_sync(self, text: str) -> np.ndarray:
        """Synchronous encoding."""
        embedding = self.model.encode(text, normalize_embeddings=self.normalize)
        return embedding
