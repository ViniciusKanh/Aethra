from fastapi import APIRouter, Depends, Request

from ..models import ChatRequest, EnterpriseChatRequest, EnterpriseChatResponse, TextTaskResponse
from ..models import UserResponse
from ..security import require_authenticated_user, require_user_or_api_key

router = APIRouter()


@router.post(
    "/chat",
    response_model=TextTaskResponse,
    tags=["Chat"],
    dependencies=[Depends(require_user_or_api_key)],
)
def chat(payload: ChatRequest, request: Request) -> TextTaskResponse:
    return request.app.state.chat_service.executar(payload)


@router.post(
    "/assistant/chat",
    response_model=EnterpriseChatResponse,
    tags=["Chat"],
)
def enterprise_chat(
    payload: EnterpriseChatRequest,
    request: Request,
    user: UserResponse = Depends(require_authenticated_user),
) -> EnterpriseChatResponse:
    return request.app.state.assistant_service.execute(payload, user)
