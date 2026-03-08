from backend.rag.retriever import retrieve_documents
from backend.models.llm import ask_llm


def civic_assist(question):

    docs = retrieve_documents(question)

    context = "\n".join([doc.page_content for doc in docs])

    prompt = f"""
    Use the following context to answer the citizen's question.

    Context:
    {context}

    Question:
    {question}

    Provide clear step-by-step guidance.
    """

    answer = ask_llm(prompt)

    return answer