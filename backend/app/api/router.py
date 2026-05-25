"""Main API router – assembles all sub-routers under /api/v1."""

from fastapi import APIRouter

from app.api.tools import router as tools_router
from app.api.workflows import router as workflows_router
from app.api.generate import router as generate_router
from app.api.knowledge import router as knowledge_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(tools_router)
api_router.include_router(workflows_router)
api_router.include_router(generate_router)
api_router.include_router(knowledge_router)
