from fastapi import APIRouter, Depends, Request

from ..models import SummarizeRequest, TextTaskResponse
from ..security import require_api_key

router = APIRouter()


@router.post(
    "/summarize",
    response_model=TextTaskResponse,
    tags=["Resumo"],
    dependencies=[Depends(require_api_key)],
)
def summarize(payload: SummarizeRequest, request: Request) -> TextTaskResponse:
    return request.app.state.summarize_service.executar(payload)
