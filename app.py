import logging
from pathlib import Path

from graph import graph


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
OUTPUT_DIR = Path("outputs")

initial_state = {
    "owner_id": 0,
    "syllabus_topic": "Fourier Transform",
    "document_statuses": [],
    "chat_history": [],
    "session_summary": "",
    "retrieved_chunks": [],
    "retrieved_metadata": [],
    "retrieval_ready": False,
    "retrieval_warnings": [],
    "generation_blocked": False,
    "blocked_reason": "",
    "working_notes": "",
    "synthesized_section": "",
    "latex_output": "",
    "evaluation_score": 0.0,
    "evaluation_feedback": [],
    "evaluation_iterations": 0,
}


result = graph.invoke(initial_state)

OUTPUT_DIR.mkdir(exist_ok=True)
with open(OUTPUT_DIR / "notes.tex", "w", encoding="utf-8") as f:
    f.write(result["latex_output"])

logger.info("LaTeX notes generated path=%s", OUTPUT_DIR / "notes.tex")
logger.info("Evaluation score=%s", result["evaluation_score"])
