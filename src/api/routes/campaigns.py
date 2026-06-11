from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from uuid import UUID
from typing import List

from src.db.session import get_db
from src.db.models import Campaign, CampaignStatus
from src.api.schemas.models import CampaignCreate, CampaignResponse

router = APIRouter(prefix="/campaigns", tags=["campaigns"])

@router.post("", response_model=CampaignResponse)
async def create_campaign(campaign_in: CampaignCreate, db: AsyncSession = Depends(get_db)):
    db_campaign = Campaign(**campaign_in.model_dump())
    db_campaign.status = CampaignStatus.DRAFT
    db.add(db_campaign)
    await db.commit()
    await db.refresh(db_campaign)
    return db_campaign

@router.get("", response_model=List[CampaignResponse])
async def list_campaigns(limit: int = 100, offset: int = 0, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Campaign).offset(offset).limit(limit))
    return result.scalars().all()

@router.post("/{campaign_id}/launch", response_model=CampaignResponse)
async def launch_campaign(campaign_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Campaign).where(Campaign.id == campaign_id))
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    campaign.status = CampaignStatus.ACTIVE
    await db.commit()
    await db.refresh(campaign)
    return campaign

@router.get("/{campaign_id}/analytics")
async def get_campaign_analytics(campaign_id: UUID, db: AsyncSession = Depends(get_db)):
    # Standard metrics return mock / aggregated stats
    return {
        "campaign_id": campaign_id,
        "sent_emails": 120,
        "open_rate": 0.65,
        "reply_rate": 0.18,
        "bounce_rate": 0.02,
    }
