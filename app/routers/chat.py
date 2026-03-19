from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.core.deps import get_current_user
from app.models.chat_schemas import ChatRequest
from app.models.user import User
from app.services.chat_service import chat_service

router = APIRouter()


@router.post("/chat")
async def chat(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Streaming chat endpoint for plant diagnosis Q&A.

    Accepts the full analysis context + conversation history.
    Returns a Server-Sent Events stream of tokens.

    Each SSE frame:
        data: <token text>\\n\\n

    Terminal frames:
        data: [DONE]\\n\\n        — stream complete
        data: [ERROR] {...}\\n\\n  — error occurred
    """
    return StreamingResponse(
        chat_service.stream_response(
            analysis=request.analysis_context,
            messages=request.messages,
            language=request.language,
        ),
        media_type="text/event-stream",
        headers={
            # Prevent any proxy/nginx from buffering the stream
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )