from fastapi import APIRouter, Depends, Request

from ..models import EmailSummarizeRequest, SummarizeRequest, TextTaskResponse
from ..security import require_user_or_api_key

router = APIRouter()


@router.post(
    "/summarize",
    response_model=TextTaskResponse,
    tags=["Resumo"],
    dependencies=[Depends(require_user_or_api_key)],
)
def summarize(payload: SummarizeRequest, request: Request) -> TextTaskResponse:
    return request.app.state.summarize_service.executar(payload)


@router.post(
    "/summarize/email",
    response_model=TextTaskResponse,
    tags=["Resumo"],
    dependencies=[Depends(require_user_or_api_key)],
)
def summarize_email(payload: EmailSummarizeRequest, request: Request) -> TextTaskResponse:
    return request.app.state.summarize_service.executar_email(payload)
