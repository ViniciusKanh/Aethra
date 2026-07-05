from fastapi import APIRouter, Depends, Request

from ..models import DwQueryResponse, DwQuestionRequest
from ..security import require_admin_key

router = APIRouter(prefix="/dw", dependencies=[Depends(require_admin_key)])


@router.post("/ask", response_model=DwQueryResponse, tags=["Data Warehouse"])
def ask_warehouse(payload: DwQuestionRequest, request: Request) -> DwQueryResponse:
    return request.app.state.warehouse_service.ask(
        question=payload.pergunta,
        model=payload.model,
        max_rows=payload.max_rows,
    )
