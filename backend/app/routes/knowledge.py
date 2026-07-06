from fastapi import APIRouter, Depends, Request

from ..models import KnowledgeStatusResponse
from ..security import require_authenticated_user

router = APIRouter(prefix="/knowledge", dependencies=[Depends(require_authenticated_user)])


@router.get("/status", response_model=KnowledgeStatusResponse, tags=["Documentos"])
def knowledge_status(request: Request) -> KnowledgeStatusResponse:
    return request.app.state.knowledge_service.status()
