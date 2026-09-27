from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from app.core.logging_config import logger

class BaseAppException(Exception):
    """Base exception class for all custom application errors."""
    def __init__(self, message: str, status_code: int = 500, detail: str = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.detail = detail or message

class AuthenticationError(BaseAppException):
    def __init__(self, message: str = "Invalid credentials or expired token", detail: str = None):
        super().__init__(message, status_code=401, detail=detail)

class DatabaseError(BaseAppException):
    def __init__(self, message: str = "Database operation failed", detail: str = None):
        super().__init__(message, status_code=500, detail=detail)

class LLMGatewayError(BaseAppException):
    def __init__(self, message: str = "Error executing LLM request", detail: str = None):
        super().__init__(message, status_code=502, detail=detail)

class MCPClientError(BaseAppException):
    def __init__(self, message: str = "Model Context Protocol error", detail: str = None):
        super().__init__(message, status_code=502, detail=detail)

class AgentExecutionError(BaseAppException):
    def __init__(self, message: str = "Agent failed to execute step", detail: str = None):
        super().__init__(message, status_code=500, detail=detail)


def register_exception_handlers(app: FastAPI) -> None:
    """Registers exception handlers on the FastAPI app instance."""
    
    @app.exception_handler(BaseAppException)
    async def app_exception_handler(request: Request, exc: BaseAppException):
        logger.error(
            f"AppException: {exc.message} | Path: {request.url.path}", 
            exc_info=True,
            extra={"extra_fields": {"status_code": exc.status_code, "detail": exc.detail}}
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "error": exc.__class__.__name__,
                "message": exc.message,
                "detail": exc.detail
            }
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        logger.critical(
            f"Unhandled exception occurred on path: {request.url.path} | Error: {str(exc)}",
            exc_info=True
        )
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": "InternalServerError",
                "message": "An unexpected error occurred on the server.",
                "detail": str(exc) if app.debug else "Internal Server Error"
            }
        )
