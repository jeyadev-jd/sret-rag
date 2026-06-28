import aiosqlite
import sqlite3
from pathlib import Path
from .config import Settings


async def init_db(settings: Settings) -> None:
    await _create_tables(settings)


async def _create_tables(settings: Settings) -> None:
    settings.metadata_db_path.parent.mkdir(parents=True, exist_ok=True)

    async with aiosqlite.connect(str(settings.metadata_db_path)) as db:
        await db.execute("PRAGMA journal_mode=WAL")
        await db.execute("PRAGMA synchronous=NORMAL")

        await db.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                source_url TEXT,
                status TEXT NOT NULL DEFAULT 'pending',
                chunk_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS chunks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                doc_id TEXT NOT NULL,
                faiss_id INTEGER,
                chunk_index INTEGER NOT NULL,
                text TEXT NOT NULL,
                source_url TEXT,
                page_num INTEGER,
                token_count INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (doc_id) REFERENCES documents(id)
            )
        """)

        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_chunks_doc_id ON chunks(doc_id)
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS embed_cache (
                text_hash TEXT PRIMARY KEY,
                embedding BLOB NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT DEFAULT 'user',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active INTEGER DEFAULT 1
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS chats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT DEFAULT 'New Chat',
                model TEXT DEFAULT 'Qwen2.5 7B Q4_K_M',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                sources TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (chat_id) REFERENCES chats(id)
            )
        """)

        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_chat ON messages(chat_id)
        """)

        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id)
        """)

        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_chats_user ON chats(user_id)
        """)

        await db.commit()


async def get_db(settings: Settings) -> aiosqlite.Connection:
    return await aiosqlite.connect(
        str(settings.metadata_db_path),
        timeout=settings.db_timeout,
        check_same_thread=False
    )
