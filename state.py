from typing import TypedDict, List, Dict


class GraphState(TypedDict):
    syllabus_topic: str
    retrieved_chunks: List[str]
    retrieved_metadata: List[Dict]
    working_notes: str
    synthesized_section: str
    synthesized_latex: str
    latex_output: str
    evaluation_score: float
    evaluation_feedback: List[str]