from pydantic_settings import BaseSettings
from functools import lru_cache
from pathlib import Path


class Settings(BaseSettings):
    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_workers: int = 4

    # PC Node config
    pc_number: int = 1  # 1=gateway, 2=embedder, 3=index, 4=llm
    pc_ip: str = "192.168.1.10"

    # Peer services
    pc2_url: str = "http://192.168.1.11:8001"
    pc3_url: str = "http://192.168.1.12:8002"
    pc4_url: str = "http://192.168.1.13:8003"

    # Storage paths
    storage_dir: Path = Path(__file__).parent.parent / "storage"
    faiss_index_path: Path = Path(__file__).parent.parent / "storage" / "faiss.index"
    metadata_db_path: Path = Path(__file__).parent.parent / "storage" / "metadata.db"
    uploads_dir: Path = Path(__file__).parent.parent / "storage" / "uploads"

    # Embedding config
    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_dim: int = 384
    embedding_normalize: bool = True
    embedding_batch_size: int = 32

    # FAISS config
    faiss_nlist: int = 50
    faiss_m: int = 8
    faiss_nprobe: int = 5

    # Chunking config
    chunk_size: int = 512
    chunk_overlap: int = 64

    # LLM config
    llm_model: str = "phi-2"
    llm_max_tokens: int = 256
    llm_temperature: float = 0.7
    llm_timeout: int = 300

    # Database
    db_connection_pool_size: int = 10
    db_timeout: float = 30.0

    # RAG
    rag_top_k: int = 5
    rag_relevance_threshold: float = 0.5

    # Async
    max_concurrent_embeds: int = 4

    # Auth
    secret_key: str = "change-me-in-env"
    admin_username: str = "admin"
    admin_password: str = "admin123"
    session_ttl_days: int = 7
    cloudflare_tunnel_token: str = ""
    allowed_models: list = [
        "phi-2",
        "qwen2.5-1.5b",
        "tinyllama-1.1b"
    ]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
