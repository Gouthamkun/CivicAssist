from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import json
import ollama

# Import legacy generic function and the new modular RAG tools
from backend.services.assistant import civic_assist, retrieve_knowledge, MASTER_PROMPT, safety_check

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------------------------------------------------------
# Core Request Models
# -----------------------------------------------------------------------------
class QueryRequest(BaseModel):
    question: str

class TaxQuery(BaseModel):
    question: str

class RefundQuery(BaseModel):
    issue: str

# -----------------------------------------------------------------------------
# Original Generic Endpoint (Kept for compatibility with old UI)
# -----------------------------------------------------------------------------
@app.post("/ask")
def ask(request: QueryRequest):
    response = civic_assist(request.question)
    return {"response": response}

# -----------------------------------------------------------------------------
# Helper: PDF Text Extractor
# -----------------------------------------------------------------------------
def extract_text_from_file(file_bytes: bytes) -> str:
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        text = ""
        for page in doc:
            text += page.get_text()
        return text
    except ImportError:
        return "PyMuPDF not installed, unable to extract PDF text."
    except Exception as e:
        return f"Error extracting text from document: {str(e)}"

def clean_json_response(raw_response: str) -> dict:
    """Cleans potential markdown backticks or junk from LLM JSON response."""
    s = raw_response.strip()
    if s.startswith("```json"):
        s = s[7:]
    if s.startswith("```"):
        s = s[3:]
    if s.endswith("```"):
        s = s[:-3]
    s = s.strip()
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        # Fallback for very simple fixes or error reporting
        return {
            "urgency": "attention",
            "deadline": "Check official portal",
            "explanation": "The AI provided a malformed response. Please rephrase your question or contact support.",
            "steps": ["Login to Income Tax Portal", "Check pending actions"],
            "official_source": "System Error",
            "disclaimer": "AI response error."
        }

# -----------------------------------------------------------------------------
# 1. Ask AI Endpoint
# -----------------------------------------------------------------------------
@app.post("/ask_tax_question")
def ask_tax_question(query: TaxQuery):
    context_chunks = retrieve_knowledge(query.question)
    prompt = MASTER_PROMPT.format(
        context = "\n---\n".join([c["text"] for c in context_chunks]),
        user_query = query.question
    )
    response = ollama.chat(
        model="llama3",
        messages=[{"role":"user", "content": prompt}],
        options={"temperature": 0.0, "format": "json"}
    )
    return safety_check(clean_json_response(response["message"]["content"]))

# -----------------------------------------------------------------------------
# 2. Explain Tax Notice Endpoint
# -----------------------------------------------------------------------------
@app.post("/explain_tax_notice")
async def explain_notice(file: UploadFile = File(...)):
    # Read raw bytes into memory (assumes mostly 1-3 page PDF notices)
    file_bytes = await file.read()
    extracted_text = extract_text_from_file(file_bytes)
    
    context_chunks = retrieve_knowledge(extracted_text)
    prompt = MASTER_PROMPT.format(
        context = "\n---\n".join([c["text"] for c in context_chunks]),
        user_query = f"Explain this tax notice I received. The text of the notice is:\n{extracted_text}"
    )
    response = ollama.chat(
        model="llama3",
        messages=[{"role":"user", "content": prompt}],
        options={"temperature": 0.0, "format": "json"}
    )
    return safety_check(clean_json_response(response["message"]["content"]))

# -----------------------------------------------------------------------------
# 3. Filing Guide Endpoint
# -----------------------------------------------------------------------------
@app.get("/tax_guides/{guide_id}")
def get_guide(guide_id: str):
    context_chunks = retrieve_knowledge(f"{guide_id} step by step procedure")
    prompt = MASTER_PROMPT.format(
        context = "\n---\n".join([c["text"] for c in context_chunks]),
        user_query = f"Give me the step by step guide for {guide_id}"
    )
    response = ollama.chat(
        model="llama3",
        messages=[{"role":"user", "content": prompt}],
        options={"temperature": 0.0, "format": "json"}
    )
    return safety_check(clean_json_response(response["message"]["content"]))

# -----------------------------------------------------------------------------
# 4. Tax Forms Endpoint
# -----------------------------------------------------------------------------
@app.get("/tax_forms/{form_name}")
def get_form(form_name: str):
    context_chunks = retrieve_knowledge(form_name)
    prompt = MASTER_PROMPT.format(
        context = "\n---\n".join([c["text"] for c in context_chunks]),
        user_query = f"Explain what is {form_name}"
    )
    response = ollama.chat(
        model="llama3",
        messages=[{"role":"user", "content": prompt}],
        options={"temperature": 0.0, "format": "json"}
    )
    return safety_check(clean_json_response(response["message"]["content"]))

# -----------------------------------------------------------------------------
# 5. Refund Guidance Endpoint
# -----------------------------------------------------------------------------
@app.post("/refund_guidance")
def refund_guidance(query: RefundQuery):
    context_chunks = retrieve_knowledge(query.issue)
    prompt = MASTER_PROMPT.format(
        context = "\n---\n".join([c["text"] for c in context_chunks]),
        user_query = f"I have this problem with my income tax refund: {query.issue}"
    )
    response = ollama.chat(
        model="llama3",
        messages=[{"role":"user", "content": prompt}],
        options={"temperature": 0.0, "format": "json"}
    )
    return safety_check(clean_json_response(response["message"]["content"]))

app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
