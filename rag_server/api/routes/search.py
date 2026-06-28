from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from typing import Optional
import time
import json
from core.auth import get_current_user
from core.config import get_settings
from core.database import get_db
from generation.llm_client import LLMClient
from retrieval.web_search import web_search

router = APIRouter()


class SearchRequest(BaseModel):
    query: str
    chat_id: Optional[int] = None
    search: bool = True
    docs: bool = True
    stream: bool = False


@router.post("/api/v1/search")
async def search_and_rag(req: SearchRequest, request: Request):
    """Web search + LLM summarize. Falls back to LLM knowledge if no results."""
    settings = get_settings()
    db = await get_db(settings)
    llm_client = LLMClient(settings)

    try:
        user = await get_current_user(request, db)
        start_time = time.time()

        web_results = []
        if req.search:
            try:
                web_results = await web_search(req.query, num_results=5)
            except Exception as e:
                print(f"Web search failed: {e}")
                web_results = []

        if web_results:
            context = "\n\n".join([
                f"[{i+1}] {r['title']}\n{r['snippet']}\nURL: {r['url']}"
                for i, r in enumerate(web_results)
            ])
            system_prompt = (
                "You are a helpful assistant. Use the provided web search results to answer "
                "the user's question. Cite sources as [1], [2], etc. If the results don't "
                "contain the answer, say so. Do not invent information."
            )
            user_prompt = f"Web search results:\n{context}\n\nQuestion: {req.query}"
        else:
            system_prompt = (
                "You are a helpful assistant. Answer the user's question concisely. "
                "If you don't know or your knowledge may be outdated, say so."
            )
            user_prompt = req.query

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        try:
            answer = await llm_client.chat_completion(messages, settings.llm_max_tokens)
        except Exception as e:
            answer = f"LLM error: {str(e)[:80]}"

        sources_list = [
            {"number": i+1, "title": r["title"], "url": r["url"], "snippet": r["snippet"]}
            for i, r in enumerate(web_results)
        ]
        sources_json = json.dumps(sources_list)

        chat_id = req.chat_id
        if not chat_id:
            await db.execute(
                "INSERT INTO chats (user_id, title, model) VALUES (?, ?, ?)",
                (user["id"], req.query[:40], settings.llm_model)
            )
            await db.commit()
            cursor = await db.execute("SELECT last_insert_rowid()")
            chat_id = (await cursor.fetchone())[0]

        try:
            await db.execute(
                "INSERT INTO messages (chat_id, role, content, sources) VALUES (?, ?, ?, ?)",
                (chat_id, "user", req.query, "[]")
            )
            await db.execute(
                "INSERT INTO messages (chat_id, role, content, sources) VALUES (?, ?, ?, ?)",
                (chat_id, "assistant", answer, sources_json)
            )
            await db.commit()
        except Exception as e:
            print(f"DB save failed: {e}")

        return {
            "query": req.query,
            "answer": answer,
            "sources": sources_list,
            "chat_id": chat_id,
            "latency_ms": int((time.time() - start_time) * 1000)
        }

    except HTTPException:
        raise
    except Exception as e:
        return {
            "query": req.query,
            "answer": f"Error: {str(e)[:120]}",
            "sources": [],
            "chat_id": req.chat_id
        }
    finally:
        try:
            await db.close()
        except Exception:
            pass
        try:
            await llm_client.close()
        except Exception:
            pass
