from retrieval.qdrant_store import QdrantStore
from retrieval.bm25_store import BM25Store


qdrant_store = QdrantStore()
bm25_store = BM25Store()

# TODO: Update BM25Store to pull from Qdrant/DB instead of local JSON files
def retrieval_agent(state):

    query = state["syllabus_topic"]

    dense_results = qdrant_store.search(query, top_k=5)
    sparse_results = bm25_store.search(query, top_k=5)

    merged = dense_results + sparse_results

    seen = set()
    unique = []

    for doc in merged:

        text = doc["text"]

        if text not in seen:
            unique.append(doc)
            seen.add(text)

    state["retrieved_chunks"] = [x["text"] for x in unique]
    state["retrieved_metadata"] = unique

    return state