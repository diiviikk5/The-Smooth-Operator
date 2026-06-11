import logging
from typing import Dict, Any
from src.db.models import TemplateFramework

logger = logging.getLogger(__name__)

class WriterAgent:
    \"\"\"Agent responsible for drafting hyper-personalized emails using frameworks like AIDA or PAS.\"\"\"

    async def run(self, enriched_lead: Dict[str, Any], context: str, framework: TemplateFramework = TemplateFramework.PAS) -> Dict[str, Any]:
        logger.info(f"Running WriterAgent using framework: {framework}")
        
        name = enriched_lead.get("name", "there")
        company = enriched_lead.get("company", "your company")
        pain_points = enriched_lead.get("pain_points", ["manual scalability bottlenecks"])
        primary_pain = pain_points[0] if pain_points else "operations scaling issues"

        subject = f"Fixing {primary_pain} at {company}"
        
        if framework == TemplateFramework.PAS:
            # Problem-Agitate-Solve
            body = (
                f"Hi {name},\\n\\n"
                f"It looks like many engineering teams face major challenges with {primary_pain}. "
                f"This often leads to missed deadlines and frustrated developers, slowing down product releases.\\n\\n"
                f"We help companies like yours solve this by automating dev workflows directly. "
                f"Would you be open to a quick 10-minute chat next week to see how we do it?\\n\\n"
                f"Best,\\nOutreach Team"
            )
        else:
            # Fallback simple template
            body = (
                f"Hi {name},\\n\\n"
                f"Hope all is well. I noticed {company} uses modern technologies and wanted to reach out. "
                f"We help teams solve core engineering pain points. Let me know if you are open to connect.\\n\\n"
                f"Best,\\nOutreach Team"
            )

        return {
            "subject": subject,
            "body": body,
            "variants": [
                {"subject": subject, "body": body, "variant": "A"},
                {"subject": f"Quick question about {primary_pain} at {company}", "body": body, "variant": "B"}
            ]
        }
