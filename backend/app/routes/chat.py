from fastapi import APIRouter, Depends, Request

from ..models import ChatRequest, TextTaskResponse
from ..security import require_api_key

router = APIRouter()


@router.post(
    "/chat",
    response_model=TextTaskResponse,
    tags=["Chat"],
    dependencies=[Depends(require_api_key)],
)
def chat(payload: ChatRequest, request: Request) -> TextTaskResponse:
    return request.app.state.chat_service.executar(payload)
