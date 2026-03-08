from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import OllamaEmbeddings

embeddings = OllamaEmbeddings(model="nomic-embed-text")

db = Chroma(
    persist_directory="vector_db",
    embedding_function=embeddings
)

def retrieve_documents(query):
    docs = db.similarity_search(query, k=3)
    return docs