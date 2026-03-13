import ollama
import os
import json
import re

# Force CPU usage
os.environ["CUDA_VISIBLE_DEVICES"] = ""

from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings

embedding = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

db = Chroma(
    persist_directory="vector_db",
    embedding_function=embedding
)

# Increased context to 10 chunks for deeper extraction
retriever = db.as_retriever(search_kwargs={"k":10})

def retrieve_knowledge(query: str):
    """Reusable vector DB retriever for all endpoints."""
    docs = retriever.invoke(query)
    return [{"text": doc.page_content} for doc in docs]

def clean_json_response(raw_response: str) -> dict:
    """Cleans potential markdown backticks or junk and enforces ALL required keys."""
    if not raw_response:
        return {}
    
    s = raw_response.strip()
    # Remove markdown code blocks
    s = re.sub(r'^```json\s*', '', s, flags=re.MULTILINE)
    s = re.sub(r'^```\s*', '', s, flags=re.MULTILINE)
    s = re.sub(r'\s*```$', '', s, flags=re.MULTILINE)
    
    try:
        # Extract the largest JSON object found
        json_match = re.search(r'(\{.*\})', s, re.DOTALL)
        if json_match:
            s = json_match.group(1)
            
        try:
            data = json.loads(s, strict=False)
        except json.JSONDecodeError:
            # Fallback: try to manually escape newlines that might break parsing
            s = s.replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t')
            data = json.loads(s, strict=False)
            
        if not isinstance(data, dict):
             raise ValueError("Parsed JSON is not a dictionary")
             
        # CONSISTENT SCHEMA DEFAULTS
        schema = {
            "urgency": "normal",
            "deadline": "Not Applicable",
            "overview": "Information not found.",
            "required_documents": [],
            "steps": [],
            "common_mistakes": [],
            "official_portal_link": "",
            "official_source": "CivicAssist Knowledge Base",
            "disclaimer": "This is official procedure explanation only.",
            "action_url": "",
            "action_label": ""
        }
        
        # Merge AI data with schema defaults.
        final_data = schema.copy()
        
        # 1. Start with schema defaults
        # 2. OVERLAY all keys from AI data (dont discard unknown keys)
        for key, val in data.items():
            if val is not None and val != "" and val != []:
                final_data[key] = val
        
        # 3. Handle Legacy/Cross-Feature Mappings
        # If we have 'explanation' (from Process Graph/OCR) but not 'overview' (from RAG), 
        # or vice-versa, sync them so the UI always has a primary text field.
        
        main_text = final_data.get("explanation") or final_data.get("overview") or final_data.get("answer") or "No detailed information was found for this specific query."
        
        final_data["overview"] = main_text
        final_data["explanation"] = main_text
        final_data["answer"] = main_text
        
        # Ensure common keys for specific features exist
        if "process_chain" not in final_data: final_data["process_chain"] = []
        if "next_steps" not in final_data: final_data["next_steps"] = final_data.get("steps", [])
        
        return final_data
    except Exception as e:
        print(f"JSON Cleaning Error: {e} | Raw: {raw_response[0:200]}")
        return {
            "urgency": "attention",
            "deadline": "Try again",
            "explanation": "The AI provided a malformed response.",
            "answer": "Error parsing AI response.",
            "steps": ["Refresh and try again"],
            "common_mistakes": ["System overload"],
            "official_source": "System Error",
            "disclaimer": "Internal Error.",
            "action_url": "",
            "action_label": ""
        }

