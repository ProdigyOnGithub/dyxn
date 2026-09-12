from typing import Any

from langgraph.graph import END, StateGraph

from agents.latex.evaluator import EvaluatorAgent
from agents.latex.latex_agent import LatexAgent
from agents.latex.planner import PlannerAgent
from agents.latex.retriever import RetrieverAgent
from agents.latex.state import GraphState
from agents.latex.synthesizer import SynthesizerAgent


class WorkflowOrchestrator:
    def __init__(
        self,
        planner: PlannerAgent,
        retriever: RetrieverAgent,
        synthesizer: SynthesizerAgent,
        latex_agent: LatexAgent,
        evaluator: EvaluatorAgent,
    ):
        self.planner = planner
        self.retriever = retriever
        self.synthesizer = synthesizer
        self.latex_agent = latex_agent
        self.evaluator = evaluator
        self.graph = self._build_graph()

    def _should_retry(self, state: GraphState) -> str:
        score = state.get("evaluation_score", 0.0)
        n = state.get("iteration_count", 0) + 1
        state["iteration_count"] = n
        if score >= 8.0 or n >= 3:
            return END
        return "synthesizer"

    def _build_graph(self):
        g = StateGraph(GraphState)
        g.add_node("planner", self.planner)
        g.add_node("retriever", self.retriever)
        g.add_node("synthesizer", self.synthesizer)
        g.add_node("latex_agent", self.latex_agent)
        g.add_node("evaluator", self.evaluator)

        g.set_entry_point("planner")
        g.add_edge("planner", "retriever")
        g.add_edge("retriever", "synthesizer")
        g.add_edge("synthesizer", "latex_agent")
        g.add_edge("latex_agent", "evaluator")
        g.add_conditional_edges("evaluator", self._should_retry)
        return g.compile()

    def run(self, initial_state: dict) -> Any:
        initial_state.setdefault("iteration_count", 0)
        return self.graph.invoke(initial_state)
