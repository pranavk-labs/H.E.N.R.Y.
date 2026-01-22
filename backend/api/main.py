"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes import health
from backend.config.settings import get_settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    # Startup
    logger.info("Starting H.E.N.R.Y. backend...")
    settings = get_settings()
    logger.info(f"Environment: {settings.app_env}")
    logger.info(f"Debug mode: {settings.debug}")

    yield

    # Shutdown
    logger.info("Shutting down H.E.N.R.Y. backend...")


# Create FastAPI app
app = FastAPI(
    title="H.E.N.R.Y. API",
    description="H.E.N.R.Y. - A personalized conversational desk assistant",
    version="0.1.0",
    lifespan=lifespan,
)

# Configure CORS
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router)

# Graph router
from backend.api.routes import graph as graph_router

app.include_router(graph_router.router)

# Productivity (tools) router
from backend.api.routes import productivity as productivity_router

app.include_router(productivity_router.router)

# Conversation and UI state router (Phase 3)
from backend.api.routes import conversation as conversation_router

app.include_router(conversation_router.router)

# Todo/task management router
from backend.api.routes import todos as todos_router

app.include_router(todos_router.router)

# Calendar router
from backend.api.routes import calendar as calendar_router

app.include_router(calendar_router.router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "H.E.N.R.Y.",
        "version": "0.1.0",
        "status": "running",
    }


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return {
        "error": "Internal server error",
        "detail": str(exc) if settings.debug else "An error occurred",
    }

