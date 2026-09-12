from typing import Any, Dict

from agents.base_agent import BaseAgent


class SynthesizerAgent(BaseAgent):
    def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        topic = state.get("syllabus_topic", "")
        retrieved = "\n\n".join(state.get("retrieved_chunks", []))
        working_notes = state.get("working_notes", "")
        chat_history = state.get("chat_history", [])
        session_summary = state.get("session_summary", "")

        history_block = ""
        if session_summary:
            history_block += f"\nPREVIOUS SESSION SUMMARY:\n{session_summary}\n"
        if chat_history:
            formatted = "\n".join(f'{m["role"]}: {m["content"]}' for m in chat_history)
            history_block += f"\nRECENT CONVERSATION:\n{formatted}\n"

        prompt = f"""
You are generating university-level notes.

TOPIC:
{topic}

PLANNER MEMORY:
{working_notes}

RETRIEVED CONTEXT:
{retrieved}
{history_block}
Generate:
- concise but detailed notes
- definitions
- formulas
- examples
- intuitive explanations
- theorem statements if relevant

Use educational structure.
Avoid hallucinations.
If there is prior conversation context, build on what was already discussed rather than repeating it.
"""
        state["synthesized_section"] = self.llm.invoke(prompt).content
        return state
