import json
import logging

import schemas

from core.llm import get_llm


logger = logging.getLogger(__name__)

llm = None

THRESHOLD = 8.0
FALLBACK_PASS_SCORE = THRESHOLD


def _get_evaluator_llm():
    global llm
    if llm is None:
        llm = get_llm()
    return llm


def _safe_error_message(exc: Exception) -> str:
    message = str(exc).strip() or type(exc).__name__
    return message.replace("\n", " ")[:500]


def _message_content(content):
    if hasattr(content, "content"):
        return _message_content(content.content)

    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict):
                parts.append(str(item.get("text") or item.get("content") or item))
            else:
                parts.append(str(item))
        return "\n".join(parts)

    return content


def _parse_json_object(text: str):
    cleaned = text.strip()

    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        decoder = json.JSONDecoder()
        for index, char in enumerate(cleaned):
            if char != "{":
                continue
            try:
                parsed, _ = decoder.raw_decode(cleaned[index:])
                return parsed
            except json.JSONDecodeError:
                continue
        raise


def _coerce_eval_output(content):
    content = _message_content(content)

    if hasattr(content, "model_dump"):
        parsed = content.model_dump()
    elif hasattr(content, "dict"):
        parsed = content.dict()
    elif isinstance(content, dict):
        parsed = content
    elif isinstance(content, str):
        parsed = _parse_json_object(content)
    else:
        raise TypeError(f"Unsupported evaluator response type: {type(content).__name__}")

    try:
        score = float(parsed.get("score", 5.0))
    except (TypeError, ValueError):
        score = 5.0

    score = max(0.0, min(10.0, score))

    feedback = parsed.get("feedback", [])
    if isinstance(feedback, str):
        feedback = [feedback]
    elif not isinstance(feedback, list):
        feedback = [str(feedback)]
    else:
        feedback = [str(item) for item in feedback]

    feedback = [item.strip() for item in feedback if item.strip()]
    if not feedback:
        feedback = ["No evaluator feedback returned."]

    return score, feedback


def _invoke_structured_evaluator(prompt: str):
    structured_llm = _get_evaluator_llm().with_structured_output(schemas.EvalOutput)
    return structured_llm.invoke(prompt)


def _invoke_json_evaluator(prompt: str):
    json_prompt = f"""{prompt}

Return only valid JSON. Do not wrap it in Markdown.
"""
    return _get_evaluator_llm().invoke(json_prompt)


def _evaluate_notes(prompt: str):
    try:
        return _coerce_eval_output(_invoke_structured_evaluator(prompt))
    except Exception as structured_exc:
        logger.warning(
            "Structured evaluator failed; falling back to plain JSON evaluator",
            exc_info=True,
        )

        try:
            return _coerce_eval_output(_invoke_json_evaluator(prompt))
        except Exception as json_exc:
            raise RuntimeError(
                "Structured evaluator failed: "
                f"{_safe_error_message(structured_exc)}; JSON evaluator failed: "
                f"{_safe_error_message(json_exc)}"
            ) from json_exc


def evaluation_agent(state):
    if state.get("generation_blocked"):
        state["evaluation_score"] = THRESHOLD
        state["evaluation_feedback"] = [
            state.get("blocked_reason")
            or "Generation was blocked because no source context was available."
        ]
        state["evaluation_iterations"] = state.get("evaluation_iterations", 0) + 1
        return state

    notes = state.get("latex_output", "")

    prompt = f"""
Evaluate the following educational notes.

Score from 0-10 for:
- correctness
- completeness
- educational clarity
- hallucination risk
- LaTeX formatting quality

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

    if not notes.strip():
        score = 0.0
        feedback = ["No LaTeX output was available for evaluation."]
    else:
        try:
            score, feedback = _evaluate_notes(prompt)
        except Exception as exc:
            logger.exception("Evaluator failed after all fallback paths")
            score = FALLBACK_PASS_SCORE
            feedback = [
                "Evaluator could not score this draft after structured and JSON fallback.",
                "Returning the current draft without evaluator-driven revision.",
                _safe_error_message(exc),
            ]

    state["evaluation_score"] = score
    state["evaluation_feedback"] = feedback
    state["evaluation_iterations"] = state.get("evaluation_iterations", 0) + 1

    return state
