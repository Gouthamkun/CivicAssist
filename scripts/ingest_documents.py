import os
# Force CPU usage because the Ollama OOM crash deadlocked the CUDA driver state
os.environ["CUDA_VISIBLE_DEVICES"] = ""

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

print("Initializing Ingestion...")

documents = []

# Load documents manually
kb_dir = "knowledge_base"
for root, dirs, files in os.walk(kb_dir):
    for file in files:
        if file.endswith(".txt"):
            file_path = os.path.join(root, file)
            print(f"Loading: {file_path}")
            try:
                # Use explicit encoding to avoid Windows issues
                with open(file_path, 'r', encoding='utf-8') as f:
                    text = f.read()
                    documents.append(Document(page_content=text, metadata={"source": file_path}))
            except Exception as e:
                print(f"Error loading {file_path}: {e}")

print(f"Loaded {len(documents)} documents")

if not documents:
    print("No documents found to ingest.")
    exit()

# Split into chunks
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1500,
    chunk_overlap=200
)

chunks = text_splitter.split_documents(documents)
print(f"Created {len(chunks)} chunks")

# Create embeddings
print("Loading Embedding Model...")
# all-MiniLM-L6-v2 is small and usually fast
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

# Store in vector database
print("Updating Vector Database...")
vector_db = Chroma.from_documents(
    documents=chunks,
    embedding=embeddings,
    persist_directory="vector_db"
)

print("Knowledge ingestion completed successfully.")