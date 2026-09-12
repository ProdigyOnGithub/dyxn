import json
from typing import Any, Dict

import api.schemas as schemas
from agents.base_agent import BaseAgent


class EvaluatorAgent(BaseAgent):
    def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        notes = state.get("latex_output", "")
        prompt = f"""
Evaluate the following educational notes.

Score from 0-10 for:
- correctness
- completeness
- educational clarity
- hallucination risk
- LaTeX formatting quality

Return ONLY valid JSON.

Required schema:

{{
  "score": float,
  "feedback": [
    "feedback item 1",
    "feedback item 2"
  ]
}}

NOTES:
{notes}
"""
        try:
            content = self.llm.with_structured_output(schemas.EvalOutput).invoke(prompt)
            if isinstance(content, str):
                parsed = json.loads(content)
                score = float(parsed.get("score", 5.0))
                feedback = parsed.get("feedback", [])
            else:
                score = float(content.score)
                feedback = content.feedback
            if not isinstance(feedback, list):
                feedback = [str(feedback)]
        except Exception as e:
            self.logger.error(f"Evaluation failed: {e}")
            score = 5.0
            feedback = ["Evaluator failed to return valid output.", str(e)]

        state["evaluation_score"] = score
        state["evaluation_feedback"] = feedback
        return state
