import os
import shutil
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import ollama
import json

from backend.services.assistant import clean_json_response, MASTER_PROMPT, civic_assist, retrieve_knowledge, safety_check

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request Models
class QuestionRequest(BaseModel):
    question: str

class RefundRequest(BaseModel):
    issue: str

# -----------------------------------------------------------------------------
# Main RAG AI Logic (Used across endpoints)
# -----------------------------------------------------------------------------

def process_custom_rag(user_query: str, context_override: str = None):
    """Internal helper to process queries with either vector DB context or specific override."""
    if context_override:
        context = context_override
    else:
        context_chunks = retrieve_knowledge(user_query)
        context = "\n---\n".join([c["text"] for c in context_chunks])
    
    prompt = MASTER_PROMPT.format(context=context, user_query=user_query)
    
    response = ollama.chat(
        model="llama3",
        messages=[{"role":"user", "content": prompt}],
        options={"temperature": 0.0, "format": "json"}
    )
    return safety_check(clean_json_response(response["message"]["content"]))

# -----------------------------------------------------------------------------
# API Endpoints
# -----------------------------------------------------------------------------

@app.post("/ask")
def ask(request: QuestionRequest):
    return {"response": civic_assist(request.question)}

@app.post("/ask_tax_question")
def ask_tax_question(request: QuestionRequest):
    return process_custom_rag(request.question)

from backend.services.ocr_service import extract_text, classify_notice, ENHANCED_NOTICE_PROMPT, NOTICE_REGISTRY

@app.post("/explain_notice")
async def explain_notice(file: UploadFile = File(...)):
    # Read the file contents directly into memory
    content = await file.read()
    content_type = file.content_type

    # 1. OCR Extraction (handles PDF or Images automatically)
    try:
        extracted_text = extract_text(content, content_type)
    except Exception as e:
        print(f"OCR Error: {e}")
        extracted_text = "FAILED TO EXTRACT TEXT. PLEASE ENSURE IT IS A CLEAR PDF OR IMAGE."
        
    # 2. Hybrid Classification
    notice_type = classify_notice(extracted_text)
    
    # 3. Targeted RAG Retrieval
    # Provide the AI with the extracted text, class, and official CBDT/EPFO sources
    context_chunks = retrieve_knowledge(f"{notice_type} explanation actions forms guidelines")
    context = "\n---\n".join([c["text"] for c in context_chunks])
    
    # 4. Generate highly structured Notice Explanation using the specialized prompt
    prompt = ENHANCED_NOTICE_PROMPT.format(
        extracted_text=extracted_text,
        notice_type=notice_type,
        context=context,
        registry=json.dumps(NOTICE_REGISTRY.get(notice_type, {}))
    )
    
    try:
        response = ollama.chat(
            model="llama3", 
            messages=[{"role":"user", "content": prompt}], 
            options={"temperature": 0.0, "format": "json"}
        )
        
        # Clean JSON and add a preview of extracted text for transparency
        import re
        s = response["message"]["content"].strip()
        json_match = re.search(r'(\{.*\})', s, re.DOTALL)
        if json_match:
            s = json_match.group(1)
        structured_data = json.loads(s, strict=False)
        structured_data["extracted_text_preview"] = extracted_text[:300] + "..." if len(extracted_text) > 50 else "Not enough text found via OCR."
        
        # Ensure fallback defaults exist
        for k in ["steps", "forms_needed", "official_links"]:
            if k not in structured_data:
                structured_data[k] = []
        if "helpline" not in structured_data:
             structured_data["helpline"] = "1800-103-0025 (IT) / 1800-118-005 (EPFO) / 1800-258-1800 (Passport)"
             
        return structured_data
        
    except Exception as e:
        return {
            "notice_type": notice_type,
            "urgency": "attention",
            "deadline": "Not Applicable",
            "explanation": "Could not parse AI response perfectly. Extracted text may be too blurry.",
            "why_received": "Unknown",
            "steps": ["Retry uploading a clearer image."],
            "forms_needed": [],
            "official_links": [],
            "what_if_ignore": "Unknown",
            "helpline": "1800-103-0025 (IT) / 1800-118-005 (EPFO)",
            "extracted_text_preview": extracted_text[:200]
        }

@app.get("/tax_guides/{guide_id}")
def get_guide(guide_id: str):
    return process_custom_rag(f"Step by step guide for: {guide_id}")

@app.get("/tax_forms/{form_name}")
def get_form(form_name: str):
    # Specifically ensure the AI knows we want a form explanation and the link
    return process_custom_rag(f"I need to fill {form_name}. Explain it and provide the download link if available.")

@app.post("/refund_guidance")
def refund_guidance(request: RefundRequest):
    return process_custom_rag(f"My tax refund issue: {request.issue}")

# -----------------------------------------------------------------------------
# Static Files & Frontend
# -----------------------------------------------------------------------------
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
