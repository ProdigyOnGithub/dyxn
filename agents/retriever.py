from retrieval.vector_store import VectorStore
from retrieval.bm25_store import BM25Store


vector_store = VectorStore()
bm25_store = BM25Store()

# Will write Retrieval using Postgres
def retrieval_agent(state):

    query = state["syllabus_topic"]

    dense_results = vector_store.search(query, top_k=5)
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