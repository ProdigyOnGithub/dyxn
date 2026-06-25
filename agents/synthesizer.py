from core.llm import get_llm


llm = None


def _get_synthesis_llm():
    global llm
    if llm is None:
        llm = get_llm()
    return llm


PROCESSING_STATUSES = {"queued", "chunking", "chunked", "embedding"}


def _processing_documents(document_statuses):
    return [
        document
        for document in document_statuses
        if document.get("status") in PROCESSING_STATUSES
    ]


def _format_processing_status(document_statuses):
    lines = []
    for document in document_statuses:
        filename = document.get("filename", document.get("document_id", "document"))
        status = document.get("status", "unknown")
        embedded = int(document.get("embedded_chunks") or 0)
        total = int(document.get("total_chunks") or 0)

        if total:
            lines.append(f"- {filename}: {status}, {embedded}/{total} chunks embedded")
        else:
            lines.append(f"- {filename}: {status}")

    return "\n".join(lines)


def synthesis_agent(state):
    topic = state["syllabus_topic"]
    document_statuses = state.get("document_statuses", [])

    if state.get("generation_blocked") or not state.get("retrieved_chunks"):
        warnings = state.get("retrieval_warnings", [])
        processing_documents = _processing_documents(document_statuses)
        details = _format_processing_status(processing_documents)
        if not details:
            details = "\n".join([f"- {warning}" for warning in warnings])
        blocked_reason = state.get("blocked_reason") or "No source context was available."

        state["synthesized_section"] = f"""\\section{{Source material is not ready}}

DYXN cannot answer from the uploaded document yet because {blocked_reason}

Current processing status:
{details}

Ask again once indexing has produced searchable chunks.
"""
        state["generation_blocked"] = True
        return state

    retrieved = "\n\n".join(state["retrieved_chunks"])

    working_notes = state["working_notes"]

    chat_history = state.get("chat_history", [])
    session_summary = state.get("session_summary", "")
    evaluation_feedback = state.get("evaluation_feedback", [])
    evaluation_iterations = state.get("evaluation_iterations", 0)
    retrieval_warnings = state.get("retrieval_warnings", [])

    history_block = ""
    if session_summary:
        history_block += f"\nPREVIOUS SESSION SUMMARY:\n{session_summary}\n"
    if chat_history:
        formatted = "\n".join([f'{m["role"]}: {m["content"]}' for m in chat_history])
        history_block += f"\nRECENT CONVERSATION:\n{formatted}\n"

    revision_block = ""
    if evaluation_iterations > 0 and evaluation_feedback:
        feedback = "\n".join([f"- {item}" for item in evaluation_feedback])
        revision_block = f"""
REVISION CONTEXT:
This is revision attempt {evaluation_iterations + 1}. The evaluator rejected the previous draft with this feedback:
{feedback}

Revise the notes directly in response to that feedback. Preserve correct material, fix weak or incorrect parts, and improve clarity/completeness.
"""

    status_block = ""
    if retrieval_warnings:
        warnings = "\n".join([f"- {warning}" for warning in retrieval_warnings])
        status_block = f"""
DOCUMENT PROCESSING STATUS:
{warnings}

If any document is still processing, answer only from the retrieved chunks that are already available and clearly mention that the answer may be incomplete until processing finishes.
"""

    prompt = f"""
You are generating university-level notes strictly from retrieved source material.

Hard rule:
- Use only the retrieved context below.
- If the retrieved context is insufficient, say exactly what is missing instead of inventing content.
- Conversation history is only for understanding the user's request. Do not treat prior chat messages or summaries as source material.

TOPIC:
{topic}

PLANNER MEMORY:
{working_notes}

RETRIEVED CONTEXT:
{retrieved}
{history_block}
{revision_block}
{status_block}
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

    response = _get_synthesis_llm().invoke(prompt)

    state["synthesized_section"] = response.content

    return state
