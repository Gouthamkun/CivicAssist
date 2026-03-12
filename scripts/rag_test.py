import os
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

def test_rag_retrieval():
    # Model and persist directory should match ingest_documents.py
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    persist_directory = "vector_db"
    
    if not os.path.exists(persist_directory):
        print(f"Error: Vector DB directory '{persist_directory}' not found.")
        return

    vector_db = Chroma(
        persist_directory=persist_directory,
        embedding_function=embeddings
    )

    test_queries = [
        "Which ITR form should I use for salary income and house property?",
        "What are the consequences of not verifying ITR within 30 days?",
        "What is a Section 143(1) intimation notice?",
        "How do I respond to a Section 139(9) defective return notice?",
        "What is the deadline for filing ITR for individual taxpayers for AY 2025-26?",
        "How can I track my income tax refund status?"
    ]

    print(f"\n{'='*60}\nINGESTED INCOME TAX RAG TEST\n{'='*60}")
    
    import sys
    # Ensure stdout handles UTF-8 for special characters like arrows
    sys.stdout.reconfigure(encoding='utf-8')

    for query in test_queries:
        print(f"\nQuery: {query}")
        results = vector_db.similarity_search(query, k=2)
        
        if not results:
            print("  Result: [NO MATCH FOUND]")
        else:
            for i, res in enumerate(results):
                source = res.metadata.get('source', 'Unknown')
                category = res.metadata.get('category', 'N/A')
                page_id = res.metadata.get('page_id', 'N/A')
                
                # Clean content for printing
                content_snippet = res.page_content[:200].replace('\n', ' ')
                print(f"  [{i+1}] Source: {os.path.basename(source)} (Category: {category}, ID: {page_id})")
                print(f"      Snippet: {content_snippet}...")
    
    print(f"\n{'='*60}\nVerification complete.")

if __name__ == "__main__":
    test_rag_retrieval()
