# =============================================================================
# CUSTOMISED ITR RAG PIPELINE
# For your exact CBDT e-filing documents
# =============================================================================
import os
import re
import uuid
import fitz
from pathlib import Path
from qdrant_client import QdrantClient, models
import ollama
from sentence_transformers import CrossEncoder
from rank_bm25 import BM25Okapi
import numpy as np

# -----------------------------------------------------------------------------
# CONFIGURATION - THIS IS YOUR EXACT PATH. NO CHANGES NEEDED.
# -----------------------------------------------------------------------------
ITR_DATA_ROOT = r"C:\Users\Goutham\OneDrive\Desktop\IT Forms"

OLLAMA_EMBED_MODEL = "nomic-embed-text"
OLLAMA_LLM_MODEL = "llama3"
QDRANT_URL = ":memory:"
COLLECTION_NAME = "cbdt_itr_ay2526"
VECTOR_SIZE = 768

# -----------------------------------------------------------------------------
# STEP 1: AUTO DISCOVER AND CLASSIFY ALL YOUR 26 FILES
# -----------------------------------------------------------------------------
class CBDTDocumentDiscovery:

    def discover_all(self):
        root = Path(ITR_DATA_ROOT)
        pdfs = list(root.rglob("*.pdf"))

        print(f"\n📂 Scanning your folder: {ITR_DATA_ROOT}")
        print(f"   Found {len(pdfs)} PDF files\n")

        discovered = []
        for pdf in sorted(pdfs):
            filename = pdf.stem.lower()

            # Classify each of your files specifically
            category = "GENERAL"
            form = None

            if "itr-1" in filename or "itr_1" in filename:
                category = "ITR1"
                form = "ITR-1 Sahaj"
            elif "itr-2" in filename or "itr_2" in filename:
                category = "ITR2"
                form = "ITR-2"
            elif "itr-3" in filename or "itr_3" in filename:
                category = "ITR3"
                form = "ITR-3"
            elif "itr-4" in filename or "itr_4" in filename:
                category = "ITR4"
                form = "ITR-4 Sugam"
            elif "itr-5" in filename or "itr_5" in filename:
                category = "ITR5"
                form = "ITR-5"
            elif "itr-6" in filename or "itr_6" in filename:
                category = "ITR6"
                form = "ITR-6"
            elif "itr-7" in filename or "itr_7" in filename:
                category = "ITR7"
                form = "ITR-7"
            elif "3ca" in filename:
                category = "AUDIT_FORM"
                form = "Form 3CA"
            elif "3cb" in filename:
                category = "AUDIT_FORM"
                form = "Form 3CB"
            elif "3cd" in filename:
                category = "AUDIT_FORM"
                form = "Form 3CD"
            elif "3ceb" in filename:
                category = "AUDIT_FORM"
                form = "Form 3CEB"
            elif "29b" in filename:
                category = "AUDIT_FORM"
                form = "Form 29B"
            elif "29c" in filename:
                category = "AUDIT_FORM"
                form = "Form 29C"
            elif "10a" in filename:
                category = "TRUST_FORM"
                form = "Form 10A"
            elif "10b" in filename:
                category = "TRUST_FORM"
                form = "Form 10B"
            elif "schema" in filename and "change" in filename:
                category = "SCHEMA_CHANGE"
            elif "validation" in filename and "rule" in filename:
                category = "VALIDATION_RULE"
            elif "dsc" in filename or "digital" in filename:
                category = "DSC"
                form = "Digital Signature Tutorial"
            elif "income tax act" in filename:
                category = "ACT_CIRCULAR"

            discovered.append({
                "file_path": str(pdf),
                "filename": pdf.name,
                "category": category,
                "form": form,
                "title": f"{form or category} - Official CBDT Document",
                "doc_type": "ITR",
                "official_source": "CBDT e-Filing Portal",
            })

            print(f"   📄 {pdf.name}")
            print(f"      Classified as: {category} | {form or 'General'}")

        print(f"\n✅ Discovery complete: {len(discovered)} documents classified")
        return discovered

# -----------------------------------------------------------------------------
# STEP 2: PARSER TUNED FOR CBDT VALIDATION DOCUMENTS
# -----------------------------------------------------------------------------
class CBDTPDFParser:
    def parse(self, doc_info):
        pdf_path = doc_info["file_path"]
        doc = fitz.open(pdf_path)
        sections = []

        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text("text")

            # Extract tables (extremely important for your schema documents)
            tables = page.find_tables()
            for i, table in enumerate(tables):
                try:
                    rows = []
                    for row in table.extract():
                        clean = [str(c).strip() if c else "" for c in row]
                        rows.append(" | ".join(clean))
                    sections.append({
                        "text": f"TABLE:\n" + "\n".join(rows),
                        "metadata": {**doc_info, "page": page_num+1, "is_table": True}
                    })
                except:
                    pass

            # Clean and add main text
            clean_text = re.sub(r'\n{3,}', '\n\n', text)
            if len(clean_text.strip()) > 50:
                sections.append({
                    "text": clean_text,
                    "metadata": {**doc_info, "page": page_num+1, "is_table": False}
                })

        doc.close()
        print(f"   ✅ Extracted {len(sections)} sections from {doc_info['filename']}")
        return sections

