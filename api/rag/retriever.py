"""
Runtime document retrieval for RAG.

Implements hybrid search across documentation and case studies
with metadata filtering based on session context.
"""
from typing import List, Dict, Any, Optional
import chromadb

from api.config import settings
from api.models import SessionContext
from api.rag.embedder import get_embedding


class HybridRetriever:
    """Hybrid retriever for documentation and case studies."""

    def __init__(self):
        """Initialize retriever with ChromaDB client."""
        self.client = chromadb.PersistentClient(path=settings.chromadb_path)
        self._collections = {}

    def _get_collection(self, name: str):
        """Get collection with caching."""
        if name not in self._collections:
            try:
                self._collections[name] = self.client.get_collection(name)
            except Exception:
                return None
        return self._collections[name]

    async def retrieve(
        self,
        query: str,
        context: Optional[SessionContext] = None,
        n_docs: int = 3,
        n_cases: int = 2
    ) -> List[Dict[str, Any]]:
        """Retrieve relevant documents based on query and context.

        Args:
            query: User query text
            context: Optional session context (for filtering)
            n_docs: Number of documentation chunks to retrieve
            n_cases: Number of case studies to retrieve

        Returns:
            List of retrieved documents with text and metadata
        """
        results = []

        # Generate query embedding
        query_embedding = get_embedding(query)

        # 1. Search documentation (always)
        doc_results = self._search_collection(
            "documentation",
            query_embedding,
            n_results=n_docs
        )
        results.extend(doc_results)

        # 2. Search case studies (filtered by time horizon if available)
        if context and context.design_variables:
            time_horizon = context.design_variables.get("time_horizon", 2020)
        else:
            time_horizon = 2020

        case_results = self._search_collection(
            f"case_studies_{time_horizon}",
            query_embedding,
            n_results=n_cases
        )
        results.extend(case_results)

        return results

    def _search_collection(
        self,
        collection_name: str,
        query_embedding: List[float],
        n_results: int = 3,
        where: Optional[Dict] = None
    ) -> List[Dict[str, Any]]:
        """Search a single collection.

        Args:
            collection_name: Name of ChromaDB collection
            query_embedding: Query embedding vector
            n_results: Number of results to return
            where: Optional metadata filter

        Returns:
            List of matching documents
        """
        collection = self._get_collection(collection_name)
        if collection is None:
            return []

        try:
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=where
            )
        except Exception as e:
            print(f"Error querying {collection_name}: {e}")
            return []

        # Format results
        documents = []
        if results and results["documents"]:
            for i, doc in enumerate(results["documents"][0]):
                metadata = results["metadatas"][0][i] if results["metadatas"] else {}
                documents.append({
                    "text": doc,
                    "metadata": metadata,
                    "collection": collection_name,
                    "distance": results["distances"][0][i] if results.get("distances") else None
                })

        return documents

    def search_similar_buildings(
        self,
        query: str,
        time_horizon: int = 2020,
        n_results: int = 5
    ) -> List[Dict[str, Any]]:
        """Find similar building case studies.

        Args:
            query: Natural language description
            time_horizon: Climate scenario year
            n_results: Number of results

        Returns:
            List of similar building scenarios
        """
        query_embedding = get_embedding(query)
        return self._search_collection(
            f"case_studies_{time_horizon}",
            query_embedding,
            n_results=n_results
        )


# Global retriever instance
_retriever: Optional[HybridRetriever] = None


def get_retriever() -> HybridRetriever:
    """Get or create global retriever instance."""
    global _retriever
    if _retriever is None:
        _retriever = HybridRetriever()
    return _retriever


async def retrieve_documents(
    query: str,
    context: Optional[SessionContext] = None
) -> List[Dict[str, Any]]:
    """Convenience function for document retrieval.

    Args:
        query: User query
        context: Optional session context

    Returns:
        Retrieved documents
    """
    retriever = get_retriever()
    return await retriever.retrieve(query, context)
