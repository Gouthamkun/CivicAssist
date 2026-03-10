import os
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

documents = []

# Load documents
for root, dirs, files in os.walk("knowledge_base"):
    for file in files:
        if file.endswith(".txt"):
            loader = TextLoader(os.path.join(root, file), encoding="utf-8")
            documents.extend(loader.load())

print(f"Loaded {len(documents)} documents")

# Split into chunks
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=400,
    chunk_overlap=50
)

chunks = text_splitter.split_documents(documents)

print(f"Created {len(chunks)} chunks")

# Create embeddings
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

# Store in vector database
vector_db = Chroma.from_documents(
    chunks,
    embeddings,
    persist_directory="vector_db"
)


print("Knowledge ingestion completed successfully.")