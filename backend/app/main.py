from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config.settings import settings
from app.core.logging_config import setup_logging, logger
from app.core.errors import register_exception_handlers
from app.api.router import api_router
from app.mcp.mcp_client import mcp_client_manager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup actions
    setup_logging()
    logger.info("Starting Universal Multi-Agent AI Assistant API Server...")
    
    # Initialize connection to all Model Context Protocol (MCP) servers
    try:
        await mcp_client_manager.start()
        logger.info("All configured MCP servers loaded.")
    except Exception as e:
        logger.error(f"Failed to load MCP servers on startup: {e}")

    yield
    
    # Shutdown actions
    logger.info("Stopping Universal Multi-Agent AI Assistant API Server...")
    await mcp_client_manager.stop()
    logger.info("Server cleanup complete.")

# Initialize FastAPI App
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust in production env config
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Error Handlers
register_exception_handlers(app)

# Include Router
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/health")
async def health_check():
    """Health check endpoint to test server connectivity."""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "mcp_servers": list(mcp_client_manager.sessions.keys())
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
