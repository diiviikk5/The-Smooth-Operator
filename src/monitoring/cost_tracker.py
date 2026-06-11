import logging

logger = logging.getLogger(__name__)

# Prices per 1M tokens as of 2026 estimation
MODEL_PRICING = {
    "gpt-4o": {"prompt": 5.0, "completion": 15.0},
    "gpt-4o-mini": {"prompt": 0.150, "completion": 0.600},
    "gemini-1.5-pro": {"prompt": 1.25, "completion": 5.00},
    "gemini-1.5-flash": {"prompt": 0.075, "completion": 0.300},
}

class CostTracker:
    \"\"\"Calculates and tracks token consumption costs for LLM invocations.\"\"\"

    def calculate_cost(self, model_name: str, prompt_tokens: int, completion_tokens: int) -> float:
        pricing = MODEL_PRICING.get(model_name, MODEL_PRICING["gpt-4o-mini"])
        
        prompt_cost = (prompt_tokens / 1_000_000) * pricing["prompt"]
        completion_cost = (completion_tokens / 1_000_000) * pricing["completion"]
        
        total_cost = prompt_cost + completion_cost
        
        logger.info(
            "model_call_cost",
            model_name=model_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost_usd=total_cost
        )
        return total_cost
