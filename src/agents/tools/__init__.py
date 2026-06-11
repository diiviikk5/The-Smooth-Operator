"""Agent tools package for The Smooth Operator.

Provides LangChain @tool decorated functions for search, email,
and analysis operations used by the agentic layer.
"""

from src.agents.tools.search_tools import (
    web_search,
    company_lookup,
    tech_stack_detect,
    social_media_search,
)
from src.agents.tools.email_tools import (
    send_email,
    check_email_deliverability,
    track_email_open,
    get_email_status,
)
from src.agents.tools.analysis_tools import (
    analyze_website,
    extract_pain_points,
    compare_leads,
    calculate_campaign_metrics,
)

__all__ = [
    "web_search",
    "company_lookup",
    "tech_stack_detect",
    "social_media_search",
    "send_email",
    "check_email_deliverability",
    "track_email_open",
    "get_email_status",
    "analyze_website",
    "extract_pain_points",
    "compare_leads",
    "calculate_campaign_metrics",
]
