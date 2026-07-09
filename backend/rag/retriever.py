"""Retriever utility for ChromaDB.

Exposes functions to query the persisted vector database and return
relevance-ranked document context.
"""

import logging
import os
from typing import Any

import chromadb
from chromadb.utils import embedding_functions

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DB_DIR = os.getenv("CHROMA_DB_DIR", os.path.join(BASE_DIR, "data", "chroma_db"))
COLLECTION_NAME = "worldcup_kb"


class RAGRetriever:
    """Retriever class to query ChromaDB for stadium policies and FAQs."""

    def __init__(self, db_dir: str = DB_DIR):
        """Initialize ChromaDB client and load the embedding function model.

        Args:
            db_dir: Directory path of the persisted ChromaDB.
        """
        self.db_dir = db_dir
        self.client = chromadb.PersistentClient(path=self.db_dir)
        self.emb_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )
        self.collection = self.client.get_or_create_collection(
            name=COLLECTION_NAME, embedding_function=self.emb_fn
        )

    def retrieve(self, query: str, n_results: int = 3) -> list[dict[str, Any]]:
        """Retrieve top N matching documents for a query.

        Args:
            query: The user query string.
            n_results: Number of matching results to return.

        Returns:
            List[Dict[str, Any]]: List of matching sections, each containing
                                 "content", "source", "header", and "distance".
        """
        if not query or not query.strip():
            return []

        try:
            results = self.collection.query(query_texts=[query], n_results=n_results)

            formatted_results = []
            if not results or "documents" not in results or not results["documents"][0]:
                return []

            documents = results["documents"][0]
            metadatas = results["metadatas"][0]
            distances = (
                results["distances"][0]
                if "distances" in results
                else [0.0] * len(documents)
            )

            for i in range(len(documents)):
                formatted_results.append(
                    {
                        "content": documents[i],
                        "source": metadatas[i].get("source", "unknown"),
                        "header": metadatas[i].get("header", "unknown"),
                        "distance": distances[i],
                    }
                )

            return formatted_results

        except Exception as e:
            logger.error("Error querying ChromaDB: %s", e, exc_info=True)
            return []


# Global helper instance
_retriever = None


def get_retriever() -> RAGRetriever:
    """Get or instantiate the global RAGRetriever.

    Returns:
        RAGRetriever: Global retriever instance.
    """
    global _retriever
    if _retriever is None:
        _retriever = RAGRetriever()
    return _retriever


def retrieve_context(query: str, n_results: int = 3) -> list[dict[str, Any]]:
    """Convenience function to retrieve context for a query.

    Args:
        query: User question query.
        n_results: Number of results.

    Returns:
        List[Dict[str, Any]]: Retrieved context documents.
    """
    return get_retriever().retrieve(query, n_results=n_results)
