"""Analysis tools for The Smooth Operator agents.

Provides LangChain @tool decorated functions for website analysis,
pain point extraction, lead comparison, and campaign metrics calculation.
"""

from __future__ import annotations

import json
import logging
import re
import time
from collections import Counter
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from src.config.settings import get_settings

logger = logging.getLogger(__name__)


class WebsiteAnalysis(BaseModel):
    """Structured website analysis result."""

    url: str = ""
    title: str = ""
    meta_description: str = ""
    primary_language: str = "en"
    page_count_estimate: int = 0
    has_blog: bool = False
    has_pricing: bool = False
    has_careers: bool = False
    has_api_docs: bool = False
    products_services: List[str] = Field(default_factory=list)
    target_audience: str = ""
    value_proposition: str = ""
    cta_text: List[str] = Field(default_factory=list)
    social_links: Dict[str, str] = Field(default_factory=dict)
    content_themes: List[str] = Field(default_factory=list)
    seo_signals: Dict[str, Any] = Field(default_factory=dict)
    load_time_ms: Optional[float] = None


class PainPoint(BaseModel):
    """Identified pain point from content analysis."""

    category: str = ""
    description: str = ""
    severity: str = "medium"
    evidence: str = ""
    source: str = ""
    confidence: float = 0.0


class LeadComparison(BaseModel):
    """Comparison report between leads."""

    lead_ids: List[str] = Field(default_factory=list)
    similarities: List[str] = Field(default_factory=list)
    differences: List[str] = Field(default_factory=list)
    recommended_approach: str = ""
    highest_priority: str = ""
    scores: Dict[str, float] = Field(default_factory=dict)


