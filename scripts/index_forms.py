import os
import sys
import json
import fitz  # PyMuPDF
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

# Add project root to path to import assistant config if needed
sys.path.append(os.getcwd())

# Configuration
VECTOR_DB_DIR = "vector_db"
FORMS_DIRS = [
    r"C:\Users\Goutham\OneDrive\Desktop\IT Forms",
    r"C:\Users\Goutham\OneDrive\Desktop\IT Forms\forms"
]

def extract_text_from_pdf(pdf_path):
    print(f"Extracting: {pdf_path}")
    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        text += page.get_text()
    return text

def index_forms():
    # 1. Initialize Embeddings and Vector DB
    embedding_model = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    db = Chroma(persist_directory=VECTOR_DB_DIR, embedding_function=embedding_model)
    
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    all_documents = []

    # 2. Iterate through directories and extract text
    for directory in FORMS_DIRS:
        if not os.path.exists(directory):
            print(f"Warning: Directory {directory} not found.")
            continue
            
        for file in os.listdir(directory):
            if file.lower().endswith(".pdf"):
                file_path = os.path.join(directory, file)
                try:
                    text = extract_text_from_pdf(file_path)
                    if not text.strip():
                        print(f"Skipping empty file: {file}")
                        continue
                        
                    chunks = splitter.split_text(text)
                    for i, chunk in enumerate(chunks):
                        all_documents.append(Document(
                            page_content=chunk,
                            metadata={"source": file, "chunk": i, "path": file_path}
                        ))
                except Exception as e:
                    print(f"Error processing {file}: {e}")

    # 3. Add to Vector DB in batches
    if all_documents:
        batch_size = 1000
        print(f"Adding {len(all_documents)} chunks to the vector database in batches of {batch_size}...")
        for i in range(0, len(all_documents), batch_size):
            batch = all_documents[i : i + batch_size]
            print(f"Adding batch {i//batch_size + 1}/{(len(all_documents)-1)//batch_size + 1}...")
            db.add_documents(batch)
        print("Indexing complete!")
    else:
        print("No new documents found to index.")

if __name__ == "__main__":
    index_forms()
