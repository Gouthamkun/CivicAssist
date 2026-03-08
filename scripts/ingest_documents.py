import os
from langchain.document_loaders import TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.vectorstores import Chroma
from langchain.embeddings import OllamaEmbeddings

documents = []

# Load documents
for root, dirs, files in os.walk("knowledge_base"):
    for file in files:
        if file.endswith(".txt"):
            loader = TextLoader(os.path.join(root, file))
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
embeddings = OllamaEmbeddings(model="nomic-embed-text")

# Store in vector database
vector_db = Chroma.from_documents(
    chunks,
    embeddings,
    persist_directory="vector_db"
)

vector_db.persist()

print("Knowledge ingestion completed successfully.")