"""
API v1 Router module.

This module aggregates all the v1 endpoint routers into a single APIRouter
instance which is then included in the main FastAPI application.

Attributes:
    router (APIRouter): The main APIRouter instance for v1 API.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    analytics,
    assistants,
    audio,
    auth,
    chat,
    connectors,
    dashboard,
    files,
    notifications,
    pricing,
    prompts,
    providers,
    settings,
    system,
    trending,
    users,
)

router: APIRouter = APIRouter()

# Register sub-routers for different modules
router.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])
router.include_router(assistants.router, prefix="/assistants", tags=["Assistants"])
router.include_router(audio.router, prefix="/audio", tags=["Audio"])
router.include_router(auth.router, prefix="/auth", tags=["Auth"])
router.include_router(chat.router, prefix="/chat", tags=["Chat"])
router.include_router(connectors.router, prefix="/connectors", tags=["Connectors"])
router.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])
router.include_router(files.router, prefix="/files", tags=["Files"])
router.include_router(notifications.router, prefix="/notifications", tags=["Notifications"])
router.include_router(pricing.router, prefix="/pricing", tags=["Pricing"])
router.include_router(prompts.router, prefix="/prompts", tags=["Prompts"])
router.include_router(providers.router, prefix="/providers", tags=["Providers"])
router.include_router(settings.router, prefix="/settings", tags=["Settings"])
router.include_router(system.router, prefix="/system", tags=["System"])
router.include_router(trending.router, prefix="/trends", tags=["Trending"])
router.include_router(users.router, prefix="/users", tags=["Users"])
