from fastapi import APIRouter, Depends, Request, status

from ..models import ConversationDetail, ConversationSummary, UserResponse
from ..security import require_authenticated_user

router = APIRouter(prefix="/conversations", tags=["Conversas"])


@router.get("", response_model=list[ConversationSummary])
def list_conversations(
    request: Request,
    user: UserResponse = Depends(require_authenticated_user),
) -> list[ConversationSummary]:
    return request.app.state.conversation_service.list_conversations(user.id)


@router.get("/{conversation_id}", response_model=ConversationDetail)
def get_conversation(
    conversation_id: str,
    request: Request,
    user: UserResponse = Depends(require_authenticated_user),
) -> ConversationDetail:
    return request.app.state.conversation_service.get(user.id, conversation_id)


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conversation(
    conversation_id: str,
    request: Request,
    user: UserResponse = Depends(require_authenticated_user),
) -> None:
    request.app.state.conversation_service.delete(user.id, conversation_id)
