import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

# Prefect decorators
def task(name=None):
    def decorator(func):
        return func
    return decorator

def flow(name=None):
    def decorator(func):
        return func
    return decorator

@task(name="get_campaign_leads")
def get_campaign_leads(campaign_id: str) -> List[Dict[str, Any]]:
    logger.info(f"Retrieving leads for campaign {campaign_id}")
    return [{"id": "1", "name": "Jane", "email": "jane@example.com", "company": "DevCorp"}]

@task(name="score_leads")
def score_leads(leads: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    logger.info("Scoring leads against ICP")
    for lead in leads:
        lead["score"] = 80.0
    return leads

@task(name="generate_outreach")
def generate_outreach(leads: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    logger.info("Drafting personalized emails")
    for lead in leads:
        lead["email_draft"] = f"Hi {lead['name']}, hope things are well at {lead['company']}..."
    return leads

@task(name="send_emails")
def send_emails(leads: List[Dict[str, Any]]):
    logger.info(f"Sending {len(leads)} emails")

@flow(name="campaign-execution")
def campaign_flow(campaign_id: str):
    leads = get_campaign_leads(campaign_id)
    scored = score_leads(leads)
    qualified = [l for l in scored if l["score"] >= 70.0]
    outreach = generate_outreach(qualified)
    send_emails(outreach)

if __name__ == "__main__":
    campaign_flow("campaign_123")
