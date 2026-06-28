from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from core.auth import get_current_user
from core.config import get_settings
from core.database import get_db

router = APIRouter()


class ChatCreateRequest(BaseModel):
    title: str = "New Chat"
    model: str = "Qwen2.5 7B Q4_K_M"


class ChatUpdateRequest(BaseModel):
    title: str = None
    model: str = None


@router.get("/api/v1/chats")
async def list_chats(request: Request):
    settings = get_settings()
    db = await get_db(settings)

    try:
        user = await get_current_user(request, db)

        cursor = await db.execute(
            "SELECT id, title, model, created_at FROM chats WHERE user_id = ? ORDER BY created_at DESC",
            (user["id"],)
        )
        chats = await cursor.fetchall()
        return [
            {"id": c[0], "title": c[1], "model": c[2], "created_at": c[3]}
            for c in chats
        ]
    finally:
        await db.close()


@router.post("/api/v1/chats")
async def create_chat(req: ChatCreateRequest, request: Request):
    settings = get_settings()
    db = await get_db(settings)

    try:
        user = await get_current_user(request, db)

        await db.execute(
            "INSERT INTO chats (user_id, title, model) VALUES (?, ?, ?)",
            (user["id"], req.title, req.model)
        )
        await db.commit()

        cursor = await db.execute(
            "SELECT last_insert_rowid()"
        )
        chat_id = (await cursor.fetchone())[0]
        return {"id": chat_id, "title": req.title, "model": req.model}
    finally:
        await db.close()


@router.get("/api/v1/chats/{chat_id}/messages")
async def get_messages(chat_id: int, request: Request):
    settings = get_settings()
    db = await get_db(settings)

    try:
        user = await get_current_user(request, db)

        cursor = await db.execute(
            "SELECT c.user_id FROM chats c WHERE c.id = ?",
            (chat_id,)
        )
        chat = await cursor.fetchone()
        if not chat or chat[0] != user["id"]:
            raise HTTPException(status_code=403, detail="Not authorized")

        cursor = await db.execute(
            "SELECT id, role, content, sources, created_at FROM messages WHERE chat_id = ? ORDER BY created_at ASC",
            (chat_id,)
        )
        messages = await cursor.fetchall()
        return [
            {
                "id": m[0],
                "role": m[1],
                "content": m[2],
                "sources": m[3],
                "created_at": m[4]
            }
            for m in messages
        ]
    finally:
        await db.close()


@router.patch("/api/v1/chats/{chat_id}")
async def update_chat(chat_id: int, req: ChatUpdateRequest, request: Request):
    settings = get_settings()
    db = await get_db(settings)

    try:
        user = await get_current_user(request, db)

        cursor = await db.execute(
            "SELECT user_id FROM chats WHERE id = ?",
            (chat_id,)
        )
        chat = await cursor.fetchone()
        if not chat or chat[0] != user["id"]:
            raise HTTPException(status_code=403, detail="Not authorized")

        updates = []
        params = []
        if req.title:
            updates.append("title = ?")
            params.append(req.title)
        if req.model:
            updates.append("model = ?")
            params.append(req.model)

        if updates:
            params.append(chat_id)
            query = f"UPDATE chats SET {', '.join(updates)} WHERE id = ?"
            await db.execute(query, params)
            await db.commit()

        return {"id": chat_id, "message": "Updated"}
    finally:
        await db.close()


@router.delete("/api/v1/chats/{chat_id}")
async def delete_chat(chat_id: int, request: Request):
    settings = get_settings()
    db = await get_db(settings)

    try:
        user = await get_current_user(request, db)

        cursor = await db.execute(
            "SELECT user_id FROM chats WHERE id = ?",
            (chat_id,)
        )
        chat = await cursor.fetchone()
        if not chat or chat[0] != user["id"]:
            raise HTTPException(status_code=403, detail="Not authorized")

        await db.execute("DELETE FROM messages WHERE chat_id = ?", (chat_id,))
        await db.execute("DELETE FROM chats WHERE id = ?", (chat_id,))
        await db.commit()

        return {"id": chat_id, "message": "Deleted"}
    finally:
        await db.close()
