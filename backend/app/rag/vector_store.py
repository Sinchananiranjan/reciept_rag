import os
from typing import List, Dict, Any, Optional
import chromadb
from app.config import settings
from app.rag.chunker import ReceiptChunk

class VectorStore:
    def __init__(self):
        self.client = chromadb.PersistentClient(path=settings.VECTOR_DB_DIR)
        self.collection = self.client.get_or_create_collection(name="receipt_chunks")

    def add_chunks(self, user_id: int, chunks: List[ReceiptChunk], embeddings: List[List[float]]):
        """Index chunks into vector store with strict user_id metadata."""
        if not chunks:
            return

        ids = [c.chunk_id for c in chunks]
        documents = [c.chunk_text for c in chunks]
        metadatas = []
        for c in chunks:
            meta = dict(c.metadata)
            meta["user_id"] = user_id  # Enforce user isolation
            metadatas.append(meta)

        self.collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas
        )

    def delete_receipt(self, user_id: int, receipt_id: int):
        """Delete all indexed chunks for a receipt belonging to user_id."""
        try:
            self.collection.delete(
                where={
                    "$and": [
                        {"user_id": {"$eq": user_id}},
                        {"receipt_id": {"$eq": receipt_id}}
                    ]
                }
            )
        except Exception:
            pass

    def search(
        self,
        user_id: int,
        query_embedding: List[float],
        top_k: int = 5,
        merchant_filter: Optional[str] = None,
        category_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Perform hybrid vector search strictly filtered by user_id and metadata."""
        where_conditions = [{"user_id": {"$eq": user_id}}]

        if merchant_filter:
            where_conditions.append({"merchant": {"$eq": merchant_filter.lower()}})

        if category_filter:
            where_conditions.append({"category": {"$eq": category_filter.lower()}})

        where_clause = {"$and": where_conditions} if len(where_conditions) > 1 else where_conditions[0]

        try:
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=where_clause
            )
        except Exception as e:
            print(f"Vector search exception: {str(e)}")
            return []

        retrieved = []
        if results and results.get("documents") and results["documents"][0]:
            docs = results["documents"][0]
            metas = results["metadatas"][0] if results.get("metadatas") else []
            dists = results["distances"][0] if results.get("distances") else []

            for i in range(len(docs)):
                retrieved.append({
                    "document": docs[i],
                    "metadata": metas[i] if i < len(metas) else {},
                    "distance": dists[i] if i < len(dists) else 0.0
                })

        return retrieved

vector_store = VectorStore()
