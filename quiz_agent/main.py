# main.py
import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from settings import settings
from routes.chat_router import router
from utils.logger import logger
from repositories.database.connection import test_connection
from migration.create_tables import Migration


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events"""
    logger.info("=" * 60)
    logger.info("Quiz & Review Multi-Agent System STARTING")
    logger.info("=" * 60)

    # Test database connection and run migrations
    if test_connection():
        logger.info("Database connected successfully")
        logger.info("Running database migrations...")
        try:
            migration = Migration()
            migration.create_tables()
            logger.info("Database migrations completed successfully")
        except Exception as e:
            logger.error(f"Database migration failed: {e}")
    else:
        logger.warning("Database connection failed - error logging may not work")

    logger.info(f"Server ready at http://{settings.HOST}:{settings.PORT}")
    logger.info(f"API Docs available at http://{settings.HOST}:{settings.PORT}/docs")
    logger.info(f"LLM Provider: {settings.LLM_PROVIDER} ({settings.OLLAMA_MODEL if settings.LLM_PROVIDER == 'ollama' else settings.BEDROCK_MODEL_ID})")
    logger.info("=" * 60)

    yield

    logger.info("Shutting down Quiz & Review Multi-Agent System")


def create_app() -> FastAPI:
    """Create and configure FastAPI application"""
    app = FastAPI(
        title="Quiz & Review Multi-Agent System",
        description="Quiz & Review Multi-Agent System generates quiz questions and validates answers using LangGraph.",
        version="1.0.0",
        lifespan=lifespan,
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routes
    app.include_router(router, prefix="/api/v1", tags=["chat"])

    @app.get("/health", tags=["health"])
    async def health():
        return {
            "status": "healthy",
            "service": "Quiz & Review Multi-Agent System",
            "provider": settings.LLM_PROVIDER,
        }

    return app


app = create_app()


def run_client():
    """Run the client server"""
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=int(settings.PORT),
        reload=True,
        access_log=True,
        log_level="info",
    )


if __name__ == "__main__":
    try:
        run_client()
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server startup failed: {e}")
        exit(1)