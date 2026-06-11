from typing import Dict, Any

class HallucinationMetric:
    \"\"\"Measures the rate of fabricated facts about the lead in the email.\"\"\"

    def score(self, email_body: str, scraped_data: Dict[str, Any]) -> float:
        # Lower score is better (0 = no hallucinations, 1 = high hallucinations)
        # Check if the email references facts (e.g. tech, projects) not found in scraped data
        
        email_words = email_body.lower().split()
        
        # Look for hallucinated tech
        tech_words = ["kubernetes", "docker", "react", "angular", "vue", "django", "pytorch", "tensorflow"]
        scraped_text = str(scraped_data).lower()
        
        hallucinations = 0
        checks = 0
        
        for tech in tech_words:
            if tech in email_words:
                checks += 1
                if tech not in scraped_text:
                    hallucinations += 1
                    
        if checks == 0:
            return 0.0
            
        return hallucinations / checks
