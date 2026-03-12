import os
import shutil
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

# Clear vector database if it exists to ensure fresh metadata
if os.path.exists("vector_db"):
    try:
        shutil.rmtree("vector_db")
        print("Cleared existing vector database.")
    except Exception as e:
        print(f"Warning: Could not clear vector_db: {e}. Proceeding with existing database.")

documents = []

# Load documents and extract metadata
# Only look at income_tax folder for now as per current focus
target_dir = os.path.join("knowledge_base", "income_tax")

for root, dirs, files in os.walk(target_dir):
    for file in files:
        if file.endswith(".txt"):
            file_path = os.path.join(root, file)
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            # Simple metadata extraction from headers
            metadata = {"source": file_path}
            for line in content.split("\n")[:15]: # Check first 15 lines
                if "**Category:**" in line:
                    metadata["category"] = line.split("**Category:**")[1].strip()
                if "**Page ID:**" in line:
                    metadata["page_id"] = line.split("**Page ID:**")[1].strip()
            
            # Ensure metadata stays as strings for Chroma
            metadata["category"] = metadata.get("category", "OTHER")
            metadata["page_id"] = metadata.get("page_id", "UNKNOWN")

            loader = TextLoader(file_path, encoding="utf-8")
            docs = loader.load()
            for doc in docs:
                doc.metadata.update(metadata)
            documents.extend(docs)

print(f"Loaded {len(documents)} documents with metadata")

# Split into chunks
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=500, # Increased chunk size slightly for better context
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