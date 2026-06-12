from langchain.chat_models import init_chat_model


llm = init_chat_model(
    model="gpt-4.1-mini",
    model_provider="openai"
)


def planner_agent(state):
    topic = state["syllabus_topic"]

    prompt = f"""
You are a curriculum planner.

For the syllabus topic:
{topic}

Determine:
1. prerequisite concepts
2. likely textbook sections
3. important formulas
4. subtopics to cover

Return a concise structured outline.
"""

    response = llm.invoke(prompt)

    state["working_notes"] = response.content

    return state