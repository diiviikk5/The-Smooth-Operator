"""Email tools for The Smooth Operator agents.

Provides LangChain @tool decorated functions for sending emails, checking
deliverability, tracking opens, and checking email status. Integrates with
SMTP and configurable email service providers.
"""

from __future__ import annotations

import email.mime.multipart
import email.mime.text
import hashlib
import json
import logging
import re
import smtplib
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from src.config.settings import get_settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# In-memory stores (production would use Redis / DB)
# ---------------------------------------------------------------------------

_email_store: Dict[str, Dict[str, Any]] = {}
_tracking_store: Dict[str, Dict[str, Any]] = {}
_daily_send_counts: Dict[str, int] = {}  # date_sender → count


class EmailSendResult(BaseModel):
    """Result of an email send operation."""

    email_id: str = ""
    status: str = "pending"
    to: str = ""
    subject: str = ""
    sent_at: Optional[str] = None
    error: Optional[str] = None
    tracking_id: Optional[str] = None


class DeliverabilityResult(BaseModel):
    """Email deliverability analysis result."""

    email: str = ""
    is_valid_format: bool = False
    is_disposable: bool = False
    is_role_based: bool = False
    has_mx_record: bool = False
    deliverability_score: float = 0.0
    risk_level: str = "unknown"
    checks_performed: List[str] = Field(default_factory=list)


class TrackingResult(BaseModel):
    """Email tracking information."""

    email_id: str = ""
    tracking_pixel_url: str = ""
    created_at: str = ""


class EmailStatus(BaseModel):
    """Current status of a sent email."""

    email_id: str = ""
    status: str = "unknown"
    sent_at: Optional[str] = None
    opened_at: Optional[str] = None
    clicked_at: Optional[str] = None
    replied_at: Optional[str] = None
    bounced: bool = False
    open_count: int = 0
    click_count: int = 0


# ---------------------------------------------------------------------------
# Disposable email domains and role-based prefixes
# ---------------------------------------------------------------------------

DISPOSABLE_DOMAINS = frozenset({
    "mailinator.com", "guerrillamail.com", "tempmail.com", "throwaway.email",
    "temp-mail.org", "10minutemail.com", "yopmail.com", "trashmail.com",
    "sharklasers.com", "guerrillamailblock.com", "grr.la", "dispostable.com",
    "maildrop.cc", "fakeinbox.com", "emailondeck.com",
})

ROLE_PREFIXES = frozenset({
    "info", "admin", "support", "sales", "contact", "help", "noreply",
    "no-reply", "postmaster", "webmaster", "abuse", "security", "billing",
    "hello", "team", "office", "hr", "careers", "marketing", "press",
})


