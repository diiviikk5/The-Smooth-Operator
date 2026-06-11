import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class ReplyAgent:
    \"\"\"Agent responsible for analyzing incoming replies and drafting contextual follow-ups.\"\"\"

    async def run(self, incoming_email_body: str, history_context: str) -> Dict[str, Any]:
        logger.info("Running ReplyAgent on incoming email response")
        
        # Classify intent
        text_lower = incoming_email_body.lower()
        if "remove" in text_lower or "unsubscribe" in text_lower or "stop" in text_lower:
            intent = "unsubscribe"
            reply_draft = "You have been successfully removed from our list. Have a great day."
        elif "interested" in text_lower or "sounds good" in text_lower or "meeting" in text_lower or "call" in text_lower:
            intent = "interested"
            reply_draft = (
                "Thanks for reaching out! Glad to hear you're interested. "
                "Here is my calendar link to book a quick slot: [Meeting Link]. Let me know if that works!"
            )
        else:
            intent = "objection"
            reply_draft = "Thanks for your response. Let me know if you change your mind, and we can connect then."

        return {
            "intent": intent,
            "reply_draft": reply_draft
        }