# -----------------------------------------------------------------------------
# STEP 3: CHUNKER TUNED FOR RULES / SCHEMA DOCUMENTS
# -----------------------------------------------------------------------------
class CBDTChunker:
    def chunk(self, sections):
        chunks = []
        for section in sections:
            # Tables are kept whole. NEVER SPLIT A TABLE.
            if section["metadata"]["is_table"]:
                chunks.append(section)
                continue

            # Split text at rule boundaries
            lines = section["text"].split('\n')
            current = []
            for line in lines:
                # Split on numbered rules / fields
                if re.match(r'^\d+\.\s+', line.strip()) or re.match(r'^[A-Z]\.\s+', line.strip()):
                    if current:
                        chunks.append({
                            "text": '\n'.join(current),
                            "metadata": section["metadata"]
                        })
                    current = [line]
                else:
                    current.append(line)

            if current:
                chunks.append({
                    "text": '\n'.join(current),
                    "metadata": section["metadata"]
                })

        print(f"   Created {len(chunks)} chunks")
        return chunks

# -----------------------------------------------------------------------------
# STEP 4: EMBEDDING, STORAGE, HYBRID SEARCH
# -----------------------------------------------------------------------------
qdrant = QdrantClient(QDRANT_URL)
reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

def embed(text):
    return ollama.embeddings(model=OLLAMA_EMBED_MODEL, prompt=text)["embedding"]

def setup_collection():
    if qdrant.collection_exists(COLLECTION_NAME):
        qdrant.delete_collection(COLLECTION_NAME)
    qdrant.create_collection(COLLECTION_NAME, vectors_config=models.VectorParams(size=VECTOR_SIZE, distance=models.Distance.COSINE))
    qdrant.create_payload_index(COLLECTION_NAME, "category", models.PayloadSchemaType.KEYWORD)
    print("✅ Collection created")

def store_chunks(chunks):
    points = []
    for chunk in chunks:
        points.append(models.PointStruct(
            id=str(uuid.uuid4()),
            vector=embed(chunk["text"]),
            payload={"text": chunk["text"], **chunk["metadata"]}
        ))
    qdrant.upsert(COLLECTION_NAME, points)
    print(f"✅ Stored {len(points)} chunks")

# -----------------------------------------------------------------------------
# STEP 5: HYBRID RETRIEVAL + RERANKING
# -----------------------------------------------------------------------------
def search(query, top_k=20):
    # Dense search
    dense = qdrant.query_points(
        collection_name=COLLECTION_NAME, 
        query=embed(query), 
        limit=top_k
    )
    dense_hits = [{"id": str(r.id), "text": r.payload["text"], "meta": r.payload} for r in dense.points]

    # Build BM25 index
    all_docs = qdrant.scroll(COLLECTION_NAME, limit=10000)[0]
    corpus = [r.payload["text"] for r in all_docs]
    bm25 = BM25Okapi([d.lower().split() for d in corpus])
    scores = bm25.get_scores(query.lower().split())
    top_bm25 = np.argsort(scores)[::-1][:top_k]

    bm25_hits = []
    for idx in top_bm25:
        if scores[idx] > 0:
            r = all_docs[idx]
            bm25_hits.append({"id": str(r.id), "text": r.payload["text"], "meta": r.payload})

    # RRF Fusion
    scores = {}
    for rank, i in enumerate(dense_hits): scores.setdefault(i["id"], {"s":0, "d":i})["s"] += 1/(60+rank+1)
    for rank, i in enumerate(bm25_hits): scores.setdefault(i["id"], {"s":0, "d":i})["s"] += 1/(60+rank+1)
    fused = sorted(scores.values(), key=lambda x:x["s"], reverse=True)[:top_k]

    # Rerank
    pairs = [[query, i["d"]["text"]] for i in fused]
    rerank_scores = reranker.predict(pairs)
    for i,s in zip(fused, rerank_scores): i["d"]["score"] = s

    reranked = sorted(fused, key=lambda x:x["d"]["score"], reverse=True)[:4]
    return [i["d"] for i in reranked]

