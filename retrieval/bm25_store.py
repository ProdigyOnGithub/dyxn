from rank_bm25 import BM25Okapi
import json


class BM25Store:

    def __init__(self, path="data/textbook_chunks.json"):

        with open(path, "r", encoding="utf-8") as f:
            self.docs = json.load(f)

        self.corpus = [x["text"].split() for x in self.docs]

        self.bm25 = BM25Okapi(self.corpus)

    def search(self, query, top_k=5):

        scores = self.bm25.get_scores(query.split())

        ranked = sorted(
            zip(scores, self.docs),
            key=lambda x: x[0],
            reverse=True
        )

        return [x[1] for x in ranked[:top_k]]