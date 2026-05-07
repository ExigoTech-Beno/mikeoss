"""
Azure Blob Storage layer.
Replaces backend/src/lib/storage.ts (Cloudflare R2 via AWS S3 SDK).

Uses the azure-storage-blob SDK with a connection string.
All key-naming conventions are preserved from the original TypeScript.
"""

import os
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

from azure.storage.blob import (
    BlobServiceClient,
    BlobSasPermissions,
    generate_blob_sas,
)
from app.config import settings


def _client() -> BlobServiceClient:
    return BlobServiceClient.from_connection_string(settings.blob_connection_string)


CONTAINER = settings.blob_container

storage_enabled = bool(settings.blob_connection_string)


# ---------------------------------------------------------------------------
# Upload / Download / Delete
# ---------------------------------------------------------------------------

async def upload_file(key: str, content: bytes, content_type: str) -> None:
    client = _client()
    blob = client.get_blob_client(container=CONTAINER, blob=key)
    blob.upload_blob(content, overwrite=True, content_settings={"content_type": content_type})


async def download_file(key: str) -> bytes | None:
    if not storage_enabled:
        return None
    try:
        client = _client()
        blob = client.get_blob_client(container=CONTAINER, blob=key)
        stream = blob.download_blob()
        return stream.readall()
    except Exception:
        return None


async def delete_file(key: str) -> None:
    if not storage_enabled:
        return
    client = _client()
    blob = client.get_blob_client(container=CONTAINER, blob=key)
    blob.delete_blob(delete_snapshots="include")


async def get_signed_url(key: str, expires_in: int = 3600,
                         download_filename: str | None = None) -> str | None:
    if not storage_enabled:
        return None
    try:
        client = _client()
        account_name = client.account_name
        account_key = client.credential.account_key

        content_disposition = None
        if download_filename:
            safe = download_filename.replace('"', "_").replace("\\", "_")
            content_disposition = f'attachment; filename="{safe}"'

        sas_token = generate_blob_sas(
            account_name=account_name,
            container_name=CONTAINER,
            blob_name=key,
            account_key=account_key,
            permission=BlobSasPermissions(read=True),
            expiry=datetime.now(timezone.utc) + timedelta(seconds=expires_in),
            content_disposition=content_disposition,
        )
        return f"https://{account_name}.blob.core.windows.net/{CONTAINER}/{quote(key)}?{sas_token}"
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Storage key helpers (mirrors storage.ts conventions)
# ---------------------------------------------------------------------------

def _ext(filename: str, fallback: str) -> str:
    idx = filename.rfind(".")
    if idx < 0:
        return fallback
    ext = filename[idx:].lower()
    import re
    return ext if re.match(r"^\.[a-z0-9]{1,16}$", ext) else fallback


def storage_key(user_id: str, doc_id: str, filename: str) -> str:
    return f"documents/{user_id}/{doc_id}/source{_ext(filename, '.bin')}"


def pdf_storage_key(user_id: str, doc_id: str, stem: str) -> str:
    return f"documents/{user_id}/{doc_id}/{stem}.pdf"


def generated_doc_key(user_id: str, doc_id: str, filename: str) -> str:
    return f"generated/{user_id}/{doc_id}/generated{_ext(filename, '.docx')}"


def version_storage_key(user_id: str, doc_id: str, version_slug: str, filename: str) -> str:
    return f"documents/{user_id}/{doc_id}/versions/{version_slug}{_ext(filename, '.bin')}"