@tool
def send_email(to: str, subject: str, body: str, from_email: str = "") -> str:
    """Send an email to a lead.

    Sends an email via SMTP with proper error handling, rate limiting,
    and tracking pixel injection. Records the email for status tracking.

    Args:
        to: Recipient email address.
        subject: Email subject line.
        body: Email body (plain text or HTML).
        from_email: Sender email address. Uses default from settings if empty.

    Returns:
        JSON string with send result including email_id and status.
    """
    logger.info("send_email called: to=%r subject=%r", to, subject[:50])
    settings = get_settings()

    result = EmailSendResult(
        email_id=str(uuid.uuid4()),
        to=to,
        subject=subject,
    )

    # Validate recipient
    if not _is_valid_email(to):
        result.status = "failed"
        result.error = f"Invalid email format: {to}"
        logger.warning("send_email rejected invalid address: %s", to)
        return result.model_dump_json(indent=2)

    # Rate limit check
    sender = from_email or settings.email.from_email
    today_key = f"{datetime.now(timezone.utc).date()}_{sender}"
    current_count = _daily_send_counts.get(today_key, 0)
    if current_count >= settings.email.daily_send_limit:
        result.status = "rate_limited"
        result.error = f"Daily send limit ({settings.email.daily_send_limit}) reached for {sender}"
        logger.warning("send_email rate limited: %s", result.error)
        return result.model_dump_json(indent=2)

    # Generate tracking
    tracking_id = str(uuid.uuid4())
    result.tracking_id = tracking_id

    # Inject tracking pixel if body is HTML or plain text
    tracking_domain = settings.email.tracking_domain or "track.smoothoperator.ai"
    tracking_pixel = (
        f'<img src="https://{tracking_domain}/open/{tracking_id}" '
        f'width="1" height="1" style="display:none" alt="" />'
    )

    # Build email message
    if "<html" in body.lower() or "<p>" in body.lower():
        html_body = body + tracking_pixel
        text_body = re.sub(r"<[^>]+>", "", body)
    else:
        text_body = body
        html_body = f"<html><body><p>{body.replace(chr(10), '<br/>')}</p>{tracking_pixel}</body></html>"

    try:
        msg = email.mime.multipart.MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{settings.email.from_name} <{sender}>" if settings.email.from_name else sender
        msg["To"] = to
        msg["X-SmoothOp-ID"] = result.email_id
        msg["X-SmoothOp-Track"] = tracking_id

        msg.attach(email.mime.text.MIMEText(text_body, "plain"))
        msg.attach(email.mime.text.MIMEText(html_body, "html"))

        # Send via SMTP
        if settings.email.smtp_host and settings.email.smtp_user:
            with smtplib.SMTP(settings.email.smtp_host, settings.email.smtp_port) as server:
                server.ehlo()
                if settings.email.smtp_port == 587:
                    server.starttls()
                    server.ehlo()
                server.login(
                    settings.email.smtp_user,
                    settings.email.smtp_password.get_secret_value(),
                )
                server.send_message(msg)
            result.status = "sent"
            result.sent_at = datetime.now(timezone.utc).isoformat()
            logger.info("Email sent successfully: id=%s to=%s", result.email_id, to)
        else:
            # Dry-run mode when SMTP not configured
            result.status = "dry_run"
            result.sent_at = datetime.now(timezone.utc).isoformat()
            logger.info("Email dry-run (SMTP not configured): id=%s to=%s", result.email_id, to)

        # Record in stores
        _email_store[result.email_id] = {
            "to": to,
            "subject": subject,
            "body": body,
            "from": sender,
            "status": result.status,
            "sent_at": result.sent_at,
            "tracking_id": tracking_id,
            "open_count": 0,
            "click_count": 0,
        }
        _tracking_store[tracking_id] = {
            "email_id": result.email_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "opens": [],
        }
        _daily_send_counts[today_key] = current_count + 1

    except smtplib.SMTPAuthenticationError as exc:
        result.status = "auth_failed"
        result.error = f"SMTP authentication failed: {exc}"
        logger.error("SMTP auth failed: %s", exc)
    except smtplib.SMTPRecipientsRefused as exc:
        result.status = "bounced"
        result.error = f"Recipient refused: {exc}"
        logger.error("Recipient refused: %s", exc)
    except Exception as exc:
        result.status = "failed"
        result.error = f"Send failed: {exc}"
        logger.error("send_email failed: %s", exc, exc_info=True)

    return result.model_dump_json(indent=2)


@tool
def check_email_deliverability(email_address: str) -> str:
    """Check the deliverability of an email address.

    Performs multiple validation checks including format validation,
    disposable email detection, role-based address detection, and
    MX record verification.

    Args:
        email_address: The email address to validate.

    Returns:
        JSON string with deliverability analysis results.
    """
    logger.info("check_email_deliverability called for %r", email_address)

    result = DeliverabilityResult(email=email_address)
    checks: List[str] = []

    # Check 1: Format validation
    result.is_valid_format = _is_valid_email(email_address)
    checks.append("format_validation")
    if not result.is_valid_format:
        result.deliverability_score = 0.0
        result.risk_level = "critical"
        result.checks_performed = checks
        return result.model_dump_json(indent=2)

    parts = email_address.split("@")
    local_part = parts[0].lower()
    domain = parts[1].lower()

    # Check 2: Disposable email detection
    result.is_disposable = domain in DISPOSABLE_DOMAINS
    checks.append("disposable_check")

    # Check 3: Role-based address detection
    result.is_role_based = local_part in ROLE_PREFIXES
    checks.append("role_based_check")

    # Check 4: MX record verification
    try:
        import dns.resolver

        answers = dns.resolver.resolve(domain, "MX")
        result.has_mx_record = len(answers) > 0
        checks.append("mx_record_check")
    except ImportError:
        logger.debug("dnspython not installed, skipping MX check")
        result.has_mx_record = True  # Assume valid if we can't check
        checks.append("mx_record_check_skipped")
    except Exception as exc:
        logger.debug("MX lookup failed for %s: %s", domain, exc)
        result.has_mx_record = False
        checks.append("mx_record_check")

    # Check 5: Domain age / reputation (heuristic)
    well_known_providers = {
        "gmail.com", "outlook.com", "hotmail.com", "yahoo.com",
        "icloud.com", "protonmail.com", "fastmail.com",
    }
    is_well_known = domain in well_known_providers
    checks.append("domain_reputation_check")

    # Calculate overall score
    score = 0.0
    if result.is_valid_format:
        score += 0.25
    if not result.is_disposable:
        score += 0.25
    if result.has_mx_record:
        score += 0.30
    if not result.is_role_based:
        score += 0.10
    if is_well_known or result.has_mx_record:
        score += 0.10

    result.deliverability_score = round(min(score, 1.0), 2)

    # Determine risk level
    if result.is_disposable:
        result.risk_level = "critical"
    elif not result.has_mx_record:
        result.risk_level = "high"
    elif result.is_role_based:
        result.risk_level = "medium"
    elif result.deliverability_score >= 0.8:
        result.risk_level = "low"
    else:
        result.risk_level = "medium"

    result.checks_performed = checks
    logger.info(
        "Deliverability check for %s: score=%.2f risk=%s",
        email_address, result.deliverability_score, result.risk_level,
    )
    return result.model_dump_json(indent=2)


