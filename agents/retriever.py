from retrieval.qdrant_store import QdrantStore

qdrant_store = QdrantStore()

def retrieval_agent(state):

    query = state["syllabus_topic"]

    # Increased top_k to 10 to compensate for the removal of BM25
    results = qdrant_store.search(query, top_k=10)

    seen = set()
    unique = []

    for doc in results:

        text = doc["text"]

        if text not in seen:
            unique.append(doc)
            seen.add(text)

    state["retrieved_chunks"] = [x["text"] for x in unique]
    state["retrieved_metadata"] = unique

    return state