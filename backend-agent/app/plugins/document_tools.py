"""
Semantic Kernel plugins that mirror chatTools.ts LLM tool definitions.

Each @kernel_function becomes a tool the LLM can call during chat.
Wired up to the SK Kernel in app/routes/chat.py.
"""

from __future__ import annotations
import json
from typing import Annotated

from semantic_kernel.functions import kernel_function
import asyncpg

from app.db.models import get_document, list_documents
from app.storage.blob import download_file, get_signed_url, storage_key, pdf_storage_key


class DocumentPlugin:
    """Tools for reading and listing documents in a chat session."""

    def __init__(self, db: asyncpg.Pool, user_id: str):
        self._db = db
        self._user_id = user_id

    @kernel_function(
        name="list_documents",
        description="List all documents available in the current project or chat context.",
    )
    async def list_documents_tool(
        self,
        project_id: Annotated[str, "The project UUID to list documents for"],
    ) -> str:
        docs = await list_documents(self._db, project_id)
        result = [{"id": d["id"], "filename": d["filename"], "file_type": d["file_type"]} for d in docs]
        return json.dumps(result)

    @kernel_function(
        name="read_document",
        description="Read and return the text content of a specific document by its ID.",
    )
    async def read_document_tool(
        self,
        document_id: Annotated[str, "The UUID of the document to read"],
    ) -> str:
        doc = await get_document(self._db, document_id)
        if not doc:
            return json.dumps({"error": "Document not found"})

        key = storage_key(self._user_id, document_id, doc["filename"])
        content = await download_file(key)
        if not content:
            # Try PDF version
            from pathlib import Path
            stem = Path(doc["filename"]).stem
            pdf_key = pdf_storage_key(self._user_id, document_id, stem)
            content = await download_file(pdf_key)

        if not content:
            return json.dumps({"error": "Document content not available"})

        # Extract text based on file type
        text = _extract_text(content, doc["file_type"], doc["filename"])
        return json.dumps({"document_id": document_id, "filename": doc["filename"], "text": text})

    @kernel_function(
        name="get_document_download_url",
        description="Get a signed download URL for a document so the user can download it.",
    )
    async def get_download_url_tool(
        self,
        document_id: Annotated[str, "The UUID of the document"],
        filename: Annotated[str, "The display filename for the download"],
    ) -> str:
        doc = await get_document(self._db, document_id)
        if not doc:
            return json.dumps({"error": "Document not found"})
        key = storage_key(self._user_id, document_id, doc["filename"])
        url = await get_signed_url(key, expires_in=3600, download_filename=filename)
        if not url:
            return json.dumps({"error": "Could not generate download URL"})
        return json.dumps({"url": url, "filename": filename})


def _extract_text(content: bytes, file_type: str, filename: str) -> str:
    """Best-effort text extraction from document bytes."""
    ft = file_type.lower()
    name = filename.lower()

    if ft == "application/pdf" or name.endswith(".pdf"):
        try:
            import io
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(content))
            return "\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception as e:
            return f"[PDF extraction error: {e}]"

    if ft in ("application/vnd.openxmlformats-officedocument.wordprocessingml.document",) or name.endswith(".docx"):
        try:
            import io
            from docx import Document
            doc = Document(io.BytesIO(content))
            return "\n".join(p.text for p in doc.paragraphs)
        except Exception as e:
            return f"[DOCX extraction error: {e}]"

    # Plain text fallback
    try:
        return content.decode("utf-8", errors="replace")
    except Exception:
        return "[Could not extract text]"
