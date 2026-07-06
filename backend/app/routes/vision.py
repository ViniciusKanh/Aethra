from fastapi import APIRouter, Depends, HTTPException, Request

from ..models import TextTaskResponse, VisionRequest
from ..security import require_user_or_api_key

router = APIRouter()


@router.post(
    "/vision",
    response_model=TextTaskResponse,
    tags=["Visao"],
    dependencies=[Depends(require_user_or_api_key)],
)
def vision(payload: VisionRequest, request: Request) -> TextTaskResponse:
    try:
        return request.app.state.vision_service.executar(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
