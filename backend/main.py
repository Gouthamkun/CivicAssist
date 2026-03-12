import logging
import os
import io
import shutil
import json
from datetime import datetime
from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional

import ollama

# Pipeline modules (Local)
from backend.rag.retrieval_pipeline import retrieve
from backend.services.response_builder import build_response
from backend.services.file_processor import process_file
from backend.classifier.document_classifier import classify_document
from backend.services.logger import log_pipeline_event
from backend.services.identity_service import extract_info_from_doc, extract_uan_from_passbook

# Legacy assistant (Local) - import explain_notice from original file 
from backend.services.notice_explainer import explain_notice as legacy_explain_notice

# Assistant & Ollama (Remote)
from backend.services.assistant import clean_json_response, MASTER_PROMPT, civic_assist, retrieve_knowledge, safety_check
from backend.services.ocr_service import extract_text, classify_notice, ENHANCED_NOTICE_PROMPT, NOTICE_REGISTRY

# Database & Auth
from backend.database import get_db, create_tables
from backend.models.auth_models import User, Document, BlockchainRecord
from backend.services.auth import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user,
)
from backend.services.encryption import encrypt_document, decrypt_document
from backend.services.blockchain_service import generate_hash, record_on_blockchain, verify_integrity

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

logger = logging.getLogger("civicassist.api")

app = FastAPI(title="CivicAssist API", version="3.0")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Create DB tables on startup ---
@app.on_event("startup")
def on_startup():
    create_tables()
    logger.info("Database tables created / verified.")

# --- Request Models ---
class QueryRequest(BaseModel):
    question: str

class LoginRequest(BaseModel):
    email: str
    password: str

class QuestionRequest(BaseModel):
    question: str

class RefundRequest(BaseModel):
    issue: str

# ===== AUTH ENDPOINTS =====

async def save_user_document_helper(db, user_id, doc_type, file):
    """Refactored helper to save/update secured user documents."""
    if not file:
        return
    file_bytes = await file.read()
    doc_hash = generate_hash(file_bytes)
    record_on_blockchain(db, user_id, doc_type, doc_hash)
    encrypted = encrypt_document(file_bytes)
    user_dir = os.path.join(UPLOAD_DIR, str(user_id))
    os.makedirs(user_dir, exist_ok=True)
    file_path = os.path.join(user_dir, f"{doc_type}.enc")
    with open(file_path, "wb") as f:
        f.write(encrypted["ciphertext"])
    
    filename = file.filename or doc_type
    if "." not in filename:
        ext_map = {"application/pdf": ".pdf", "image/png": ".png", "image/jpeg": ".jpg", "image/jpg": ".jpg"}
        filename += ext_map.get(file.content_type, "")

    existing = db.query(Document).filter(
        Document.user_id == user_id,
        Document.doc_type == doc_type
    ).first()
    
    if existing:
        existing.filename = filename
        existing.content_type = file.content_type or "application/octet-stream"
        existing.encryption_nonce = encrypted["nonce"]
        existing.uploaded_at = datetime.utcnow()
    else:
        new_doc = Document(
            user_id=user_id,
            doc_type=doc_type,
            filename=filename,
            content_type=file.content_type or "application/octet-stream",
            file_data=b"", 
            encryption_nonce=encrypted["nonce"],
            is_encrypted=True,
        )
        db.add(new_doc)
    db.commit()
    return file_bytes

