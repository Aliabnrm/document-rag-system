from fastapi import APIRouter

from app.api.routes.health import router as health_router
from app.modules.collections.presentation.routes import router as collections_router
from app.modules.conversations.presentation.routes import (
    collection_router as conversation_collection_router,
)
from app.modules.conversations.presentation.routes import (
    conversation_router,
)
from app.modules.documents.presentation.routes import router as documents_router

api_router = APIRouter()
api_router.include_router(health_router, tags=["system"])
api_router.include_router(collections_router)
api_router.include_router(documents_router)
api_router.include_router(conversation_collection_router)
api_router.include_router(conversation_router)
