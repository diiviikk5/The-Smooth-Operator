import re
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class GuardrailsManager:
    \"\"\"Performs compliance and safety checks (PII detection, tone/profanity, blocklists).\"\"\"

    def __init__(self, blocklist: List[str] = None):
        self.blocklist = blocklist or []

    def validate_generation(self, text: str, lead_email: str) -> Dict[str, Any]:
        \"\"\"Runs all safety checks on generated email text.\"\"\"
        errors = []

        # 1. Blocklist check
        domain = lead_email.split("@")[-1] if "@" in lead_email else ""
        if lead_email in self.blocklist or domain in self.blocklist:
            errors.append("recipient_on_blocklist")

        # 2. PII check
        ssn_pattern = r"\b\d{3}-\d{2}-\d{4}\b"
        if re.search(ssn_pattern, text):
            errors.append("pii_detected_ssn")

        # 3. Profanity/Tone check
        offensive_words = ["spam", "click here immediately", "make money quick", "guarantee success"]
        matched_words = [w for w in offensive_words if w in text.lower()]
        if matched_words:
            errors.append(f"banned_phrases_detected: {matched_words}")

        passed = len(errors) == 0
        
        return {
            "passed": passed,
            "errors": errors,
            "action": "allow" if passed else "block"
        }
