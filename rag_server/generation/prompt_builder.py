class PromptBuilder:
    @staticmethod
    def build_rag_prompt(
        query: str,
        retrieved_chunks: list[dict],
        system_message: str = None
    ) -> str:
        """Build RAG prompt with numbered citations [1][2] etc."""
        if not system_message:
            system_message = "You are a helpful assistant. Use only the provided context to answer."

        context_text = ""
        sources = []

        for idx, chunk in enumerate(retrieved_chunks, 1):
            source = chunk.get("source_url", "Unknown")
            page = chunk.get("page_num")
            if page is not None:
                source += f" (page {page})"

            context_text += f"[{idx}] {chunk['text']}\n\n"
            sources.append({
                "number": idx,
                "url": chunk.get("source_url", ""),
                "page": page
            })

        prompt = f"""{system_message}

Context:
{context_text}

Question: {query}

Answer:"""

        return prompt, sources

    @staticmethod
    def build_chat_messages(
        query: str,
        retrieved_chunks: list[dict],
        system_message: str = None
    ) -> list[dict]:
        """Build OpenAI-compat messages for chat endpoint."""
        prompt, _ = PromptBuilder.build_rag_prompt(query, retrieved_chunks, system_message)

        return [
            {"role": "system", "content": system_message or "You are helpful."},
            {"role": "user", "content": prompt}
        ]
