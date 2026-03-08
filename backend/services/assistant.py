import ollama
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings

embedding = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

db = Chroma(
    persist_directory="vector_db",
    embedding_function=embedding
)

retriever = db.as_retriever(search_kwargs={"k":3})


def civic_assist(question):

    docs = retriever.invoke(question)

    context = "\n".join([doc.page_content for doc in docs])

    prompt = f"""
You are CivicAssist, an AI assistant that helps citizens understand Indian government services.

Context:
{context}

Question:
{question}

Answer clearly and step-by-step.
"""

    response = ollama.chat(
        model="llama3",
        messages=[{"role":"user","content":prompt}]
    )

    return response["message"]["content"]