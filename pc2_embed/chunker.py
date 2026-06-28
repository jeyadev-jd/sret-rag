from semantic_text_splitter import TextSplitter
from transformers import AutoTokenizer


async def get_text_splitter(model_name: str = "all-MiniLM-L6-v2", chunk_size: int = 512) -> TextSplitter:
    """Initialize semantic text splitter with BERT tokenizer."""
    tokenizer = AutoTokenizer.from_pretrained(model_name)

    def count_tokens(text: str) -> int:
        return len(tokenizer.encode(text))

    splitter = TextSplitter.from_token_count(
        token_count_func=count_tokens,
        max_tokens=chunk_size,
        trim_chunks=True
    )
    return splitter


async def chunk_text(text: str, chunk_size: int = 512, overlap: int = 64) -> list[str]:
    """Split text into semantic chunks."""
    splitter = await get_text_splitter(chunk_size=chunk_size)
    chunks = splitter.chunks(text, chunk_size=chunk_size, overlap=overlap)
    return chunks


async def chunk_pages(pages: list[dict], chunk_size: int = 512, overlap: int = 64) -> list[dict]:
    """Chunk per-page texts, preserve page numbers."""
    chunked = []
    chunk_index = 0

    for page in pages:
        chunks = await chunk_text(page["text"], chunk_size, overlap)
        for chunk_text_str in chunks:
            chunked.append({
                "chunk_index": chunk_index,
                "text": chunk_text_str,
                "page_num": page["page_num"],
                "token_count": len(chunk_text_str.split())  # rough estimate
            })
            chunk_index += 1

    return chunked
