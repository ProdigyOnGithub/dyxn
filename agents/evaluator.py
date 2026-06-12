from langchain.chat_models import init_chat_model
import schemas
import json


llm = init_chat_model(
    model="gpt-4.1-mini",
    model_provider="openai"
)

THRESHOLD = 8.0

def evaluation_agent(state):

    notes = state["latex_output"]

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
    structured_llm = llm.with_structured_output(schemas.EvalOutput)
    content = structured_llm.invoke(prompt)

    try:
        parsed = json.loads(content)

        score = float(parsed.get("score", 5.0))

        feedback = parsed.get("feedback", [])

        if not isinstance(feedback, list):
            feedback = [str(feedback)]

    except Exception as e:

        score = 5.0

        feedback = [
            "Evaluator failed to return valid JSON.",
            str(e)
        ]

    state["evaluation_score"] = score
    state["evaluation_feedback"] = feedback

    return state