import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class ScorerAgent:
    \"\"\"Agent that evaluates enriched lead data against Ideal Customer Profile (ICP) criteria.\"\"\"

    async def run(self, enriched_lead: Dict[str, Any], target_icp: Dict[str, Any]) -> Dict[str, Any]:
        logger.info(f"Running ScorerAgent on company: {enriched_lead.get('company')}")
        
        # Simple scoring algorithm based on keyword match
        score = 50.0
        reasons = []
        
        # Check tech stack alignment
        icp_tech = target_icp.get("preferred_technologies", [])
        lead_tech = enriched_lead.get("tech_stack", [])
        matched_tech = [t for t in lead_tech if t in icp_tech]
        if matched_tech:
            score += len(matched_tech) * 10.0
            reasons.append(f"Matched tech stack: {', '.join(matched_tech)}")

        # Check role alignment
        icp_roles = target_icp.get("target_roles", [])
        lead_role = enriched_lead.get("role", "").lower()
        if any(r.lower() in lead_role for r in icp_roles):
            score += 20.0
            reasons.append(f"Matched target role: {lead_role}")
            
        score = min(score, 100.0)
        
        return {
            "score": score,
            "score_reasoning": " | ".join(reasons) if reasons else "Generic match, low alignment indicators."
        }
