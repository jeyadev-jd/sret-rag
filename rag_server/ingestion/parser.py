import fitz
import html2text
from pathlib import Path
from typing import Tuple


async def parse_pdf(file_path: Path) -> Tuple[str, list[dict]]:
    """Parse PDF → text + {page_num, text}."""
    doc = fitz.open(file_path)
    full_text = ""
    pages = []

    for page_num, page in enumerate(doc):
        text = page.get_text()
        full_text += text + "\n"
        pages.append({
            "page_num": page_num,
            "text": text
        })

    doc.close()
    return full_text, pages


async def parse_html(file_path: Path) -> str:
    """HTML → Markdown → plain text."""
    with open(file_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    h = html2text.HTML2Text()
    h.ignore_links = False
    h.body_width = 0
    markdown = h.handle(html_content)
    return markdown


async def parse_text(file_path: Path) -> str:
    """Plain text → as-is."""
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


async def parse_document(file_path: Path) -> Tuple[str, list[dict] | None]:
    """Auto-detect file type and parse."""
    suffix = file_path.suffix.lower()

    if suffix == ".pdf":
        return await parse_pdf(file_path)
    elif suffix in (".html", ".htm"):
        text = await parse_html(file_path)
        return text, None
    elif suffix in (".txt", ".md"):
        text = await parse_text(file_path)
        return text, None
    else:
        raise ValueError(f"Unsupported file type: {suffix}")
