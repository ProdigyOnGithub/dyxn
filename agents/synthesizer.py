from core.llm import get_llm


llm = get_llm()


def synthesis_agent(state):

    topic = state["syllabus_topic"]

    retrieved = "\n\n".join(state["retrieved_chunks"])

    working_notes = state["working_notes"]

    chat_history = state.get("chat_history", [])
    session_summary = state.get("session_summary", "")

    history_block = ""
    if session_summary:
        history_block += f"\nPREVIOUS SESSION SUMMARY:\n{session_summary}\n"
    if chat_history:
        formatted = "\n".join([f'{m["role"]}: {m["content"]}' for m in chat_history])
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
    
    response = llm.invoke(prompt)

    state["synthesized_section"] = response.content

    return state