class CampaignMetrics(BaseModel):
    """Campaign performance metrics summary."""

    campaign_id: str = ""
    total_leads: int = 0
    emails_sent: int = 0
    emails_opened: int = 0
    emails_replied: int = 0
    positive_replies: int = 0
    meetings_booked: int = 0
    open_rate: float = 0.0
    reply_rate: float = 0.0
    positive_reply_rate: float = 0.0
    meeting_rate: float = 0.0
    avg_lead_score: float = 0.0
    avg_email_quality: float = 0.0
    total_cost: float = 0.0
    cost_per_lead: float = 0.0
    cost_per_meeting: float = 0.0
    top_performing_subject: str = ""
    top_performing_framework: str = ""
    recommendations: List[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Pain-point extraction patterns
# ---------------------------------------------------------------------------

PAIN_POINT_PATTERNS = {
    "scaling_challenges": [
        r"(?:struggle|struggling|difficult|hard|challenge|challenging)\s+(?:to\s+)?(?:scale|grow|expand)",
        r"(?:can't|cannot|unable to)\s+(?:keep up|handle|manage)\s+(?:growth|demand|volume)",
        r"(?:bottleneck|constraint|limitation)\s+(?:in|with|on)\s+(?:growth|scaling)",
    ],
    "manual_processes": [
        r"(?:manual|tedious|time-consuming|repetitive)\s+(?:process|task|work|workflow)",
        r"(?:still|currently)\s+(?:using|doing|handling)\s+(?:manually|by hand|spreadsheet)",
        r"(?:automate|automation)\s+(?:is|would be|could be)\s+(?:needed|helpful|critical)",
    ],
    "data_quality": [
        r"(?:dirty|messy|inconsistent|unreliable|inaccurate)\s+(?:data|information|records)",
        r"(?:data\s+)?(?:quality|integrity|accuracy)\s+(?:issue|problem|concern|challenge)",
        r"(?:single source of truth|data silo|fragmented data)",
    ],
    "team_productivity": [
        r"(?:team|employee|staff)\s+(?:productivity|efficiency|performance)\s+(?:issue|problem|decline|low)",
        r"(?:burnout|overwork|turnover|retention)\s+(?:issue|problem|concern|rate)",
        r"(?:collaboration|communication)\s+(?:gap|issue|problem|breakdown)",
    ],
    "customer_acquisition": [
        r"(?:customer|lead)\s+(?:acquisition|generation|conversion)\s+(?:cost|challenge|problem)",
        r"(?:CAC|cost per acquisition)\s+(?:is|has been|continues to be)\s+(?:high|rising|increasing)",
        r"(?:pipeline|funnel)\s+(?:issue|problem|leak|dry)",
    ],
    "technical_debt": [
        r"(?:technical debt|legacy|outdated|old)\s+(?:system|infrastructure|code|platform)",
        r"(?:migration|modernization|upgrade)\s+(?:needed|planned|overdue)",
        r"(?:security|compliance|regulation)\s+(?:concern|risk|issue|requirement)",
    ],
    "revenue_pressure": [
        r"(?:revenue|margin|profit)\s+(?:pressure|decline|stagnation|challenge)",
        r"(?:budget|cost)\s+(?:cut|reduction|constraint|pressure|squeeze)",
        r"(?:ROI|return on investment)\s+(?:concern|pressure|need to demonstrate)",
    ],
}


@tool
def analyze_website(url: str) -> str:
    """Analyze a website to extract business intelligence.

    Performs comprehensive analysis of a website including structure,
    content themes, value proposition, target audience, and SEO signals.

    Args:
        url: The website URL to analyze.

    Returns:
        JSON string with structured website analysis.
    """
    logger.info("analyze_website called for url=%r", url)

    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"

    analysis = WebsiteAnalysis(url=url)
    start_time = time.time()

    try:
        import httpx

        settings = get_settings()
        with httpx.Client(
            timeout=settings.scraping.timeout,
            follow_redirects=True,
            headers={"User-Agent": settings.scraping.user_agent},
        ) as client:
            response = client.get(url)
            html = response.text

        analysis.load_time_ms = round((time.time() - start_time) * 1000, 2)

        # Extract title
        title_match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
        if title_match:
            analysis.title = title_match.group(1).strip()[:200]

        # Extract meta description
        meta_match = re.search(
            r'<meta\s+[^>]*name=["\']description["\']\s+[^>]*content=["\'](.*?)["\']',
            html, re.IGNORECASE,
        )
        if not meta_match:
            meta_match = re.search(
                r'<meta\s+[^>]*content=["\'](.*?)["\']\s+[^>]*name=["\']description["\']',
                html, re.IGNORECASE,
            )
        if meta_match:
            analysis.meta_description = meta_match.group(1).strip()[:300]

        # Detect key pages
        html_lower = html.lower()
        analysis.has_blog = any(
            p in html_lower for p in ["/blog", "/posts", "/articles", "/news"]
        )
        analysis.has_pricing = any(
            p in html_lower for p in ["/pricing", "/plans", "pricing-table"]
        )
        analysis.has_careers = any(
            p in html_lower for p in ["/careers", "/jobs", "/hiring", "work-with-us"]
        )
        analysis.has_api_docs = any(
            p in html_lower for p in ["/api", "/docs", "/developer", "/documentation"]
        )

        # Count internal links as page estimate
        internal_links = re.findall(
            r'href=["\'](/[^"\']*?)["\']', html
        )
        unique_paths = set()
        for link in internal_links:
            path = link.split("?")[0].split("#")[0]
            if path and path != "/":
                unique_paths.add(path)
        analysis.page_count_estimate = len(unique_paths) + 1

        # Extract CTAs
        cta_patterns = [
            r'<(?:a|button)[^>]*class="[^"]*(?:cta|btn-primary|button-primary)[^"]*"[^>]*>(.*?)</(?:a|button)>',
            r'<(?:a|button)[^>]*>((?:Get Started|Sign Up|Try Free|Book a Demo|Schedule|Contact Us|Learn More|Start Free Trial|Request Demo)[^<]*)</(?:a|button)>',
        ]
        ctas = set()
        for pattern in cta_patterns:
            matches = re.findall(pattern, html, re.IGNORECASE)
            for match in matches:
                cleaned = re.sub(r"<[^>]+>", "", match).strip()
                if 2 <= len(cleaned) <= 50:
                    ctas.add(cleaned)
        analysis.cta_text = list(ctas)[:10]

        # Extract social links
        social_patterns = {
            "twitter": r'href=["\'](https?://(?:www\.)?(?:twitter|x)\.com/[^"\']+)["\']',
            "linkedin": r'href=["\'](https?://(?:www\.)?linkedin\.com/[^"\']+)["\']',
            "github": r'href=["\'](https?://(?:www\.)?github\.com/[^"\']+)["\']',
            "facebook": r'href=["\'](https?://(?:www\.)?facebook\.com/[^"\']+)["\']',
            "youtube": r'href=["\'](https?://(?:www\.)?youtube\.com/[^"\']+)["\']',
        }
        for platform, pattern in social_patterns.items():
            match = re.search(pattern, html, re.IGNORECASE)
            if match:
                analysis.social_links[platform] = match.group(1)

        # Extract content themes via heading analysis
        headings = re.findall(r"<h[1-3][^>]*>(.*?)</h[1-3]>", html, re.IGNORECASE | re.DOTALL)
        cleaned_headings = [re.sub(r"<[^>]+>", "", h).strip() for h in headings]
        cleaned_headings = [h for h in cleaned_headings if 3 <= len(h) <= 100]
        analysis.content_themes = cleaned_headings[:15]

        # Infer value proposition from hero section / first heading
        if analysis.content_themes:
            analysis.value_proposition = analysis.content_themes[0]
        elif analysis.meta_description:
            analysis.value_proposition = analysis.meta_description

        # SEO signals
        analysis.seo_signals = {
            "has_title": bool(analysis.title),
            "has_meta_description": bool(analysis.meta_description),
            "has_h1": bool(re.search(r"<h1[^>]*>", html, re.IGNORECASE)),
            "has_structured_data": "application/ld+json" in html_lower,
            "has_og_tags": 'property="og:' in html_lower or "property='og:" in html_lower,
            "has_canonical": 'rel="canonical"' in html_lower,
            "has_sitemap_link": "sitemap" in html_lower,
            "has_robots_meta": 'name="robots"' in html_lower,
        }

        # Infer target audience from content
        audience_signals = []
        if analysis.has_api_docs:
            audience_signals.append("developers")
        if analysis.has_pricing:
            audience_signals.append("business buyers")
        if re.search(r"enterprise|Fortune 500|large organization", html, re.IGNORECASE):
            audience_signals.append("enterprise")
        if re.search(r"small business|SMB|startup|solopreneur", html, re.IGNORECASE):
            audience_signals.append("SMB/startup")
        analysis.target_audience = ", ".join(audience_signals) if audience_signals else "general"

    except ImportError:
        logger.warning("httpx not installed – returning minimal analysis")
        analysis.seo_signals = {"error": "httpx required for full analysis"}
    except Exception as exc:
        logger.error("analyze_website failed for %r: %s", url, exc, exc_info=True)
        analysis.seo_signals = {"error": str(exc)}

    return analysis.model_dump_json(indent=2)


@tool
def extract_pain_points(content: str) -> str:
    """Extract potential pain points from text content.

    Analyzes content (blog posts, website copy, social posts, interviews)
    to identify business pain points that could be addressed in outreach.

    Args:
        content: The text content to analyze for pain points.

    Returns:
        JSON string with list of identified pain points with severity and confidence.
    """
    logger.info("extract_pain_points called with %d chars of content", len(content))

    pain_points: List[PainPoint] = []
    content_lower = content.lower()

    for category, patterns in PAIN_POINT_PATTERNS.items():
        for pattern in patterns:
            matches = list(re.finditer(pattern, content, re.IGNORECASE))
            for match in matches:
                # Extract surrounding context (±100 chars)
                start = max(0, match.start() - 100)
                end = min(len(content), match.end() + 100)
                context = content[start:end].strip()

                # Determine severity based on language intensity
                severity = _assess_severity(match.group(0))

                pain_points.append(
                    PainPoint(
                        category=category.replace("_", " ").title(),
                        description=_summarize_pain_point(category, match.group(0)),
                        severity=severity,
                        evidence=context,
                        source="content_analysis",
                        confidence=_calculate_confidence(match.group(0), context),
                    )
                )

    # General sentiment-based pain point detection
    negative_phrases = [
        (r"(?:we|our team|our company)\s+(?:need|must|have to|should)\s+(.{10,80})", "stated_need"),
        (r"(?:biggest|main|key|top)\s+(?:challenge|problem|issue|concern|priority)\s+(?:is|are|was)\s+(.{10,80})", "explicit_challenge"),
        (r"(?:frustrated|annoyed|disappointed|unhappy)\s+(?:with|by|about)\s+(.{10,80})", "frustration"),
        (r"(?:wish|hope|looking for|searching for|need)\s+(?:a|an|the)?\s*(?:better|easier|faster|simpler|more efficient)\s+(.{10,80})", "desire"),
    ]

    for pattern, source_type in negative_phrases:
        matches = list(re.finditer(pattern, content, re.IGNORECASE))
        for match in matches:
            full_match = match.group(0)
            specific = match.group(1) if match.lastindex and match.lastindex >= 1 else full_match

            start = max(0, match.start() - 50)
            end = min(len(content), match.end() + 50)
            context = content[start:end].strip()

            pain_points.append(
                PainPoint(
                    category=source_type.replace("_", " ").title(),
                    description=specific.strip().rstrip(".,;!"),
                    severity="medium",
                    evidence=context,
                    source="sentiment_analysis",
                    confidence=0.6,
                )
            )

    # Deduplicate by similar descriptions
    seen_descriptions: set = set()
    unique_points: List[PainPoint] = []
    for pp in pain_points:
        desc_key = pp.description.lower()[:50]
        if desc_key not in seen_descriptions:
            seen_descriptions.add(desc_key)
            unique_points.append(pp)

    # Sort by confidence then severity
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    unique_points.sort(
        key=lambda p: (severity_order.get(p.severity, 2), -p.confidence)
    )

    logger.info("Extracted %d pain points from content", len(unique_points))
    return json.dumps([p.model_dump() for p in unique_points[:20]], indent=2)


@tool
def compare_leads(lead_ids: list) -> str:  # type: ignore[type-arg]
    """Compare multiple leads to identify patterns and prioritize outreach.

    Takes a list of lead IDs (or lead data dicts serialized as a JSON string
    if the leads aren't stored), compares them across key dimensions, and
    recommends prioritization.

    Args:
        lead_ids: List of lead identifiers or serialized lead data dicts.

    Returns:
        JSON string with comparison report including similarities,
        differences, and prioritization recommendation.
    """
    logger.info("compare_leads called with %d leads", len(lead_ids))

    comparison = LeadComparison(lead_ids=[str(lid) for lid in lead_ids])

    # If lead_ids are actually serialized lead data, try parsing
    leads_data: List[Dict[str, Any]] = []
    for lid in lead_ids:
        if isinstance(lid, dict):
            leads_data.append(lid)
        elif isinstance(lid, str):
            try:
                parsed = json.loads(lid)
                if isinstance(parsed, dict):
                    leads_data.append(parsed)
                else:
                    leads_data.append({"id": lid})
            except json.JSONDecodeError:
                leads_data.append({"id": lid})
        else:
            leads_data.append({"id": str(lid)})

    if len(leads_data) < 2:
        comparison.similarities = ["Insufficient data for comparison"]
        return comparison.model_dump_json(indent=2)

    # Compare across dimensions
    all_industries = [d.get("industry", "unknown") for d in leads_data]
    all_company_sizes = [d.get("employee_count", "unknown") for d in leads_data]
    all_roles = [d.get("role", "unknown") for d in leads_data]
    all_tech_stacks = [set(d.get("tech_stack", [])) for d in leads_data]

    # Find similarities
    if len(set(all_industries)) == 1 and all_industries[0] != "unknown":
        comparison.similarities.append(f"All leads are in the {all_industries[0]} industry")
    if len(set(all_roles)) == 1 and all_roles[0] != "unknown":
        comparison.similarities.append(f"All leads have the role: {all_roles[0]}")

    # Tech stack overlap
    if all_tech_stacks and all(ts for ts in all_tech_stacks):
        common_tech = set.intersection(*all_tech_stacks) if all_tech_stacks else set()
        if common_tech:
            comparison.similarities.append(f"Shared technologies: {', '.join(common_tech)}")

    # Find differences
    if len(set(all_industries)) > 1:
        comparison.differences.append(f"Different industries: {', '.join(set(all_industries))}")
    if len(set(all_company_sizes)) > 1:
        comparison.differences.append(f"Varying company sizes: {', '.join(set(str(s) for s in all_company_sizes))}")

    # Score and prioritize
    for i, lead in enumerate(leads_data):
        score = 50.0  # Base score
        if lead.get("score"):
            score = float(lead["score"])
        elif lead.get("buying_signals"):
            score += len(lead["buying_signals"]) * 10
        if lead.get("recent_activity"):
            score += 15
        comparison.scores[str(lead.get("id", f"lead_{i}"))] = round(score, 1)

    # Determine highest priority
    if comparison.scores:
        best_id = max(comparison.scores, key=comparison.scores.get)  # type: ignore[arg-type]
        comparison.highest_priority = best_id
        comparison.recommended_approach = (
            f"Prioritize {best_id} (score: {comparison.scores[best_id]}). "
            f"Consider batch-similar leads for template efficiency."
        )

    return comparison.model_dump_json(indent=2)


@tool
def calculate_campaign_metrics(campaign_id: str) -> str:
    """Calculate comprehensive performance metrics for a campaign.

    Aggregates data from email sends, opens, replies, and conversions
    to produce a full campaign performance report with recommendations.

    Args:
        campaign_id: The unique identifier of the campaign.

    Returns:
        JSON string with detailed campaign metrics and recommendations.
    """
    logger.info("calculate_campaign_metrics called for campaign_id=%r", campaign_id)

    from src.agents.tools.email_tools import _email_store

    # Gather campaign emails from store
    campaign_emails = [
        e for e in _email_store.values()
        if e.get("campaign_id") == campaign_id or campaign_id == "all"
    ]

    metrics = CampaignMetrics(campaign_id=campaign_id)

    if not campaign_emails:
        # Generate metrics from whatever emails exist in the store
        campaign_emails = list(_email_store.values())

    metrics.total_leads = len(campaign_emails)
    metrics.emails_sent = sum(1 for e in campaign_emails if e.get("status") in ("sent", "dry_run"))
    metrics.emails_opened = sum(1 for e in campaign_emails if e.get("open_count", 0) > 0)
    metrics.emails_replied = sum(1 for e in campaign_emails if e.get("replied"))
    metrics.positive_replies = sum(1 for e in campaign_emails if e.get("reply_sentiment") == "positive")
    metrics.meetings_booked = sum(1 for e in campaign_emails if e.get("meeting_booked"))

    # Calculate rates
    if metrics.emails_sent > 0:
        metrics.open_rate = round(metrics.emails_opened / metrics.emails_sent, 4)
        metrics.reply_rate = round(metrics.emails_replied / metrics.emails_sent, 4)
        metrics.positive_reply_rate = round(metrics.positive_replies / metrics.emails_sent, 4)
        metrics.meeting_rate = round(metrics.meetings_booked / metrics.emails_sent, 4)

    # Calculate costs
    metrics.total_cost = sum(e.get("cost", 0.0) for e in campaign_emails)
    if metrics.total_leads > 0:
        metrics.cost_per_lead = round(metrics.total_cost / metrics.total_leads, 4)
    if metrics.meetings_booked > 0:
        metrics.cost_per_meeting = round(metrics.total_cost / metrics.meetings_booked, 2)

    # Find top performers
    subject_performance: Dict[str, List[float]] = {}
    framework_performance: Dict[str, List[float]] = {}
    for e in campaign_emails:
        subj = e.get("subject", "unknown")
        fw = e.get("framework", "unknown")
        opened = 1.0 if e.get("open_count", 0) > 0 else 0.0
        subject_performance.setdefault(subj, []).append(opened)
        framework_performance.setdefault(fw, []).append(opened)

    if subject_performance:
        best_subject = max(
            subject_performance,
            key=lambda k: sum(subject_performance[k]) / len(subject_performance[k]),
        )
        metrics.top_performing_subject = best_subject

    if framework_performance:
        best_fw = max(
            framework_performance,
            key=lambda k: sum(framework_performance[k]) / len(framework_performance[k]),
        )
        metrics.top_performing_framework = best_fw

    # Generate recommendations
    recommendations: List[str] = []
    if metrics.open_rate < 0.3:
        recommendations.append(
            "Open rate below 30% – consider A/B testing subject lines and improving sender reputation."
        )
    if metrics.reply_rate < 0.05:
        recommendations.append(
            "Reply rate below 5% – review email personalization and CTA clarity."
        )
    if metrics.open_rate > 0.5 and metrics.reply_rate < 0.1:
        recommendations.append(
            "High open rate but low replies – emails are getting attention but content needs improvement."
        )
    if metrics.positive_reply_rate < 0.02:
        recommendations.append(
            "Very low positive reply rate – revisit ICP targeting and value proposition."
        )
    if not recommendations:
        recommendations.append("Campaign performing within normal parameters. Continue monitoring.")

    metrics.recommendations = recommendations

    return metrics.model_dump_json(indent=2)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _assess_severity(matched_text: str) -> str:
    """Assess the severity of a pain point based on language intensity.

    Args:
        matched_text: The text that matched a pain point pattern.

    Returns:
        Severity level: critical, high, medium, or low.
    """
    text_lower = matched_text.lower()
    critical_words = {"critical", "urgent", "crisis", "emergency", "breaking", "failing"}
    high_words = {"major", "significant", "serious", "severe", "constantly", "always"}
    low_words = {"minor", "slight", "sometimes", "occasionally", "small"}

    if any(w in text_lower for w in critical_words):
        return "critical"
    elif any(w in text_lower for w in high_words):
        return "high"
    elif any(w in text_lower for w in low_words):
        return "low"
    return "medium"


def _summarize_pain_point(category: str, matched_text: str) -> str:
    """Generate a concise description of a pain point.

    Args:
        category: The pain point category.
        matched_text: The matched text.

    Returns:
        Concise description.
    """
    category_descriptions = {
        "scaling_challenges": "Difficulty scaling operations or infrastructure",
        "manual_processes": "Reliance on manual or time-consuming processes",
        "data_quality": "Data quality or data management issues",
        "team_productivity": "Team productivity or retention challenges",
        "customer_acquisition": "Customer acquisition cost or pipeline issues",
        "technical_debt": "Technical debt or legacy system constraints",
        "revenue_pressure": "Revenue or margin pressure",
    }
    base = category_descriptions.get(category, f"Issue related to {category}")
    # Append specific context from matched text
    specific = matched_text.strip()
    if len(specific) > 10:
        return f"{base}: '{specific[:80]}'"
    return base


def _calculate_confidence(matched_text: str, context: str) -> float:
    """Calculate confidence score for a pain point detection.

    Args:
        matched_text: The directly matched text.
        context: Surrounding context.

    Returns:
        Confidence score between 0 and 1.
    """
    confidence = 0.5  # Base confidence for pattern match

    # Boost for explicit language
    if re.search(r"(?:we|our|I|my)\s+(?:need|struggle|face)", context, re.IGNORECASE):
        confidence += 0.2  # First-person context increases confidence

    # Boost for specificity
    if re.search(r"\d+%|\$[\d,]+|\d+\s+(?:hours|days|weeks)", context):
        confidence += 0.15  # Quantified pain points are more reliable

    # Reduce for hypothetical language
    if re.search(r"(?:might|could|may|possibly|perhaps|if)", matched_text, re.IGNORECASE):
        confidence -= 0.15

    return round(max(0.1, min(confidence, 1.0)), 2)
