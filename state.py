from typing import Dict, List, TypedDict


class GraphState(TypedDict):
    owner_id: int
    syllabus_topic: str
    document_statuses: List[Dict]
    chat_history: List[Dict]
    session_summary: str
    retrieved_chunks: List[str]
    retrieved_metadata: List[Dict]
    retrieval_ready: bool
    retrieval_warnings: List[str]
    generation_blocked: bool
    blocked_reason: str
    working_notes: str
    synthesized_section: str
    synthesized_latex: str
    latex_output: str
    evaluation_score: float
    evaluation_feedback: List[str]
    evaluation_iterations: int
