import sys
sys.stdout.reconfigure(encoding='utf-8')

from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

db = Chroma(
    persist_directory="vector_db",
    embedding_function=HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
)

data = db.get(include=["metadatas"])

cats = {}
ids = {}
sources = set()

for m in data["metadatas"]:
    c = m.get("category", "N/A")
    p = m.get("page_id", "N/A")
    s = m.get("source", "N/A")
    cats[c] = cats.get(c, 0) + 1
    ids[p] = ids.get(p, 0) + 1
    sources.add(s)

print(f"Total chunks in vector DB: {len(data['ids'])}")
print(f"\nChunks per Category:")
for k, v in sorted(cats.items()):
    print(f"  {k}: {v}")

print(f"\nChunks per Page ID:")
for k, v in sorted(ids.items()):
    print(f"  {k}: {v}")

print(f"\nIndexed source files ({len(sources)}):")
for s in sorted(sources):
    print(f"  {s}")