@tool
def track_email_open(email_id: str) -> str:
    """Generate a tracking pixel URL for an email.

    Creates or retrieves the tracking pixel URL that can be embedded in
    email HTML to track opens.

    Args:
        email_id: The unique identifier of the sent email.

    Returns:
        JSON string with tracking pixel URL and metadata.
    """
    logger.info("track_email_open called for email_id=%r", email_id)
    settings = get_settings()

    email_record = _email_store.get(email_id)
    if not email_record:
        return json.dumps({"error": f"Email {email_id} not found"})

    tracking_id = email_record.get("tracking_id", str(uuid.uuid4()))
    tracking_domain = settings.email.tracking_domain or "track.smoothoperator.ai"

    result = TrackingResult(
        email_id=email_id,
        tracking_pixel_url=f"https://{tracking_domain}/open/{tracking_id}",
        created_at=datetime.now(timezone.utc).isoformat(),
    )

    return result.model_dump_json(indent=2)


@tool
def get_email_status(email_id: str) -> str:
    """Get the current status of a sent email.

    Retrieves comprehensive status information including delivery status,
    open tracking, click tracking, and reply detection.

    Args:
        email_id: The unique identifier of the email.

    Returns:
        JSON string with current email status and engagement metrics.
    """
    logger.info("get_email_status called for email_id=%r", email_id)

    email_record = _email_store.get(email_id)

    if not email_record:
        return EmailStatus(
            email_id=email_id,
            status="not_found",
        ).model_dump_json(indent=2)

    tracking_id = email_record.get("tracking_id")
    tracking_data = _tracking_store.get(tracking_id, {}) if tracking_id else {}

    opens = tracking_data.get("opens", [])

    status = EmailStatus(
        email_id=email_id,
        status=email_record.get("status", "unknown"),
        sent_at=email_record.get("sent_at"),
        opened_at=opens[0] if opens else None,
        open_count=len(opens),
        click_count=email_record.get("click_count", 0),
        bounced=email_record.get("status") == "bounced",
    )

    return status.model_dump_json(indent=2)


def record_email_open(tracking_id: str) -> None:
    """Record an email open event from a tracking pixel hit.

    Args:
        tracking_id: The tracking identifier from the pixel URL.
    """
    if tracking_id in _tracking_store:
        _tracking_store[tracking_id]["opens"].append(
            datetime.now(timezone.utc).isoformat()
        )
        email_id = _tracking_store[tracking_id].get("email_id")
        if email_id and email_id in _email_store:
            _email_store[email_id]["open_count"] = len(
                _tracking_store[tracking_id]["opens"]
            )
        logger.info("Recorded open for tracking_id=%s", tracking_id)


def _is_valid_email(addr: str) -> bool:
    """Validate email address format.

    Args:
        addr: Email address to validate.

    Returns:
        True if the format is valid.
    """
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, addr))