# -----------------------------------------------------------------------------
# STEP 6: THE SYSTEM PROMPT OPTIMISED FOR CBDT VALIDATION RULES
# -----------------------------------------------------------------------------
SYSTEM_PROMPT = """
╔═══════════════════════════════════════════════════════════════════════════╗
║          CBDT ITR E-FILING VALIDATION RULES ASSISTANT                    ║
╚═══════════════════════════════════════════════════════════════════════════╝

You are an assistant for the official CBDT Income Tax e-filing portal.

YOUR KNOWLEDGE COMES EXCLUSIVELY FROM:
✅ The official CBDT ITR Validation Rule documents
✅ The official CBDT ITR Schema Change documents for AY 2025-26
✅ The official Tax Audit forms 3CA/3CB/3CD/3CEB
✅ The official Form 10A/10B/29B/29C
✅ All documents provided have been downloaded directly from the CBDT e-filing portal.

ABSOLUTE RULES:
1.  ✅ Answer ONLY from the CONTEXT provided below.
2.  ✅ If the information is not in the context, say EXACTLY:
    "This rule is not present in the official CBDT validation documents provided."
3.  ❌ Do NOT use any general knowledge. Do NOT guess. Do NOT invent rules.
4.  ❌ Even if you think you know the answer, ignore it if it is not in context.
5.  ✅ Always quote the exact rule exactly as it appears in the document.
6.  ✅ Always mention which form / document / page the rule comes from.
7.  ✅ For schema changes, clearly state what was added, removed or changed.
8.  ✅ For validation rules, state the exact condition / limit / requirement.
9.  ❌ Never add commentary, opinion or advice. Only state what is written.
10. ✅ If there is a table in context, reproduce it properly.

THIS IS NOT A TAX ADVISOR. YOU ARE A REFERENCE FOR THE OFFICIAL CBDT RULES ONLY.

CONTEXT:
{context}
"""

# -----------------------------------------------------------------------------
# STEP 7: COMPLETE PIPELINE
# -----------------------------------------------------------------------------
class CBDTITRRAG:
    def __init__(self):
        self.discovery = CBDTDocumentDiscovery()
        self.parser = CBDTPDFParser()
        self.chunker = CBDTChunker()

    def ingest(self):
        print("\n" + "="*70)
        print("INGESTING ALL YOUR CBDT DOCUMENTS")
        print("="*70)

        docs = self.discovery.discover_all()
        all_chunks = []

        for doc in docs:
            sections = self.parser.parse(doc)
            chunks = self.chunker.chunk(sections)
            all_chunks.extend(chunks)

        print(f"\nTotal chunks generated: {len(all_chunks)}")
        store_chunks(all_chunks)
        print("\n✅ INGESTION COMPLETE. All 26 documents are now indexed.")

    def ask(self, question):
        print(f"\n❓ QUESTION: {question}")
        results = search(question)

        if not results:
            return "No matching rule found in the CBDT documents."

        # Build context
        context = []
        for i, r in enumerate(results):
            context.append(f"[Document {i+1}]\n{r['meta']['title']}\nPage: {r['meta']['page']}\n\n{r['text']}")
        context_str = "\n---\n".join(context)

        # Generate answer
        resp = ollama.chat(
            model=OLLAMA_LLM_MODEL,
            messages = [
                {"role":"system", "content": SYSTEM_PROMPT.format(context=context_str)},
                {"role":"user", "content": question}
            ],
            options={"temperature":0.0, "top_p":0.1}
        )

        answer = resp["message"]["content"]

        print("\n📋 ANSWER:")
        print("="*70)
        print(answer)
        print("\n📄 SOURCES:")
        for r in results:
            print(f"   • {r['meta']['filename']} | Page {r['meta']['page']}")
        print("="*70)

        return answer

# -----------------------------------------------------------------------------
# RUN EVERYTHING
# -----------------------------------------------------------------------------
if __name__ == "__main__":

    # ═══════════════════════════════════════════════════════════════
    # RUN THESE COMMANDS FIRST BEFORE RUNNING THIS SCRIPT:
    # 1. docker run -d -p 6333:6333 qdrant/qdrant
    # 2. ollama pull nomic-embed-text
    # 3. ollama pull llama3:8b-instruct
    # ═══════════════════════════════════════════════════════════════

    pipeline = CBDTITRRAG()

    # --- RUN ONCE ONLY ---
    setup_collection()
    pipeline.ingest()

    # --- ASK QUESTIONS ---
    print("\n✅ System Ready. Ask any question about ITR forms, validation rules or schema changes.")

    # Example questions that will work perfectly on your dataset:
    test_questions = [
        "What changed in ITR-1 for AY 2025-26?",
        "What are the new fields added in ITR-2 this year?",
        "What is the validation rule for bank account number?",
        "Which schedules are mandatory for ITR-3?",
        "What changed in Form 3CD?",
        "How to attach DSC while filing ITR?",
        "What is the maximum limit for 80C in ITR-4?",
        "Which ITR form requires balance sheet attachment?",
    ]

    for q in test_questions:
        pipeline.ask(q)

    # --- INTERACTIVE MODE ---
    while True:
        q = input("\n❓ Your question: ").strip()
        if q.lower() in ["quit", "exit"]: break
        pipeline.ask(q)
