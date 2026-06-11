from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from uuid import UUID
from typing import List

from src.db.session import get_db
from src.db.models import Email, EmailStatus, AgentTrace
from src.api.schemas.models import EmailCreate, EmailResponse

router = APIRouter(prefix="/emails", tags=["emails"])

@router.post("/generate", response_model=EmailResponse)
async def generate_email(email_in: EmailCreate, db: AsyncSession = Depends(get_db)):
    db_email = Email(**email_in.model_dump())
    db_email.status = EmailStatus.DRAFT
    db.add(db_email)
    await db.commit()
    await db.refresh(db_email)
    return db_email

@router.post("/{email_id}/send", response_model=EmailResponse)
async def send_email(email_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Email).where(Email.id == email_id))
    email = result.scalar_one_or_none()
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")
    
    email.status = EmailStatus.SENT
    await db.commit()
    await db.refresh(email)
    return email

@router.get("/{email_id}/trace")
async def get_email_trace(email_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AgentTrace).where(AgentTrace.output_data.contains({"email_id": str(email_id)})))
    traces = result.scalars().all()
    return {"email_id": email_id, "traces": traces}
