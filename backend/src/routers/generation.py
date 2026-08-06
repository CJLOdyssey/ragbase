"""Generation API routes — SPEC §3.3 全部端点."""

from typing import Any

from auth import get_user_id
from core.error_codes import ErrorCode, error_response
from core.infra.logging_config import get_logger
from fastapi import APIRouter, Request
from pydantic import BaseModel, Field
from pydantic.alias_generators import to_camel
from services.generation_service import generation_service
from services.image_service import image_service

logger = get_logger(__name__)
router = APIRouter(tags=["generations"])

_MAX_TOPIC = 500
_MAX_EXTRA = 2000


class GenerationRequest(BaseModel):
    model_config = {"alias_generator": to_camel, "populate_by_name": True}
    content_type: str = "generic"
    generation_mode: str = "generate"
    topic: str = Field(..., max_length=_MAX_TOPIC)
    additional_requirements: str = Field(default="", max_length=_MAX_EXTRA)
    asset_ids: list[str] = Field(default_factory=list)
    key_id: str | None = None
    model: str | None = None
    template_id: str | None = None


class ContinueRequest(BaseModel):
    model_config = {"alias_generator": to_camel, "populate_by_name": True}
    content: str = Field(..., min_length=1)


class ImageRequest(BaseModel):
    model_config = {"alias_generator": to_camel, "populate_by_name": True}
    prompt: str = Field(..., min_length=1, max_length=1000)
    provider: str
    key_id: str | None = None


class ComposeRequest(BaseModel):
    model_config = {"alias_generator": to_camel, "populate_by_name": True}
    template_id: str
    title: str = ""
    summary: str = ""


class GenerationResponse(BaseModel):
    run_id: str
    session_id: str | None = None
    status: str


@router.post("/api/generations", response_model=GenerationResponse)
async def create_generation(req: GenerationRequest, request: Request) -> Any:
    user_id = get_user_id(request)
    try:
        result = await generation_service.create_generation(
            user_id=user_id,
            content_type=req.content_type,
            topic=req.topic,
            additional_requirements=req.additional_requirements,
            asset_ids=req.asset_ids,
            key_id=req.key_id,
            model=req.model,
            generation_mode=req.generation_mode,
            template_id=req.template_id,
        )
        return GenerationResponse(**result)
    except ValueError as e:
        raise error_response(ErrorCode.INVALID_REQUEST, detail=str(e)) from e
    except Exception as e:  # noqa: BLE001
        logger.exception("Generation creation failed")
        raise error_response(ErrorCode.INTERNAL_ERROR, detail=f"生成失败: {e}") from e


@router.get("/api/generations/{run_id}")
async def get_generation(run_id: str) -> Any:
    result = await generation_service.get_generation(run_id)
    if result is None:
        raise error_response(ErrorCode.RUN_NOT_FOUND, detail="未找到该次生成")
    return result


@router.post("/api/generations/{run_id}/continue")
async def continue_generation(run_id: str, req: ContinueRequest, request: Request) -> Any:
    try:
        user_id = get_user_id(request)
        result = await generation_service.continue_generation(run_id, req.content, user_id)
        return GenerationResponse(**result)
    except ValueError as e:
        raise error_response(ErrorCode.INVALID_REQUEST, detail=str(e)) from e


@router.post("/api/generations/{run_id}/variations")
async def create_variations(run_id: str, request: Request) -> Any:
    try:
        user_id = get_user_id(request)
        result = await generation_service.create_variations(run_id, user_id)
        return GenerationResponse(**result)
    except ValueError as e:
        raise error_response(ErrorCode.GENERATION_LIMIT, detail=str(e)) from e


@router.post("/api/generations/{run_id}/image")
async def generate_image(run_id: str, req: ImageRequest, request: Request) -> Any:
    user_id = get_user_id(request)
    try:
        result = await image_service.generate(
            run_id, req.prompt, provider=req.provider, key_id=req.key_id, user_id=user_id
        )
        return {"attachment_id": result.attachment_id, "storage_path": result.storage_path}
    except ValueError as e:
        raise error_response(ErrorCode.INVALID_REQUEST, detail=str(e)) from e


@router.post("/api/generations/{run_id}/compose")
async def compose_card(run_id: str, req: ComposeRequest) -> Any:
    try:
        result = await generation_service.compose_card(
            run_id, req.template_id, title=req.title, summary=req.summary
        )
        return result
    except ValueError as e:
        raise error_response(ErrorCode.TEMPLATE_NOT_FOUND, detail=str(e)) from e


@router.get("/api/compose-templates")
async def list_compose_templates() -> Any:
    from repository.compose_templates import list_templates

    templates = await list_templates()
    return [
        {"id": t.id, "name": t.name, "layout": t.layout_json, "is_default": t.is_default}
        for t in templates
    ]
