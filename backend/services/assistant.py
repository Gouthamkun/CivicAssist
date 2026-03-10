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

    context = "\\n".join([doc.page_content for doc in docs])

    import json
    import os
    
    # Dynamically scan for available physical forms in real-time
    available_forms_catalog = "No physical forms available."
    try:
        form_files = [f for f in os.listdir("frontend/forms") if f.endswith(".pdf")]
        if form_files:
            catalog_lines = [f"- {f.replace('.pdf','')} Form (URL: forms/{f})" for f in form_files]
            available_forms_catalog = "\\n".join(catalog_lines)
    except Exception:
        pass

    prompt = f"""
You are CivicAssist, an AI assistant that helps citizens understand Indian government services.

Context:
{context}

REAL-TIME AVAILABLE FORMS CATALOG:
{available_forms_catalog}

Question:
{question}

CRITICAL RAG INSTRUCTION:
1. ALWAYS prioritize the MODERN ONLINE PROCESS (e.g. UAN Member Portal) if it's available in the context (look for `SOURCE: official_modern_guide`). Do NOT describe older manual offline processes (like submitting physical forms to trusts or PF Offices) unless explicitly asked.
2. YOU MUST EVALUATE EVERY QUERY AGAINST THE REAL-TIME AVAILABLE FORMS CATALOG:
   - If the user's query involves a topic or workflow that matches a form listed in the catalog (e.g., PF Transfer, Withdrawal, Pension, LIC Policy), YOU MUST output its exact URL in `action_url` and set `action_label` to "Download [Form Name]". Do this even if the modern process is online.
   - If AND ONLY IF the query has absolutely nothing to do with any of the forms in the catalog, you MUST set `action_label` to exactly "Form is not required" and leave `action_url` as "".

Answer clearly and step-by-step based ONLY on the provided Context. 

CRITICAL INSTRUCTION: You MUST return your response ONLY as a valid JSON object. Do not include any other text outside the JSON.
The JSON must have the following structure:
{{
    "answer": "Your detailed step-by-step explanation here. YOU MUST use explicit escaped newline characters (\\\\n) to logically separate each step or bullet point instead of actual line breaks so the JSON does not crash.",
    "action_label": "Optional button text if a form is needed (e.g. 'Download Form 19'). If no form is needed, output exactly 'Form is not required'",
    "action_url": "Optional URL if a form is needed (e.g. 'forms/form19.pdf'). If no form is needed, output an empty string ''"
}}

If the user needs a specific form, provide the action_label and action_url. If no action is needed, set action_label to "Form is not required" and leave action_url empty.
"""

    response = ollama.chat(
        model="llama3",
        messages=[{"role":"user","content":prompt}]
    )

    try:
        import re
        content_str = response["message"]["content"]
        
        # Strip out code markdown blocks if the LLM adds them
        if content_str.startswith("```json"):
            content_str = content_str[7:-3]
        elif content_str.startswith("```"):
            content_str = content_str[3:-3]
            
        # Regex to find the first { and last } to handle chatty preambles "Here is the JSON: {}"
        json_match = re.search(r'\{.*\}', content_str.strip(), re.DOTALL)
        if json_match:
            content_str = json_match.group(0)
            
        parsed_response = json.loads(content_str, strict=False)
        return parsed_response
    except Exception as e:
        print(f"Failed to parse JSON: {e}")
        # Fallback if the LLM completely fails format
        return {
            "answer": response["message"]["content"],
            "action_label": "",
            "action_url": ""
        }