import ollama
import os
import json

# Force CPU usage because the Ollama OOM crash deadlocked the CUDA driver state
os.environ["CUDA_VISIBLE_DEVICES"] = ""

from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings

embedding = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

db = Chroma(
    persist_directory="vector_db",
    embedding_function=embedding
)

retriever = db.as_retriever(search_kwargs={"k":3})



def retrieve_knowledge(query: str):
    """Reusable vector DB retriever for all endpoints."""
    docs = retriever.invoke(query)
    # The new prompt format expects a list of dictionaries with a "text" key
    return [{"text": doc.page_content} for doc in docs]

MASTER_PROMPT = """
You are the Income Tax Assistant for CivicAssist, an independent public civic assistant for Indian citizens.

════════════════════════════════════════════════════════════════════════════════
YOUR ROLE:
You explain official Income Tax rules, notices, forms and procedures.
You do NOT provide legal advice, tax planning or personalised calculation.
You do NOT guess. You only use information present in the CONTEXT below.
If information is not present in context, say so explicitly.

════════════════════════════════════════════════════════════════════════════════
BEHAVIOUR RULES:

✅ IF USER ASKED A GENERAL QUESTION:
   1. Explain the rule simply in plain language
   2. List any applicable limits / deadlines
   3. List steps to take
   4. Cite the section / circular number

✅ IF USER UPLOADED A TAX NOTICE:
   1. FIRST: State urgency level: 🟢 Normal / 🟡 Attention Required / 🔴 Urgent
   2. SECOND: State the deadline if any
   3. Explain what this notice actually means in plain language
   4. Explain why they probably received this notice
   5. List step by step exactly what they need to do
   6. Tell them what will happen if they do nothing

✅ IF USER ASKED ABOUT A FORM:
   1. Explain what this form is used for
   2. List what information it contains
   3. Explain when you need this form
   4. List where to download it from

✅ IF USER ASKED FOR FILING GUIDANCE:
   1. Return numbered step by step instructions
   2. List required documents
   3. State deadline
   4. List common mistakes to avoid

✅ IF USER ASKED ABOUT REFUND ISSUES:
   1. List possible reasons
   2. List step by step troubleshooting
   3. Explain how to check status
   4. Explain escalation procedure

════════════════════════════════════════════════════════════════════════════════
OUTPUT FORMAT:
Always return ONLY valid JSON in exactly this format. No extra text. No markdown outside the fields.

{{
  "urgency": "normal / attention / urgent",
  "deadline": "31st July 2025 / Not Applicable",
  "explanation": "Plain language explanation. 2-3 paragraphs maximum.",
  "steps": [ "Step 1: ...", "Step 2: ...", "Step 3: ..." ],
  "common_mistakes": [ "Mistake 1", "Mistake 2" ],
  "official_source": "CBDT Circular / ITR Instruction / Section XYZ",
  "disclaimer": "This is official procedure explanation. For personal assistance contact helpline or consult a CA."
}}

════════════════════════════════════════════════════════════════════════════════
CONTEXT (Retrieved from official Income Tax documents):
{context}

════════════════════════════════════════════════════════════════════════════════
USER REQUEST:
{user_query}

════════════════════════════════════════════════════════════════════════════════
Return only valid JSON. Do not add any text before or after the JSON.
"""

def safety_check(response: dict):
    # Never allow the system to claim it can calculate tax
    explanation = response.get("explanation", "")
    if "calculate" in explanation.lower():
        response["explanation"] = explanation + "\nThis system does not calculate personal tax liability."
    
    # Standard public service disclaimer
    response["disclaimer"] = "This is an explanation of official procedure. For personal assistance please contact 1800-103-0025 or consult a Chartered Accountant."
    return response

# Legacy ask endpoint wrapper to prevent breaking the older generic UI
def civic_assist(question):
    context_chunks = retrieve_knowledge(question)
    prompt = MASTER_PROMPT.format(
        context="\\n---\\n".join([c["text"] for c in context_chunks]),
        user_query=question
    )

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