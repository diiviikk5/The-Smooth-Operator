from pydantic import BaseModel, EmailStr, HttpUrl
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
from src.db.models import LeadStatus, CampaignStatus, EmailStatus, TemplateFramework

# Lead Schemas
class LeadBase(BaseModel):
    name: str
    email: EmailStr
    company: str
    role: str
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None
    website: Optional[str] = None

class LeadCreate(LeadBase):
    pass

class LeadUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    company: Optional[str] = None
    role: Optional[str] = None
    status: Optional[LeadStatus] = None
    tech_stack: Optional[Dict[str, Any]] = None
    pain_points: Optional[Dict[str, Any]] = None
    recent_activity: Optional[Dict[str, Any]] = None
    enrichment_data: Optional[Dict[str, Any]] = None
    score: Optional[float] = None
    score_reasoning: Optional[str] = None

class LeadResponse(LeadBase):
    id: UUID
    status: LeadStatus
    tech_stack: Optional[Dict[str, Any]] = None
    pain_points: Optional[Dict[str, Any]] = None
    recent_activity: Optional[Dict[str, Any]] = None
    enrichment_data: Optional[Dict[str, Any]] = None
    score: Optional[float] = None
    score_reasoning: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# Campaign Schemas
class CampaignBase(BaseModel):
    name: str
    description: Optional[str] = None
    target_icp: Dict[str, Any]
    email_template_id: Optional[UUID] = None
    settings: Optional[Dict[str, Any]] = None

class CampaignCreate(CampaignBase):
    pass

class CampaignResponse(CampaignBase):
    id: UUID
    status: CampaignStatus
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# Email Template Schemas
class EmailTemplateBase(BaseModel):
    name: str
    subject_template: str
    body_template: str
    framework: TemplateFramework
    variables: Dict[str, Any]

class EmailTemplateCreate(EmailTemplateBase):
    pass

class EmailTemplateResponse(EmailTemplateBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# Email Schemas
class EmailBase(BaseModel):
    lead_id: UUID
    campaign_id: UUID
    subject: str
    body: str
    personalization_data: Optional[Dict[str, Any]] = None
    ab_variant: Optional[str] = None

class EmailCreate(EmailBase):
    pass

class EmailResponse(EmailBase):
    id: UUID
    status: EmailStatus
    sent_at: Optional[datetime] = None
    opened_at: Optional[datetime] = None
    replied_at: Optional[datetime] = None
    follow_up_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
