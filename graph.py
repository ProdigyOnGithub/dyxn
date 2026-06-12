from langgraph.graph import StateGraph, END
from state import GraphState

from agents.planner import planner_agent
from agents.retriever import retrieval_agent
from agents.synthesizer import synthesis_agent
from agents.latex_agent import latex_agent
from agents.evaluator import evaluation_agent

MAX_ITER = 3
current_iter = 0

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

    if score >= 8.0 or current_iter >= MAX_ITER:
        return END
    current_iter += 1
    return "synthesizer"


builder.add_conditional_edges(
    "evaluator",
    evaluation_router,
    {
        END: END,
        "synthesizer": "synthesizer"
    }
)


graph = builder.compile()