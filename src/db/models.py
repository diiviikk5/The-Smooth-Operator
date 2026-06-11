"""SQLAlchemy 2.0 async ORM models for The Smooth Operator.

All models inherit from ``Base`` which provides:
- ``id``: UUID primary key (server-generated)
- ``created_at``: Timestamp set on insert
- ``updated_at``: Timestamp updated on every modification

Relationships are defined with lazy="selectin" to avoid N+1 queries
in async contexts.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
)


# ── Enumerations ─────────────────────────────────────────────────────────────


class LeadStatus(str, enum.Enum):
    """Lifecycle status of a lead in the outreach pipeline."""

    NEW = "new"
    ENRICHED = "enriched"
    SCORED = "scored"
    CONTACTED = "contacted"
    REPLIED = "replied"
    CONVERTED = "converted"
    UNSUBSCRIBED = "unsubscribed"


class CampaignStatus(str, enum.Enum):
    """Lifecycle status of an outreach campaign."""

    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"


class EmailStatus(str, enum.Enum):
    """Delivery and engagement status of a single email."""

    DRAFT = "draft"
    QUEUED = "queued"
    SENT = "sent"
    OPENED = "opened"
    CLICKED = "clicked"
    REPLIED = "replied"
    BOUNCED = "bounced"
    SPAM = "spam"


class TemplateFramework(str, enum.Enum):
    """Copywriting framework used for email generation."""

    AIDA = "aida"
    PAS = "pas"
    BAB = "bab"
    CUSTOM = "custom"


# ── Base Model ───────────────────────────────────────────────────────────────


class Base(DeclarativeBase):
    """Abstract base for all ORM models.

    Provides a UUID primary key and automatic timestamp columns.
    All models should inherit from this class.
    """

    __abstract__ = True

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


# ── Domain Models ────────────────────────────────────────────────────────────


class Lead(Base):
    """A prospective contact for outreach.

    Stores both raw contact information and enrichment data gathered
    by the scraper/enrichment agents.  The ``score`` field is populated
    by the lead-scoring agent.

    Attributes:
        name: Full name of the lead.
        email: Primary email address (unique, indexed).
        company: Company or organization the lead belongs to.
        role: Job title / role.
        linkedin_url: LinkedIn profile URL.
        github_url: GitHub profile URL.
        website: Personal or company website.
        tech_stack: JSON list of technologies used by the lead's company.
        pain_points: JSON list of identified pain points.
        recent_activity: JSON list of recent posts, commits, talks, etc.
        enrichment_data: Free-form JSON blob with all enrichment data.
        score: ICP fit score (0.0–1.0).
        score_reasoning: Human-readable explanation of the score.
        status: Current pipeline status.
        emails: Related outreach emails.
    """

    __tablename__ = "leads"

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    email: Mapped[str] = mapped_column(
        String(320), nullable=False, unique=True, index=True
    )
    company: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[str | None] = mapped_column(String(255), nullable=True)
    linkedin_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    github_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    website: Mapped[str | None] = mapped_column(String(2048), nullable=True)

    tech_stack: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True, default=None
    )
    pain_points: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True, default=None
    )
    recent_activity: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True, default=None
    )
    enrichment_data: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True, default=None
    )

    score: Mapped[float | None] = mapped_column(Float, nullable=True, default=None)
    score_reasoning: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)

    status: Mapped[LeadStatus] = mapped_column(
        Enum(LeadStatus, name="lead_status", native_enum=False),
        nullable=False,
        default=LeadStatus.NEW,
        index=True,
    )

    # Relationships
    emails: Mapped[list[Email]] = relationship(
        "Email",
        back_populates="lead",
        lazy="selectin",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Lead(id={self.id!s:.8}, name={self.name!r}, status={self.status.value})>"


class Campaign(Base):
    """An outreach campaign targeting a specific ICP.

    Campaigns group emails and define the target audience,
    template, and sending settings.

    Attributes:
        name: Campaign name.
        description: Optional campaign description.
        target_icp: JSON definition of the Ideal Customer Profile.
        email_template_id: FK to the template used for email generation.
        status: Current campaign status.
        settings: JSON blob with sending schedules, limits, etc.
        emails: Related outreach emails.
    """

    __tablename__ = "campaigns"

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_icp: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True, default=None
    )
    email_template_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("email_templates.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[CampaignStatus] = mapped_column(
        Enum(CampaignStatus, name="campaign_status", native_enum=False),
        nullable=False,
        default=CampaignStatus.DRAFT,
        index=True,
    )
    settings: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True, default=None
    )

    # Relationships
    emails: Mapped[list[Email]] = relationship(
        "Email",
        back_populates="campaign",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    template: Mapped[EmailTemplate | None] = relationship(
        "EmailTemplate",
        back_populates="campaigns",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Campaign(id={self.id!s:.8}, name={self.name!r}, status={self.status.value})>"


class Email(Base):
    """A single outreach email sent to a lead within a campaign.

    Tracks the full lifecycle from draft through delivery and engagement.

    Attributes:
        lead_id: FK to the target lead.
        campaign_id: FK to the parent campaign.
        subject: Email subject line.
        body: Full email body (HTML or plain text).
        personalization_data: JSON with the data points used for personalization.
        status: Delivery / engagement status.
        sent_at: Timestamp when the email was actually sent.
        opened_at: Timestamp of first open (via tracking pixel).
        replied_at: Timestamp of first reply.
        follow_up_count: Number of follow-up emails in this thread.
        ab_variant: A/B test variant identifier (e.g. "A", "B").
        lead: Related lead.
        campaign: Related campaign.
        evaluation: Associated quality evaluation.
        traces: Agent traces for this email.
    """

    __tablename__ = "emails"

    lead_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("leads.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    campaign_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("campaigns.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    subject: Mapped[str] = mapped_column(String(998), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    personalization_data: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True, default=None
    )

    status: Mapped[EmailStatus] = mapped_column(
        Enum(EmailStatus, name="email_status", native_enum=False),
        nullable=False,
        default=EmailStatus.DRAFT,
        index=True,
    )

    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    opened_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    replied_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    follow_up_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ab_variant: Mapped[str | None] = mapped_column(String(10), nullable=True)

    # Relationships
    lead: Mapped[Lead] = relationship("Lead", back_populates="emails", lazy="selectin")
    campaign: Mapped[Campaign | None] = relationship(
        "Campaign", back_populates="emails", lazy="selectin"
    )
    evaluation: Mapped[EvaluationResult | None] = relationship(
        "EvaluationResult",
        back_populates="email",
        lazy="selectin",
        uselist=False,
        cascade="all, delete-orphan",
    )
    traces: Mapped[list[AgentTrace]] = relationship(
        "AgentTrace",
        back_populates="email",
        lazy="selectin",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"<Email(id={self.id!s:.8}, lead_id={self.lead_id!s:.8}, "
            f"status={self.status.value})>"
        )


class EmailTemplate(Base):
    """Reusable email template with Jinja2 variables.

    Templates define the structure and copywriting framework
    for generated emails.

    Attributes:
        name: Template name for identification.
        subject_template: Jinja2 template string for the subject line.
        body_template: Jinja2 template string for the email body.
        framework: Copywriting framework (AIDA, PAS, BAB, or custom).
        variables: JSON schema of required template variables.
        campaigns: Campaigns using this template.
    """

    __tablename__ = "email_templates"

    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    subject_template: Mapped[str] = mapped_column(Text, nullable=False)
    body_template: Mapped[str] = mapped_column(Text, nullable=False)
    framework: Mapped[TemplateFramework] = mapped_column(
        Enum(TemplateFramework, name="template_framework", native_enum=False),
        nullable=False,
        default=TemplateFramework.AIDA,
    )
    variables: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True, default=None
    )

    # Relationships
    campaigns: Mapped[list[Campaign]] = relationship(
        "Campaign",
        back_populates="template",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<EmailTemplate(id={self.id!s:.8}, name={self.name!r})>"


class EvaluationResult(Base):
    """Quality evaluation scores for a generated email.

    Produced by the LLM-as-judge evaluation pipeline, assessing
    multiple dimensions of email quality.

    Attributes:
        email_id: FK to the evaluated email.
        personalization_score: How well the email is personalized (0.0–1.0).
        faithfulness_score: Factual accuracy relative to lead data (0.0–1.0).
        hallucination_score: Degree of fabricated information (0.0–1.0, lower is better).
        spam_score: Likelihood of being flagged as spam (0.0–1.0, lower is better).
        tone_score: Appropriateness of tone (0.0–1.0).
        overall_score: Weighted composite score (0.0–1.0).
        judge_reasoning: Detailed text explanation from the LLM judge.
        metadata: Additional evaluation metadata.
        email: Related email.
    """

    __tablename__ = "evaluation_results"

    email_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("emails.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    personalization_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    faithfulness_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    hallucination_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    spam_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    tone_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    overall_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    judge_reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True, default=None
    )

    # Relationships
    email: Mapped[Email] = relationship(
        "Email", back_populates="evaluation", lazy="selectin"
    )

    def __repr__(self) -> str:
        return (
            f"<EvaluationResult(id={self.id!s:.8}, email_id={self.email_id!s:.8}, "
            f"overall={self.overall_score:.2f})>"
        )


class AgentTrace(Base):
    """Trace record for an individual agent action.

    Captures the input, output, cost, and performance of each
    step in the agent pipeline for observability and debugging.

    Attributes:
        email_id: FK to the email this trace relates to (optional).
        agent_name: Name of the agent that executed the action.
        action: Specific action performed (e.g. "research", "generate", "review").
        input_data: JSON input passed to the agent.
        output_data: JSON output produced by the agent.
        tokens_used: Total tokens consumed (prompt + completion).
        cost: Estimated cost in USD.
        latency_ms: Wall-clock latency in milliseconds.
        success: Whether the action completed successfully.
        error: Error message if the action failed.
        email: Related email (if applicable).
    """

    __tablename__ = "agent_traces"

    email_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("emails.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    agent_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    input_data: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True, default=None
    )
    output_data: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True, default=None
    )
    tokens_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cost: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    latency_ms: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    email: Mapped[Email | None] = relationship(
        "Email", back_populates="traces", lazy="selectin"
    )

    def __repr__(self) -> str:
        return (
            f"<AgentTrace(id={self.id!s:.8}, agent={self.agent_name!r}, "
            f"action={self.action!r}, success={self.success})>"
        )
