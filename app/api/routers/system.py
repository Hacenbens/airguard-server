from fastapi import APIRouter, Request

router = APIRouter(tags=["system"])


@router.get("/health")
async def health(request: Request):
    return {"status": "ok", "model": request.app.state.container.settings.model_path.name}
