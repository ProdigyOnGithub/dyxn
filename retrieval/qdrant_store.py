from ingestion.embedding import embed_text
from db.qdrant import client
from core.config import config

class QdrantStore:
    def __init__(self):
        self.client = client

    def search(self, query: str, top_k: int = 5):
        """
        Embeds the query and searches both Textbook and Slides Qdrant collections.
        """
        q_emb = embed_text(query)
        
        results = []
        
        if config.TEXTBOOK_COLLECTION_NAME:
            try:
                tb_hits = self.client.search(
                    collection_name=config.TEXTBOOK_COLLECTION_NAME,
                    query_vector=q_emb,
                    limit=top_k
                )
                for hit in tb_hits:
                    results.append(hit.payload)
            except Exception as e:
                pass
                
        if config.SLIDES_COLLECTION_NAME:
            try:
                sl_hits = self.client.search(
                    collection_name=config.SLIDES_COLLECTION_NAME,
                    query_vector=q_emb,
                    limit=top_k
                )
                for hit in sl_hits:
                    results.append(hit.payload)
            except Exception as e:
                pass
                
        return results
