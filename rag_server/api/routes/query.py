from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
import time
import json
from core.config import get_settings
from core.database import get_db
from core.auth import get_current_user
from retrieval.embedder import Embedder
from retrieval.vector_store import VectorStore
from generation.llm_client import LLMClient
from generation.prompt_builder import PromptBuilder

router = APIRouter()


class QueryRequest(BaseModel):
    query: str
    chat_id: Optional[int] = None
    top_k: int = 5
    stream: bool = False


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    messages: list[ChatMessage]
    max_tokens: int = 2048
    temperature: float = 0.7
    stream: bool = False


@router.post("/api/v1/query")
async def query(
    req: QueryRequest,
    request: Request
):
    settings = get_settings()
    db = await get_db(settings)
    embedder = Embedder(settings)
    vector_store = VectorStore(settings)
    await vector_store.init()
    llm_client = LLMClient(settings)

    try:
        user = await get_current_user(request, db)
        start_time = time.time()

        chat_id = req.chat_id
        if not chat_id:
            await db.execute(
                "INSERT INTO chats (user_id, title, model) VALUES (?, ?, ?)",
                (user["id"], req.query[:40], "Qwen2.5 7B Q4_K_M")
            )
            await db.commit()
            cursor = await db.execute("SELECT last_insert_rowid()")
            chat_id = (await cursor.fetchone())[0]

        query_embedding = await embedder.embed_text(req.query, db)
        results = await vector_store.search(query_embedding, req.top_k, db)

        if not results:
            await db.execute(
                "INSERT INTO messages (chat_id, role, content, sources) VALUES (?, ?, ?, ?)",
                (chat_id, "user", req.query, "[]")
            )
            await db.execute(
                "INSERT INTO messages (chat_id, role, content, sources) VALUES (?, ?, ?, ?)",
                (chat_id, "assistant", "No relevant documents found.", "[]")
            )
            await db.commit()

            return {
                "query": req.query,
                "answer": "No relevant documents found.",
                "sources": [],
                "chat_id": chat_id,
                "latency_ms": int((time.time() - start_time) * 1000)
            }

        prompt, sources = PromptBuilder.build_rag_prompt(req.query, results)
        try:
            answer = await llm_client.complete(prompt, settings.llm_max_tokens)
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"LLM error (PC4 at {settings.pc4_url}): {e}")

        sources_json = json.dumps([{"number": s["number"], "url": s.get("url", ""), "page": s.get("page", "")} for s in sources])

        await db.execute(
            "INSERT INTO messages (chat_id, role, content, sources) VALUES (?, ?, ?, ?)",
            (chat_id, "user", req.query, "[]")
        )
        await db.execute(
            "INSERT INTO messages (chat_id, role, content, sources) VALUES (?, ?, ?, ?)",
            (chat_id, "assistant", answer, sources_json)
        )
        await db.commit()

        return {
            "query": req.query,
            "answer": answer,
            "sources": sources,
            "chat_id": chat_id,
            "latency_ms": int((time.time() - start_time) * 1000)
        }

    finally:
        await db.close()
        await llm_client.close()


@router.post("/v1/chat/completions")
async def chat_completions(
    req: ChatCompletionRequest,
    request: Request
):
    settings = get_settings()
    db = await get_db(settings)
    embedder = Embedder(settings)
    vector_store = VectorStore(settings)
    await vector_store.init()
    llm_client = LLMClient(settings)

    try:
        user = await get_current_user(request, db)

        user_message = None
        for msg in req.messages:
            if msg.role == "user":
                user_message = msg.content
                break

        if not user_message:
            raise HTTPException(status_code=400, detail="No user message found")

        query_embedding = await embedder.embed_text(user_message, db)
        results = await vector_store.search(query_embedding, 5, db)

        messages = [
            {"role": "system", "content": "You are a helpful assistant. Use context to answer."}
        ]

        if results:
            context = "\n".join([f"[{i+1}] {r['text']}" for i, r in enumerate(results)])
            messages.append({
                "role": "system",
                "content": f"Context:\n{context}"
            })

        messages.append({
            "role": "user",
            "content": user_message
        })

        if req.stream:
            async def generate():
                async for chunk in llm_client.stream_complete(messages[-1]["content"]):
                    escaped_chunk = chunk.replace('"', '\\"').replace('\n', '\\n')
                    yield f'data: {{"choices": [{{"delta": {{"content": "{escaped_chunk}"}}}}]}}\n\n'

            return StreamingResponse(generate(), media_type="text/event-stream")

        else:
            answer = await llm_client.chat_completion(messages, req.max_tokens)
            return {
                "choices": [{
                    "message": {
                        "role": "assistant",
                        "content": answer
                    }
                }]
            }

    finally:
        await db.close()
        await llm_client.close()
