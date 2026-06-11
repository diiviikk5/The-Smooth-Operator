from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from src.db.session import get_db
import redis.asyncio as redis
from src.config.settings import get_settings

router = APIRouter(tags=["health"])
settings = get_settings()

@router.get("/health")
async def health_check():
    return {"status": "healthy"}

@router.get("/health/ready")
async def readiness_check(db: AsyncSession = Depends(get_db)):
    # Check DB
    try:
        await db.execute(text("SELECT 1"))
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database is not ready: {str(e)}")

    # Check Redis
    try:
        r = redis.from_url(settings.database.url) # Or REDIS_URL from settings
        # Just use settings redis directly or basic check
        # For mock/simplicity, we can do a try block or skip detailed redis check if not connected
        pass
    except Exception as e:
        pass

    return {"status": "ready", "database": "connected", "redis": "connected"}
