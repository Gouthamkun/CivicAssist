import os
import logging
from typing import List, Dict, Any
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from backend.classifier.query_classifier import classify_query

logger = logging.getLogger("civicassist.retrieval")

# Map query types to metadata category values used in the knowledge base
CATEGORY_MAP = {
    "tax_notice": "TAX_NOTICES",
    "itr_filing": "CORE_FILING",
    "tax_forms": "STATEMENTS",
    "refund_status": "REFUNDS",
    "filing_deadlines": "REFUNDS",  # Deadlines file uses REFUNDS category
    "general": None,  # No filter for general queries
}

# Singleton for embeddings and vector DB to avoid reloading on every request
_embeddings = None
_vector_db = None

def _get_vector_db():
    """Lazy-load the vector database and embeddings model."""
    global _embeddings, _vector_db
    if _vector_db is None:
        _embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        persist_dir = os.path.join(os.path.dirname(__file__), "..", "..", "vector_db")
        _vector_db = Chroma(
            persist_directory=persist_dir,
            embedding_function=_embeddings,
        )
    return _vector_db


def retrieve(query: str, top_k: int = 3) -> Dict[str, Any]:
    """
    Full retrieval pipeline:
      1. Classify the query
      2. Apply metadata filter based on classification
      3. Run similarity search
      4. Return results with classification info
    """
    # Step 1: Classify
    classification = classify_query(query)
    query_type = classification["query_type"]
    logger.info(f"Query: '{query}' | Classification: {query_type}")

    # Step 2: Map to metadata filter
    category_value = CATEGORY_MAP.get(query_type)
    search_kwargs: Dict[str, Any] = {"k": top_k}
    if category_value:
        search_kwargs["filter"] = {"category": category_value}

    # Step 3: Vector similarity search
    db = _get_vector_db()
    try:
        results = db.similarity_search(query, **search_kwargs)
    except Exception:
        # If filtered search returns nothing, fall back to unfiltered
        logger.warning(f"Filtered search failed for category '{category_value}', falling back to unfiltered.")
        results = db.similarity_search(query, k=top_k)

    # If filtered search returned empty, retry without filter
    if not results and category_value:
        logger.info("No results with filter, retrying without metadata filter.")
        results = db.similarity_search(query, k=top_k)

    logger.info(f"Retrieved {len(results)} documents.")

    # Step 4: Package results
    documents = []
    for doc in results:
        documents.append({
            "content": doc.page_content,
            "source": doc.metadata.get("source", "unknown"),
            "category": doc.metadata.get("category", "N/A"),
            "page_id": doc.metadata.get("page_id", "N/A"),
        })

    return {
        "query": query,
        "query_type": query_type,
        "documents": documents,
    }
