"""Voice runtime lifecycle API routes."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from backend.services.voice_runtime_service import VoiceRuntimeService

router = APIRouter(prefix="/voice-runtime", tags=["voice-runtime"])


class ModelRequest(BaseModel):
    """Optional model override for preload/unload requests."""

    model: Optional[str] = None


@router.get("/status")
async def runtime_status():
    """Return current voice runtime status."""
    return VoiceRuntimeService.get_instance().status()


@router.post("/start")
async def runtime_start():
    """Start the configured voice runtime."""
    return await VoiceRuntimeService.get_instance().start()


@router.post("/stop")
async def runtime_stop():
    """Stop the configured voice runtime."""
    return await VoiceRuntimeService.get_instance().stop()


@router.post("/preload")
async def runtime_preload(payload: ModelRequest):
    """Preload the configured or requested LLM."""
    return await VoiceRuntimeService.get_instance().preload_llm(payload.model)


@router.post("/unload")
async def runtime_unload(payload: ModelRequest):
    """Unload the configured or requested LLM."""
    return await VoiceRuntimeService.get_instance().unload_llm(payload.model)
