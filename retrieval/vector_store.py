import json
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer


class VectorStore:

    def __init__(self, path="data/textbook_chunks.json"):
        self.model = SentenceTransformer("all-MiniLM-L6-v2")

        with open(path, "r", encoding="utf-8") as f:
            self.docs = json.load(f)

        self.texts = [x["text"] for x in self.docs]

        embeddings = self.model.encode(self.texts)
        self.embeddings = np.array(embeddings).astype("float32")

        self.index = faiss.IndexFlatL2(self.embeddings.shape[1])
        self.index.add(self.embeddings)

    def search(self, query, top_k=5):

        q_emb = self.model.encode([query]).astype("float32")

        distances, indices = self.index.search(q_emb, top_k)

        results = []

        for idx in indices[0]:
            results.append(self.docs[idx])

        return results