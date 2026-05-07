"""
Chat routes — Foundry Responses protocol (OpenAI-compatible streaming).
Replaces backend/src/routes/chat.ts.

The /chat/responses endpoint speaks the OpenAI /responses contract so that
any OpenAI-compatible client (including the Foundry playground and Teams) works
out of the box once the agent is deployed as a Foundry Hosted Agent.
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
import json

from app.auth.middleware import require_auth
from app.db.connection import get_pool
from app.db.models import (
    list_chats, create_chat, list_chat_messages, append_chat_message, get_project
)
from app.plugins.document_tools import DocumentPlugin

router = APIRouter()


@router.get("/")
async def get_chats(request: Request, _=Depends(require_auth)):
    db = await get_pool()
    chats = await list_chats(db, request.state.user_id)
    return chats


@router.post("/create")
async def create_chat_endpoint(request: Request, _=Depends(require_auth)):
    body = await request.json()
    db = await get_pool()
    chat = await create_chat(db, request.state.user_id, body.get("project_id"))
    return chat


@router.get("/{chat_id}/messages")
async def get_messages(chat_id: str, request: Request, _=Depends(require_auth)):
    db = await get_pool()
    messages = await list_chat_messages(db, chat_id)
    return messages


@router.post("/{chat_id}/responses")
async def chat_responses(chat_id: str, request: Request, _=Depends(require_auth)):
    """
    Foundry Responses protocol endpoint.
    Accepts OpenAI-compatible input, streams back SSE response events.
    """
    body = await request.json()
    db = await get_pool()
    user_id = request.state.user_id

    # Build SK kernel with all plugins
    from semantic_kernel import Kernel
    from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
    from app.config import settings
    from app.plugins.austlii import AustLIIPlugin
    from app.plugins.australian_legislation import AustralianLegislationPlugin

    kernel = Kernel()
    kernel.add_service(
        AzureChatCompletion(
            deployment_name=settings.foundry_model_deployment,
            endpoint=settings.foundry_project_endpoint,
            ad_token_provider=None,  # uses managed identity in Foundry
        )
    )
    kernel.add_plugin(DocumentPlugin(db, user_id), plugin_name="documents")
    kernel.add_plugin(AustLIIPlugin(), plugin_name="austlii")
    kernel.add_plugin(AustralianLegislationPlugin(), plugin_name="au_legislation")

    user_message = body.get("input", "")
    await append_chat_message(db, chat_id, "user", user_message)

    async def stream():
        from semantic_kernel.contents import ChatHistory
        history = ChatHistory()
        history.add_system_message(
            "You are Mike, an AI legal assistant specialising in Australian law. "
            "You have access to:\n"
            "- The user's uploaded documents (documents plugin)\n"
            "- AustLII: search Australian case law, legislation, and tribunal decisions (austlii plugin)\n"
            "- Australian legislation: Privacy Act APPs, Corporations Act, Fair Work Act, "
            "ACL and more (au_legislation plugin)\n\n"
            "Always cite your sources. For privacy matters always reference the relevant APP. "
            "For employment matters reference the Fair Work Act 2009. "
            "For contract disputes reference relevant case law from AustLII. "
            "Remind users this is not legal advice and to consult a qualified Australian solicitor."
        )
        for msg in await list_chat_messages(db, chat_id):
            if msg["role"] == "user":
                history.add_user_message(msg["content"])
            else:
                history.add_assistant_message(msg["content"])

        full_text = []
        chat_service = kernel.get_service(type=AzureChatCompletion)
        async for chunk in chat_service.get_streaming_chat_message_contents(history):
            if chunk and chunk[0].content:
                delta = chunk[0].content
                full_text.append(delta)
                event = json.dumps({"type": "content_block_delta", "delta": {"text": delta}})
                yield f"data: {event}\n\n"

        complete = "".join(full_text)
        await append_chat_message(db, chat_id, "assistant", complete,
                                   model=settings.foundry_model_deployment)
        yield "data: [DONE]\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream")
