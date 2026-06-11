from typing import List, Dict, Any

class AgentMetrics:
    \"\"\"Aggregates performance and execution statistics of agents.\"\"\"

    def aggregate(self, traces: List[Dict[str, Any]]) -> Dict[str, Any]:
        total_latency = 0.0
        total_cost = 0.0
        success_count = 0
        
        for trace in traces:
            total_latency += trace.get("latency_ms", 0.0)
            total_cost += trace.get("cost", 0.0)
            if trace.get("success", False):
                success_count += 1
                
        total_runs = len(traces)
        
        return {
            "total_runs": total_runs,
            "success_rate": success_count / max(total_runs, 1),
            "average_latency_ms": total_latency / max(total_runs, 1),
            "total_cost_usd": total_cost,
        }
