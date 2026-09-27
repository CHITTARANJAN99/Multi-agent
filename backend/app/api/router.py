from fastapi import APIRouter
from app.api.endpoints.auth_router import router as auth_router
from app.api.endpoints.agent_router import router as agent_router
from app.api.endpoints.mcp_router import router as mcp_router

api_router = APIRouter()

# Include endpoints routers
api_router.include_router(auth_router)
api_router.include_router(agent_router)
api_router.include_router(mcp_router)
