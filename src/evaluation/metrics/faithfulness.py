from typing import List, Dict, Any

class FaithfulnessMetric:
    \"\"\"Checks if email claims are supported by the retrieved RAG context.\"\"\"

    def score(self, email_body: str, retrieved_context: str) -> float:
        # Simplified token overlap / exact match heuristic
        # In production, we'd use NLI or LLM-as-a-judge
        if not retrieved_context:
            return 0.0
            
        claims = [c.strip() for c in email_body.split(".") if len(c.strip()) > 10]
        supported_claims = 0

        context_lower = retrieved_context.lower()
        for claim in claims:
            # check if major words in claim are in context
            words = [w.lower() for w in claim.split() if len(w) > 4]
            if words and all(w in context_lower for w in words[:3]):
                supported_claims += 1

        if not claims:
            return 1.0
        return supported_claims / len(claims)
