"""Database module for The Smooth Operator.

Provides SQLAlchemy 2.0 async models and session management.

Usage:
    from src.db import Base, Lead, Campaign, Email
    from src.db.session import get_db
"""

from src.db.models import (
    AgentTrace,
    Base,
    Campaign,
    CampaignStatus,
    Email,
    EmailStatus,
    EmailTemplate,
    EvaluationResult,
    Lead,
    LeadStatus,
    TemplateFramework,
)
from src.db.session import async_engine, async_session_factory, get_db

__all__ = [
    "AgentTrace",
    "Base",
    "Campaign",
    "CampaignStatus",
    "Email",
    "EmailStatus",
    "EmailTemplate",
    "EvaluationResult",
    "Lead",
    "LeadStatus",
    "TemplateFramework",
    "async_engine",
    "async_session_factory",
    "get_db",
]
