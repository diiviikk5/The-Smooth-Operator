import re

class EmailQualityMetric:
    \"\"\"Evaluates overall email parameters: readability, spam risks, and tone.\"\"\"

    def score(self, email_body: str) -> float:
        # 1. Readability check (Flesch readability score estimation based on sentence/word count)
        sentences = len(re.split(r'[.!?]+', email_body))
        words = len(email_body.split())
        
        avg_sentence_len = words / max(sentences, 1)
        readability_score = 1.0 if avg_sentence_len < 15 else (0.5 if avg_sentence_len < 25 else 0.2)

        # 2. Spam words check
        spam_keywords = ["free", "buy now", "click here", "guaranteed", "earn money", "risk free"]
        spam_count = sum(1 for kw in spam_keywords if kw in email_body.lower())
        spam_score = max(0.0, 1.0 - (spam_count * 0.2))

        # 3. Tone score (matches business professional)
        tone_score = 0.8
        if "please" in email_body.lower() or "thanks" in email_body.lower():
            tone_score = 1.0
            
        return (readability_score + spam_score + tone_score) / 3.0
