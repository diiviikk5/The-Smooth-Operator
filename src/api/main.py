\"\"\"Main FastAPI application entrypoint for The Smooth Operator.\"\"\"

from contextlib import asynccontextmanager
import time
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import structlog

from src.config.settings import get_settings
from src.api.routes import health, leads, emails, campaigns

# Configure structured logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamps(),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer(),
    ]
)
logger = structlog.get_logger()

settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic: init DB connections, cache connections, vector store
    logger.info("Starting up Smooth Operator API...")
    yield
    # Shutdown logic: clean up connections
    logger.info("Shutting down Smooth Operator API...")

app = FastAPI(
    title="The Smooth Operator API",
    description="AI-powered cold outreach engine with advanced RAG, lead enrichment, and campaign management.",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    logger.info(
        "http_request",
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        duration_ms=int(duration * 1000),
    )
    return response

# Include routers
app.include_router(health.router, prefix="/api/v1")
app.include_router(leads.router, prefix="/api/v1")
app.include_router(emails.router, prefix="/api/v1")
app.include_router(campaigns.router, prefix="/api/v1")
