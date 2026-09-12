from typing import Any, Dict

from agents.base_agent import BaseAgent


class PlannerAgent(BaseAgent):
    def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        topic = state.get("syllabus_topic", "")
        chat_history = state.get("chat_history", [])
        session_summary = state.get("session_summary", "")

        history_block = ""
        if session_summary:
            history_block += f"\nPREVIOUS SESSION SUMMARY:\n{session_summary}\n"
        if chat_history:
            formatted = "\n".join(f'{m["role"]}: {m["content"]}' for m in chat_history)
            history_block += f"\nRECENT CONVERSATION:\n{formatted}\n"

        prompt = f"""
You are a curriculum planner.
{history_block}
For the syllabus topic:
{topic}

Determine:
1. prerequisite concepts
2. likely textbook sections
3. important formulas
4. subtopics to cover

If there is prior conversation context, use it to avoid repeating what was already covered and build on the user's learning progression.

Return a concise structured outline.
"""
        state["working_notes"] = self.llm.invoke(prompt).content
        return state
