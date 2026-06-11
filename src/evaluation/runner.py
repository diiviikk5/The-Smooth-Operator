import logging
from typing import List, Dict, Any
from src.evaluation.metrics.personalization import PersonalizationMetric
from src.evaluation.metrics.faithfulness import FaithfulnessMetric
from src.evaluation.metrics.hallucination import HallucinationMetric
from src.evaluation.metrics.email_quality import EmailQualityMetric
from src.evaluation.judges.llm_judge import LLMJudge

logger = logging.getLogger(__name__)

class EvaluationRunner:
    \"\"\"Runs evaluation test cases through metrics and judges to compile comparison reports.\"\"\"

    def __init__(self):
        self.personalization_metric = PersonalizationMetric()
        self.faithfulness_metric = FaithfulnessMetric()
        self.hallucination_metric = HallucinationMetric()
        self.email_quality_metric = EmailQualityMetric()
        self.llm_judge = LLMJudge()

    async def run_test_case(self, email_body: str, lead_data: Dict[str, Any], context: str) -> Dict[str, Any]:
        logger.info(f"Evaluating test case for lead: {lead_data.get('email')}")
        
        p_score = self.personalization_metric.score(email_body, lead_data)
        f_score = self.faithfulness_metric.score(email_body, context)
        h_score = self.hallucination_metric.score(email_body, lead_data)
        q_score = self.email_quality_metric.score(email_body)
        
        judge_results = await self.llm_judge.evaluate(email_body, lead_data)
        
        return {
            "personalization_score": p_score,
            "faithfulness_score": f_score,
            "hallucination_score": h_score,
            "quality_score": q_score,
            "judge_overall_score": judge_results["overall_score"],
            "judge_reasoning": judge_results["reasoning"],
        }

    async def run_suite(self, test_cases: List[Dict[str, Any]]) -> Dict[str, Any]:
        results = []
        for case in test_cases:
            res = await self.run_test_case(
                email_body=case["email_body"],
                lead_data=case["lead_data"],
                context=case["context"]
            )
            results.append(res)
            
        # Calculate aggregates
        count = len(results)
        if count == 0:
            return {"cases_run": 0}
            
        avg_personalization = sum(r["personalization_score"] for r in results) / count
        avg_faithfulness = sum(r["faithfulness_score"] for r in results) / count
        avg_hallucination = sum(r["hallucination_score"] for r in results) / count
        avg_quality = sum(r["quality_score"] for r in results) / count
        avg_judge = sum(r["judge_overall_score"] for r in results) / count
        
        return {
            "cases_run": count,
            "averages": {
                "personalization_score": avg_personalization,
                "faithfulness_score": avg_faithfulness,
                "hallucination_score": avg_hallucination,
                "quality_score": avg_quality,
                "judge_overall_score": avg_judge,
            },
            "results": results
        }
