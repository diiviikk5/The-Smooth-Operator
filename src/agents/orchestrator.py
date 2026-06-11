import logging
from typing import Dict, Any, List, TypedDict, Optional
from src.config.settings import get_settings

logger = logging.getLogger(__name__)

class AgentState(TypedDict):
    lead_data: Dict[str, Any]
    enrichment_data: Dict[str, Any]
    score: float
    score_reasoning: str
    email_draft: str
    email_subject: str
    approval_status: str # approved, rejected, revision
    campaign_config: Dict[str, Any]
    retrieved_context: str
    agent_traces: List[Dict[str, Any]]
    error: Optional[str]
    current_step: str

class OutreachOrchestrator:
    \"\"\"LangGraph-based state machine orchestrator for the AI outreach workflow.\"\"\"

    def __init__(self):
        self.settings = get_settings()
        self.graph = None
        
        try:
            from langgraph.graph import StateGraph, END
            self.StateGraph = StateGraph
            self.END = END
            self._build_graph()
        except ImportError:
            logger.warning("langgraph not installed. Running OutreachOrchestrator in sequential mock mode.")

    def _build_graph(self):
        # We define a standard StateGraph
        workflow = self.StateGraph(AgentState)

        # Define nodes
        workflow.add_node("scrape", self._scrape_node)
        workflow.add_node("enrich", self._enrich_node)
        workflow.add_node("score", self._score_node)
        workflow.add_node("retrieve", self._retrieve_context_node)
        workflow.add_node("write", self._write_email_node)
        workflow.add_node("send", self._send_node)

        # Set entry point
        workflow.set_entry_point("scrape")

        # Add transitions
        workflow.add_conditional_edges(
            "score",
            self._route_score,
            {
                "continue": "retrieve",
                "skip": self.END
            }
        )
        workflow.add_edge("scrape", "enrich")
        workflow.add_edge("enrich", "score")
        workflow.add_edge("retrieve", "write")
        workflow.add_edge("write", "send")
        workflow.add_edge("send", self.END)

        self.graph = workflow.compile()

    def _scrape_node(self, state: AgentState) -> Dict[str, Any]:
        logger.info("Scraping node executed")
        return {"lead_data": {"name": "John Doe", "company": "Example Inc", "role": "CTO"}, "current_step": "enrich"}

    def _enrich_node(self, state: AgentState) -> Dict[str, Any]:
        logger.info("Enriching node executed")
        return {"enrichment_data": {"tech_stack": ["React", "AWS", "Python"], "pain_points": ["scalability"]}, "current_step": "score"}

    def _score_node(self, state: AgentState) -> Dict[str, Any]:
        logger.info("Scoring node executed")
        return {"score": 85.0, "score_reasoning": "High ICP alignment.", "current_step": "retrieve"}

    def _route_score(self, state: AgentState) -> str:
        score = state.get("score", 0.0)
        threshold = state.get("campaign_config", {}).get("min_score_threshold", 50.0)
        return "continue" if score >= threshold else "skip"

    def _retrieve_context_node(self, state: AgentState) -> Dict[str, Any]:
        logger.info("Retrieving RAG context node executed")
        return {"retrieved_context": "Found relevant cold outreach framework: PAS.", "current_step": "write"}

    def _write_email_node(self, state: AgentState) -> Dict[str, Any]:
        logger.info("Writing email node executed")
        return {
            "email_draft": "Hi John,\nWe saw Example Inc uses React and Python. We help solve scalability pain points...",
            "email_subject": "Scale Example Inc with AI",
            "current_step": "send"
        }

    def _send_node(self, state: AgentState) -> Dict[str, Any]:
        logger.info("Sending email node executed")
        return {"approval_status": "sent", "current_step": "end"}

    async def run(self, lead_url: str, campaign_config: Dict[str, Any]) -> Dict[str, Any]:
        \"\"\"Runs the orchestrator graph or sequential execution.\"\"\"
        initial_state = {
            "lead_data": {},
            "enrichment_data": {},
            "score": 0.0,
            "score_reasoning": "",
            "email_draft": "",
            "email_subject": "",
            "approval_status": "draft",
            "campaign_config": campaign_config,
            "retrieved_context": "",
            "agent_traces": [],
            "error": None,
            "current_step": "start"
        }

        if self.graph:
            # Run compiled StateGraph
            result = await self.graph.ainvoke(initial_state)
            return dict(result)
        else:
            # Sequential fallback simulation
            logger.info("Running sequential workflow fallback")
            s = initial_state
            s.update(self._scrape_node(s))
            s.update(self._enrich_node(s))
            s.update(self._score_node(s))
            if self._route_score(s) == "continue":
                s.update(self._retrieve_context_node(s))
                s.update(self._write_email_node(s))
                s.update(self._send_node(s))
            return s
