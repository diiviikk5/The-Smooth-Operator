from typing import Dict, Any

class PersonalizationMetric:
    \"\"\"Evaluates how personalized an email is to the target lead.\"\"\"

    def score(self, email_body: str, lead_data: Dict[str, Any]) -> float:
        name = lead_data.get("name", "").lower()
        company = lead_data.get("company", "").lower()
        role = lead_data.get("role", "").lower()

        points = 0
        max_points = 3

        body_lower = email_body.lower()

        if name and name in body_lower:
            points += 1
        if company and company in body_lower:
            points += 1
        if role and role in body_lower:
            points += 1

        return points / max_points