@app.post("/api/register")
async def register(
    name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(...),
    password: str = Form(...),
    aadhaar_file: Optional[UploadFile] = File(None),
    pan_file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
):
    email = email.strip().lower()
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise HTTPException(status_code=400, detail="An account with this email already exists.")
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters.")
    
    user = User(
        name=name.strip(),
        email=email,
        phone=phone.strip(),
        hashed_password=hash_password(password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Process initial documents if uploaded - also extract names to sync
    if aadhaar_file:
        fbytes = await save_user_document_helper(db, user.id, "aadhaar", aadhaar_file)
        try:
            info = extract_info_from_doc(fbytes, "aadhaar")
            if info.get("name"):
                user.name = info["name"]
                db.commit()
        except Exception as e:
            logger.error(f"Post-registration Aadhaar sync failed: {e}")

    if pan_file:
        fbytes = await save_user_document_helper(db, user.id, "pan", pan_file)
        try:
            info = extract_info_from_doc(fbytes, "pan")
            if info.get("name") and len(user.name.split()) < 2:
                user.name = info["name"]
                db.commit()
        except Exception as e:
            logger.error(f"Post-registration PAN sync failed: {e}")

    logger.info(f"[/api/register] New user registered: {email}")
    return {"success": True, "message": "Registration successful!"}

@app.post("/api/upload_document")
async def upload_document(
    doc_type: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if doc_type not in ["aadhaar", "pan"]:
        raise HTTPException(status_code=400, detail="Invalid document type.")
    
    fbytes = await save_user_document_helper(db, current_user.id, doc_type, file)
    
    # Sync name if extracted from new upload
    try:
        info = extract_info_from_doc(fbytes, doc_type)
        if info.get("name"):
            current_user.name = info["name"]
            db.commit()
    except Exception as e:
        logger.error(f"Post-upload {doc_type} name sync failed: {e}")

    return {"success": True, "message": f"{doc_type.capitalize()} uploaded and secured with blockchain integrity!"}

@app.get("/api/verify_integrity/{doc_type}")
async def verify_document_integrity(
    doc_type: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    doc = db.query(Document).filter(
        Document.user_id == current_user.id, Document.doc_type == doc_type
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    file_path = os.path.join(UPLOAD_DIR, str(current_user.id), f"{doc_type}.enc")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Physical file missing.")
    with open(file_path, "rb") as f:
        ciphertext = f.read()
    try:
        plaintext = decrypt_document(ciphertext, doc.encryption_nonce)
        result = verify_integrity(db, current_user.id, doc_type, plaintext)
    except Exception as e:
        logger.error(f"Decryption failed during integrity check: {e}")
        result = {
            "authentic": False,
            "error": "Decryption failed - Document content is corrupted or tampered.",
            "current_hash": "ERROR",
            "stored_hash": db.query(BlockchainRecord).filter(
                BlockchainRecord.user_id == current_user.id, BlockchainRecord.doc_type == doc_type
            ).first().doc_hash
        }
    return result

@app.get("/api/view_document/{doc_type}")
async def view_document(
    doc_type: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    doc = db.query(Document).filter(
        Document.user_id == current_user.id, Document.doc_type == doc_type
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    file_path = os.path.join(UPLOAD_DIR, str(current_user.id), f"{doc_type}.enc")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Physical file missing.")
    with open(file_path, "rb") as f:
        ciphertext = f.read()
    plaintext = decrypt_document(ciphertext, doc.encryption_nonce)
    
    # Set headers to allow inline viewing in browser
    headers = {
        "Content-Disposition": f'inline; filename="{doc.filename}"',
        "Content-Type": doc.content_type
    }
    return StreamingResponse(io.BytesIO(plaintext), media_type=doc.content_type, headers=headers)

@app.get("/api/download_document/{doc_type}")
async def download_document(
    doc_type: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    doc = db.query(Document).filter(
        Document.user_id == current_user.id, Document.doc_type == doc_type
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    file_path = os.path.join(UPLOAD_DIR, str(current_user.id), f"{doc_type}.enc")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Physical file missing.")
    with open(file_path, "rb") as f:
        ciphertext = f.read()
    plaintext = decrypt_document(ciphertext, doc.encryption_nonce)
    headers = {
        "Content-Disposition": f'attachment; filename="{doc.filename}"',
        "Access-Control-Expose-Headers": "Content-Disposition"
    }
    return StreamingResponse(io.BytesIO(plaintext), media_type=doc.content_type, headers=headers)

@app.delete("/api/remove_document/{doc_type}")
async def remove_document(
    doc_type: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    doc = db.query(Document).filter(
        Document.user_id == current_user.id, Document.doc_type == doc_type
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    
    # Remove database entries
    db.delete(doc)
    # Also remove blockchain record for this user/doc if it exists
    bc_record = db.query(BlockchainRecord).filter(
        BlockchainRecord.user_id == current_user.id, BlockchainRecord.doc_type == doc_type
    ).first()
    if bc_record:
        db.delete(bc_record)
        
    db.commit()
    
    # Remove physical file
    file_path = os.path.join(UPLOAD_DIR, str(current_user.id), f"{doc_type}.enc")
    if os.path.exists(file_path):
        os.remove(file_path)
        
    return {"success": True, "message": f"{doc_type.capitalize()} removed successfully."}

@app.get("/api/user_documents")
def get_user_documents(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    docs = db.query(Document).filter(Document.user_id == current_user.id).all()
    return {"uploaded_types": [d.doc_type for d in docs]}

@app.post("/api/login")
def login(request: LoginRequest, db: Session = Depends(get_db)):
    email = request.email.strip().lower()
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=401, detail="Account not found. Please register first.")
    if not verify_password(request.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect password. Please try again.")
    token = create_access_token(user.id, user.email)
    return {
        "success": True, "token": token,
        "user": {"name": user.name, "email": user.email, "phone": user.phone},
    }

@app.get("/api/me")
def get_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id, "name": current_user.name,
        "email": current_user.email, "phone": current_user.phone,
    }

# --- EPFO PF Withdrawal Extension ---
@app.get("/api/epfo/user-info")
async def get_epfo_user_info(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    doc = db.query(Document).filter(Document.user_id == current_user.id, Document.doc_type == "aadhaar").first()
    if not doc:
        doc = db.query(Document).filter(Document.user_id == current_user.id, Document.doc_type == "pan").first()
    if not doc:
        return {"name": current_user.name, "dob": "Not available (Please upload Aadhaar/PAN)", "source": "registration"}
    file_path = os.path.join(UPLOAD_DIR, str(current_user.id), f"{doc.doc_type}.enc")
    if not os.path.exists(file_path):
        return {"name": current_user.name, "dob": "File missing", "source": "error"}
    with open(file_path, "rb") as f:
        ciphertext = f.read()
    plaintext = decrypt_document(ciphertext, doc.encryption_nonce)
    info = extract_info_from_doc(plaintext, doc.doc_type)
    return {"name": info.get("name") or current_user.name, "dob": info.get("dob") or "Not found in document", "source": doc.doc_type}

@app.post("/api/epfo/verify-passbook")
async def verify_passbook(file: UploadFile = File(...), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    from backend.services.identity_service import normalize_name, normalize_dob
    file_bytes = await file.read()
    pb_info = extract_uan_from_passbook(file_bytes)
    pb_name_norm = normalize_name(pb_info["name"])
    pb_dob_norm = normalize_dob(pb_info["dob"])
    docs = db.query(Document).filter(Document.user_id == current_user.id, Document.doc_type.in_(["aadhaar", "pan"])).all()
    baselines = []
    for doc in docs:
        file_path = os.path.join(UPLOAD_DIR, str(current_user.id), f"{doc.doc_type}.enc")
        if os.path.exists(file_path):
            with open(file_path, "rb") as f:
                ciphertext = f.read()
            plaintext = decrypt_document(ciphertext, doc.encryption_nonce)
            info = extract_info_from_doc(plaintext, doc.doc_type)
            baselines.append({
                "name": normalize_name(info.get("name") or current_user.name),
                "dob": normalize_dob(info.get("dob")),
                "source": doc.doc_type
            })
    if not baselines:
        baselines.append({"name": normalize_name(current_user.name), "dob": None, "source": "registration"})
    name_mismatch = False
    dob_mismatch = False
    if pb_name_norm:
        matched_any_name = False
        for bl in baselines:
            if pb_name_norm == bl["name"]:
                matched_any_name = True
                break
        if not matched_any_name:
            name_mismatch = True
    else:
        name_mismatch = True
    if pb_dob_norm:
        matched_any_dob = False
        dob_docs_exist = False
        for bl in baselines:
            if bl["dob"]:
                dob_docs_exist = True
                if pb_dob_norm == bl["dob"]:
                    matched_any_dob = True
                    break
        if dob_docs_exist and not matched_any_dob:
            dob_mismatch = True
    elif any(bl["dob"] for bl in baselines):
        dob_mismatch = True
    issues = []
    if name_mismatch:
        issues.append("Name mismatch between UAN and Aadhaar/PAN")
    if dob_mismatch:
        issues.append("Date of Birth mismatch")
    
    status = "Verified Successfully" if not issues else "Issues Detected"
    
    if not issues:
        fix = "Congratulations! All your details from the UAN passbook match your uploaded identity documents (Aadhaar/PAN). You are now eligible for smooth PF withdrawal processing without any data conflict."
    else:
        # Use RAG to generate a specific fix based on the knowledge base
        query = f"How to fix mismatch in EPFO portal for: {', '.join(issues)}. Provide step by step instructions."
        rag_res = process_custom_rag(query)
        fix = rag_res.get("answer") or rag_res.get("overview") or "Please log in to the EPFO Unified Portal and navigate to Manage -> Modify Basic Details. Submit your correct details as per your Aadhaar card and then ask your employer to approve the request."

    return {
        "status": status, 
        "problems_found": issues, 
        "suggested_fix": fix, 
        "extracted_details": pb_info
    }


# -----------------------------------------------------------------------------
# Main RAG AI Logic (Used across endpoints)
# -----------------------------------------------------------------------------
def process_custom_rag(user_query: str, context_override: str = None):
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

@app.post("/api/ask_tax_question")
def ask_tax_question(request: QueryRequest):
    # Support for the frontend's api call that is meant to use custom RAG
    return process_custom_rag(request.question)

@app.post("/ask_tax_question")
def ask_tax_question_legacy(request: QuestionRequest):
    return process_custom_rag(request.question)

@app.post("/api/explain_notice")
async def explain_notice_endpoint(file: UploadFile = File(...)):
    # Connect both pipelines. The remote ollama one is more robust.
    content = await file.read()
    content_type = file.content_type
    try:
        extracted_text = extract_text(content, content_type)
    except Exception as e:
        extracted_text = "FAILED TO EXTRACT TEXT. PLEASE ENSURE IT IS A CLEAR PDF OR IMAGE."
    notice_type = classify_notice(extracted_text)
    context_chunks = retrieve_knowledge(f"{notice_type} explanation actions forms guidelines")
    context = "\n---\n".join([c["text"] for c in context_chunks])
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
        import re
        s = response["message"]["content"].strip()
        json_match = re.search(r'(\{.*\})', s, re.DOTALL)
        if json_match:
            s = json_match.group(1)
        structured_data = json.loads(s, strict=False)
        structured_data["extracted_text_preview"] = extracted_text[:300] + "..." if len(extracted_text) > 50 else "Not enough text found via OCR."
        
        # Ensure new intelligence fields exist with sensible fallbacks
        defaults = {
            "department": "Unknown Department",
            "severity_index": "Medium",
            "risk_analysis": "N/A",
            "consequence": "N/A",
            "strategy": "N/A",
            "steps": [],
            "forms_needed": [],
            "official_links": [],
            "helpline": "1800-103-0025 (IT) / 1800-118-005 (EPFO)"
        }
        for k, v in defaults.items():
            if k not in structured_data or not structured_data[k]:
                structured_data[k] = v
                
        return structured_data
    except Exception as e:
        logger.error(f"Notice parsing failed: {e}")
        return {
            "notice_type": notice_type,
            "department": "Unknown",
            "urgency": "attention",
            "severity_index": "High",
            "deadline": "Check Notice",
            "risk_analysis": "The notice could not be analyzed deeply. Ignoring government notices can lead to penalties or legal action.",
            "consequence": "Varies by department",
            "explanation": "Could not parse AI response perfectly. This usually happens if the text is blurry or the notice structure is complex.",
            "strategy": "Upload a clearer photo or manually check the official portal.",
            "steps": ["Login to official portal", "Identify notice section", "Verify deadline"],
            "forms_needed": [],
            "official_links": [],
            "helpline": "1800-103-0025",
            "extracted_text_preview": extracted_text[:200]
        }

@app.post("/explain_notice")
async def explain_notice_remote(file: UploadFile = File(...)):
    return await explain_notice_endpoint(file)

@app.get("/tax_guides/{guide_id}")
def get_guide(guide_id: str):
    return process_custom_rag(f"Step by step guide for: {guide_id}")

@app.get("/tax_forms/{form_name}")
def get_form(form_name: str):
    return process_custom_rag(f"I need to fill {form_name}. Explain it and provide the download link if available.")

@app.post("/refund_guidance")
def refund_guidance(request: RefundRequest):
    return process_custom_rag(f"My tax refund issue: {request.issue}")

app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
