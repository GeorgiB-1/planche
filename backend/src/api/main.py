"""
Planche.bg API - Main FastAPI Application Entry Point

AI Interior Design Platform for Bulgaria.
Combines all routers and middleware into a single FastAPI application.

Run with:
    uvicorn src.api.main:app --host 0.0.0.0 --port 8000
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.api.routes_product import router as product_router

app = FastAPI(
    title="Planche.bg API",
    description="AI Interior Design Platform for Bulgaria",
    version="0.1.0",
)

# ---------------------------------------------------------------------------
# CORS middleware (allow all origins for MVP -- restrict in production)
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Global exception handler
# ---------------------------------------------------------------------------
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch unhandled exceptions and return structured JSON error responses."""
    error_type = type(exc).__name__

    # Map known error types to user-friendly messages
    error_messages = {
        "ValueError": "Невалидна заявка. Моля, проверете данните.",  # Invalid request
        "FileNotFoundError": "Файлът не е намерен.",  # File not found
        "ConnectionError": "Грешка при свързване с услугата.",  # Connection error
        "TimeoutError": "Заявката отне твърде дълго време.",  # Request timeout
    }

    message = error_messages.get(error_type, "Възникна неочаквана грешка.")  # Unexpected error

    # Log the error with context
    print(f"[api] ERROR {error_type}: {exc} | Path: {request.url.path}")

    # Determine status code
    status_code = 500
    if isinstance(exc, ValueError):
        status_code = 400
    elif isinstance(exc, FileNotFoundError):
        status_code = 404

    return JSONResponse(
        status_code=status_code,
        content={
            "error": error_type,
            "message": message,
            "detail": str(exc) if status_code < 500 else None,
        },
    )


# ---------------------------------------------------------------------------
# Include routers
# ---------------------------------------------------------------------------
app.include_router(product_router)

# Phase 4: design routes (not yet implemented)
try:
    from src.api.routes_design import router as design_router

    app.include_router(design_router)
except ImportError:
    pass


# ---------------------------------------------------------------------------
# Root & health-check endpoints
# ---------------------------------------------------------------------------
@app.get("/")
async def root():
    """Root endpoint returning basic API information."""
    return {
        "name": "Planche.bg API",
        "version": "0.1.0",
        "status": "running",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring and load balancers."""
    return {"status": "healthy"}


# ---------------------------------------------------------------------------
# Convenience: run directly with `python -m src.api.main`
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("src.api.main:app", host="0.0.0.0", port=8000, reload=True)
