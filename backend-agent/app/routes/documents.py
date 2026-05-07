"""
Document upload and management routes.
Replaces backend/src/routes/documents.ts.
"""

from fastapi import APIRouter, Depends, Request, UploadFile, File, HTTPException
from app.auth.middleware import require_auth
from app.db.connection import get_pool
from app.db.models import create_document, list_documents, get_document
from app.storage.blob import upload_file, delete_file, storage_key, get_signed_url

router = APIRouter()


@router.get("/{project_id}")
async def list_project_documents(project_id: str, request: Request, _=Depends(require_auth)):
    db = await get_pool()
    docs = await list_documents(db, project_id)
    return docs


@router.post("/upload")
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    _=Depends(require_auth),
):
    db = await get_pool()
    user_id = request.state.user_id
    form = await request.form()
    project_id = form.get("project_id") or None

    content = await file.read()
    content_type = file.content_type or "application/octet-stream"

    doc = await create_document(db, user_id, project_id, file.filename, content_type, "")
    key = storage_key(user_id, doc["id"], file.filename)

    await upload_file(key, content, content_type)

    # Update storage_path now we have the doc id
    pool = await get_pool()
    await pool.execute(
        "UPDATE documents SET storage_path = $1 WHERE id = $2", key, doc["id"]
    )
    doc["storage_path"] = key
    return doc


@router.get("/{doc_id}/download-url")
async def get_document_url(doc_id: str, request: Request, _=Depends(require_auth)):
    db = await get_pool()
    doc = await get_document(db, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    url = await get_signed_url(doc["storage_path"], download_filename=doc["filename"])
    return {"url": url}
