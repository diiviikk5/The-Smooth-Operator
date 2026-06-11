import logging
from typing import Dict, Any
from src.config.settings import get_settings

logger = logging.getLogger(__name__)

class MetricsCollector:
    \"\"\"Exposes prometheus metrics and collects API/retrieval counters and gauges.\"\"\"

    def __init__(self):
        self.settings = get_settings()
        self.prometheus = None
        
        try:
            import prometheus_client as pc
            self.prometheus = pc
            
            # Define metrics
            self.emails_generated = pc.Counter("emails_generated_total", "Total emails generated")
            self.emails_sent = pc.Counter("emails_sent_total", "Total emails sent")
            self.leads_scraped = pc.Counter("leads_scraped_total", "Total leads scraped")
            self.latency_seconds = pc.Histogram("request_latency_seconds", "Request latency in seconds", ["endpoint"])
            
            logger.info("Initialized Prometheus metrics collectors")
        except ImportError:
            logger.warning("prometheus_client not installed. Running in mock metrics collector mode.")

    def increment_emails_generated(self):
        if self.prometheus:
            self.emails_generated.inc()

    def increment_emails_sent(self):
        if self.prometheus:
            self.emails_sent.inc()

    def increment_leads_scraped(self):
        if self.prometheus:
            self.leads_scraped.inc()

    def record_latency(self, endpoint: str, duration: float):
        if self.prometheus:
            self.latency_seconds.labels(endpoint=endpoint).observe(duration)
