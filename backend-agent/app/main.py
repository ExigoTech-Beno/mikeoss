from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routes import chat, documents, projects, tabular, workflows, user, downloads

app = FastAPI(title="Mike Legal AI — Foundry Hosted Agent", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Foundry Responses protocol — conversational chat (OpenAI-compatible streaming)
app.include_router(chat.router, prefix="/chat")

# Foundry Invocations protocol — batch/non-conversational (tabular review, extractions)
app.include_router(tabular.router, prefix="/tabular")

# Standard REST routes
app.include_router(documents.router, prefix="/documents")
app.include_router(projects.router, prefix="/projects")
app.include_router(workflows.router, prefix="/workflows")
app.include_router(user.router, prefix="/user")
app.include_router(downloads.router, prefix="/downloads")


@app.get("/health")
async def health():
    return {"status": "ok"}
