from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn
from pathlib import Path
from core.config import get_settings
from core.database import init_db, get_db
from core.auth import hash_password
from api.routes import health, ingest, query, auth, admin, chat, search

app = FastAPI(title="SRET-RAG SERVER", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

app.include_router(health.router)
app.include_router(ingest.router)
app.include_router(query.router)
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(chat.router)
app.include_router(search.router)

static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")


@app.on_event("startup")
async def startup():
    settings = get_settings()
    await init_db(settings)

    db = await get_db(settings)
    try:
        cursor = await db.execute("SELECT id FROM users WHERE role = 'admin'")
        admin_exists = await cursor.fetchone()

        if not admin_exists:
            pwd_hash = await hash_password(settings.admin_password)
            await db.execute(
                "INSERT INTO users (username, password_hash, role, is_active) VALUES (?, ?, ?, 1)",
                (settings.admin_username, pwd_hash, "admin")
            )
            await db.commit()
    finally:
        await db.close()


@app.get("/")
async def root():
    return {"message": "SRET-RAG SERVER running"}


if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        workers=1,
        reload=False
    )
