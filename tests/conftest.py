import pytest
from src.config.settings import Settings
from src.db.models import Lead, Campaign, Email, TemplateFramework, CampaignStatus

@pytest.fixture
def mock_settings():
    return Settings()

@pytest.fixture
def sample_lead():
    return Lead(
        name="Jane Doe",
        email="jane@example.com",
        company="TechCorp",
        role="VP of Engineering",
        linkedin_url="https://linkedin.com/in/janedoe",
        github_url="https://github.com/janedoe",
        website="https://techcorp.com",
    )

@pytest.fixture
def sample_campaign():
    return Campaign(
        name="TechCorp Outreach",
        description="Outreach campaign targeting TechCorp VP of Engineering",
        target_icp={"preferred_technologies": ["React", "Go"]},
        status=CampaignStatus.DRAFT,
    )
