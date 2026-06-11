import logging
from typing import Dict, Any, Optional
from src.config.settings import get_settings

logger = logging.getLogger(__name__)

class TracingManager:
    \"\"\"Manages LLM and Agent tracing integrations (LangSmith, phoenix, basic log).\"\"\"

    def __init__(self):
        self.settings = get_settings()
        self.enable_tracing = self.settings.monitoring.enable_tracing

        if self.enable_tracing and self.settings.monitoring.langsmith_api_key:
            # LangSmith config set in environment variables is picked up automatically
            # by LangChain and LangGraph runtimes.
            logger.info("LangSmith tracing configuration detected and initialized")

    def log_run(self, name: str, run_type: str, inputs: Dict[str, Any], outputs: Dict[str, Any] = None, error: Optional[str] = None):
        \"\"\"Helper to write agent execution steps directly to logs if tracing is disabled.\"\"\"
        logger.info(
            f"Trace: {name} ({run_type})",
            inputs=inputs,
            outputs=outputs,
            error=error
        )