MASTER_PROMPT = """
You are CivicAssist AI, a government guidance assistant.
Your job is to convert retrieved knowledge from government documents into a clear, formal, structured guidance response for citizens.

════════════════════════════════════════════════════════════════════════════════
MANDATORY FORM DOWNLOADS (Use these OR mention them if relevant):
- ITR-2: url 'forms/ITR-2.pdf', label 'Download ITR-2'
- ITR-3: url 'forms/ITR-3.pdf', label 'Download ITR-3'
- ITR-5: url 'forms/ITR-5.pdf', label 'Download ITR-5'
- ITR-6: url 'forms/ITR-6.pdf', label 'Download ITR-6'
- Form 16: url 'forms/Form 16.pdf', label 'Download Form 16 Guide'
- Form 26AS: url 'forms/Form 26AS.pdf', label 'Download 26AS Sample'
- AIS / TIS: url 'forms/AIS.pdf', label 'Download AIS Guide'
- PF Withdrawal (Form 19): url 'forms/PF Final Settlement.pdf', label 'Download Form 19'
- PF Transfer (Form 13): url 'forms/PF Transfer.pdf', label 'Download Form 13'

TECHNICAL EXTRACTION RULES:
1. OVERVIEW: MUST be exactly 1-2 sentences summarizing the process. NEVER include steps or document lists here.
2. STEPS ARRAY: You MUST break down the procedure into individual string elements within the "steps" JSON array.
3. DOCUMENTS ARRAY: Put any required documents into the "required_documents" JSON array.
4. FORBID GENERIC SUMMARIES. Quote exact terms like "Para 57".
5. NO NEWLINES. Do not use literal newlines (\n) inside JSON string values.

════════════════════════════════════════════════════════════════════════════════
OUTPUT SCHEMA (MANDATORY):
{{
  "urgency": "normal / attention / urgent",
  "deadline": "Date or Not Applicable",
  "overview": "Brief 2-3 sentence summary explaining the process. Verbatim citations where possible.",
  "required_documents": ["Aadhaar Card", "PAN Card"],
  "steps": ["Step 1", "Step 2"],
  "common_mistakes": ["Important note 1", "Legally significant mistake"],
  "official_portal_link": "https://url-to-portal if available",
  "official_source": "Paragraph/Section/Form Name",
  "disclaimer": "Technical disclaimer.",
  "action_url": "forms/filename.pdf",
  "action_label": "Download button text"
}}

EXAMPLE EXCELLENT JSON:
{{
  "urgency": "normal",
  "deadline": "Not Applicable",
  "overview": "To withdraw your PF, you must submit Form 19 as per Para 57. The process can be completed online via the UAN Member Portal.",
  "required_documents": ["Aadhaar Card linked to UAN", "Cancelled Cheque", "PAN Card"],
  "steps": ["Step 1: Login to UAN portal.", "Step 2: Go to Online Services and select Claim (Form 31, 19, 10C & 10D).", "Step 3: Verify bank account.", "Step 4: Select 'Only PF Withdrawal (Form 19)'."],
  "common_mistakes": ["Not linking Aadhaar with UAN", "Applying before completing 2 months of unemployment"],
  "official_portal_link": "https://unifiedportal-mem.epfindia.gov.in/memberinterface/",
  "official_source": "Para 57",
  "disclaimer": "This is official procedure explanation only.",
  "action_url": "forms/PF Final Settlement.pdf",
  "action_label": "Download Form 19"
}}
════════════════════════════════════════════════════════════════════════════════
CONTEXT:
{context}

════════════════════════════════════════════════════════════════════════════════
{profile_context}

CRITICAL PERSONALIZATION ENGINE (HIGH PRIORITY):
Your response MUST be deeply personalized. Generic answers are considered a failure.
1. ACKNOWLEDGE ALL TRAITS: Start the 'overview' by explicitly mentioning at least TWO profile traits.
   - Example: "As a Senior Citizen in the 10-20L salary bracket, Section 80C is particularly useful because..."
2. DYNAMIC TAX LIMITS:
   - If 'senior_citizen': True → ALWAYS mention the higher basic exemption (₹3L for Age 60-80, ₹5L for 80+).
   - If 'salary_range': 10L+ → ALWAYS mention the benefit of the Old Regime vs New Regime for their bracket.
3. CONTEXTUAL DOCUMENTS:
   - If 'ITR Filed': False → Remind them that they need to register on the portal first.
   - If 'business'/'freelancer' → Add Form 10-IE (Regime selection) to required_documents.
4. PERSONALIZED FOR HEADER: At the very beginning of the 'overview', include a tag: "[Personalized Guidance Context Applied]"
5. If NO profile is provided, use a "[Public Knowledge]" tag instead.

════════════════════════════════════════════════════════════════════════════════
USER REQUEST:
{user_query}
Return ONLY valid JSON. Focus on TECHNICAL details from the context.
"""

ENHANCED_PROCESS_PROMPT = """
You are CivicAssist AI, a government process navigator.
Your job is to explain a government workflow using BOTH a structured process graph path and retrieved document context.

════════════════════════════════════════════════════════════════════════════════
PROCESS GRAPH PATH:
{process_path}

════════════════════════════════════════════════════════════════════════════════
DOCUMENT CONTEXT:
{context}

════════════════════════════════════════════════════════════════════════════════
USER PROFILE:
{profile_context}

════════════════════════════════════════════════════════════════════════════════
USER QUERY:
{user_query}

OUTPUT SCHEMA (MANDATORY):
{{
  "process_chain": ["NodeA", "NodeB", "NodeC"],
  "current_step": "The node that matches user's current situation",
  "explanation": "Detailed explanation incorporating graph reasoning.",
  "required_documents": ["Doc 1", "Doc 2"],
  "next_steps": ["Step 1", "Step 2"],
  "official_source": "Source citation"
}}

Return ONLY valid JSON.
"""

def safety_check(response: dict):
    # Standard public service disclaimer
    response["disclaimer"] = "This is a technical explanation based on official documents. For personal assistance please contact the official helpline or consult a professional."
    return response

def civic_assist(question, profile_context="No user profile provided."):
    context_chunks = retrieve_knowledge(question)
    prompt = MASTER_PROMPT.format(
        context="\n---\n".join([c["text"] for c in context_chunks]),
        profile_context=profile_context,
        user_query=question
    )

    response = ollama.chat(
        model="llama3",
        messages=[{"role":"user","content":prompt}],
        options={"temperature": 0.0, "format": "json"}
    )
    
    return safety_check(clean_json_response(response["message"]["content"]))