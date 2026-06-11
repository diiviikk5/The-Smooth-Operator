from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
from uuid import UUID

from src.db.session import get_db
from src.db.models import Lead, LeadStatus
from src.api.schemas.models import LeadCreate, LeadResponse, LeadUpdate

router = APIRouter(prefix="/leads", tags=["leads"])

@router.post("", response_model=LeadResponse)
async def create_lead(lead_in: LeadCreate, db: AsyncSession = Depends(get_db)):
    db_lead = Lead(**lead_in.model_dump())
    db.add(db_lead)
    await db.commit()
    await db.refresh(db_lead)
    return db_lead

@router.get("", response_model=List[LeadResponse])
async def list_leads(limit: int = 100, offset: int = 0, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Lead).offset(offset).limit(limit))
    return result.scalars().all()

@router.get("/{lead_id}", response_model=LeadResponse)
async def get_lead(lead_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead

@router.patch("/{lead_id}", response_model=LeadResponse)
async def update_lead(lead_id: UUID, lead_in: LeadUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    update_data = lead_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(lead, field, value)
        
    await db.commit()
    await db.refresh(lead)
    return lead

@router.delete("/{lead_id}")
async def delete_lead(lead_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    await db.delete(lead)
    await db.commit()
    return {"message": "Lead deleted successfully"}

# Trigger scraper, enrich, score, search
@router.post("/{lead_id}/scrape", response_model=LeadResponse)
async def scrape_lead(lead_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    # Normally we would trigger scraping async here
    lead.status = LeadStatus.ENRICHED
    await db.commit()
    await db.refresh(lead)
    return lead

@router.post("/{lead_id}/enrich", response_model=LeadResponse)
async def enrich_lead(lead_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    # Normally trigger enrichment async
    await db.commit()
    return lead

@router.post("/{lead_id}/score", response_model=LeadResponse)
async def score_lead(lead_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    # Score lead
    lead.score = 85.0
    lead.score_reasoning = "Ideal fit: high tech stack alignment and buyer signals."
    lead.status = LeadStatus.SCORED
    await db.commit()
    await db.refresh(lead)
    return lead

@router.get("/search", response_model=List[LeadResponse])
async def search_leads(q: str = Query(..., min_length=1), db: AsyncSession = Depends(get_db)):
    # Simple semantic search placeholder for database query
    result = await db.execute(select(Lead).where(Lead.name.ilike(f"%{q}%")))
    return result.scalars().all()
