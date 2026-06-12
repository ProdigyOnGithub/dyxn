from langchain.chat_models import init_chat_model


llm = init_chat_model(
    model="gpt-4.1-mini",
    model_provider="openai"
)


def synthesis_agent(state):

    topic = state["syllabus_topic"]

    retrieved = "\n\n".join(state["retrieved_chunks"])

    working_notes = state["working_notes"]

    prompt = f"""
You are generating university-level notes.

TOPIC:
{topic}

PLANNER MEMORY:
{working_notes}

RETRIEVED CONTEXT:
{retrieved}

Generate:
- concise but detailed notes
- definitions
- formulas
- examples
- intuitive explanations
- theorem statements if relevant

Use educational structure.
Avoid hallucinations.
"""
    
    response = llm.invoke(prompt)

    state["synthesized_section"] = response.content

    return state