from langgraph.graph import END, StateGraph

from agents.evaluator import evaluation_agent
from agents.latex_agent import latex_agent
from agents.planner import planner_agent
from agents.retriever import retrieval_agent
from agents.synthesizer import synthesis_agent
from state import GraphState

MAX_ITER = 3

builder = StateGraph(GraphState)

builder.add_node("planner", planner_agent)
builder.add_node("retriever", retrieval_agent)
builder.add_node("synthesizer", synthesis_agent)
builder.add_node("latex", latex_agent)
builder.add_node("evaluator", evaluation_agent)


builder.set_entry_point("planner")

builder.add_edge("planner", "retriever")
builder.add_edge("retriever", "synthesizer")
builder.add_edge("synthesizer", "latex")
builder.add_edge("latex", "evaluator")


def evaluation_router(state):
    score = state["evaluation_score"]
    iterations = state.get("evaluation_iterations", 0)

    if score >= 8.0 or iterations >= MAX_ITER:
        return END

    return "synthesizer"


builder.add_conditional_edges(
    "evaluator",
    evaluation_router,
    {
        END: END,
        "synthesizer": "synthesizer",
    },
)


graph = builder.compile()
