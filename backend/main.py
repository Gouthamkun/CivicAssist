import logging
import os
import io
import shutil
import json
import re
from datetime import datetime
from typing import List, Tuple, Optional
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
from backend.services.assistant import civic_assist, ENHANCED_PROCESS_PROMPT, safety_check, clean_json_response, MASTER_PROMPT, retrieve_knowledge
from backend.services.graph_service import graph_service
from backend.services.query_mapper import map_query_to_graph_nodes
from backend.services.ocr_service import extract_text, classify_notice, ENHANCED_NOTICE_PROMPT, NOTICE_REGISTRY

# Database & Auth
from backend.database import get_db, create_tables
from backend.models.auth_models import User, Document, BlockchainRecord, CitizenProfile
from backend.services.auth import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user,
    get_current_user_optional
)
from backend.services.encryption import encrypt_document, decrypt_document
from backend.services.blockchain_service import generate_hash, record_on_blockchain, verify_integrity

from apscheduler.schedulers.background import BackgroundScheduler
from backend.models.auth_models import PassportTracking
from backend.services.passport_engine import is_passport_delayed, generate_delay_email_html
from backend.services.notifier import send_delay_email, trigger_voice_call

scheduler = BackgroundScheduler()

def check_passport_delays():
    """Background task to scan for delayed passports and notify users."""
    logger.info("Running background passport delay check...")
    try:
        from backend.database import SessionLocal
        db = SessionLocal()
        # Find active tracking records not yet notified for delay
        records = db.query(PassportTracking).filter(
            PassportTracking.passport_received == False,
            PassportTracking.notified_delay == False
        ).all()

        for record in records:
            if is_passport_delayed(record):
                user = db.query(User).filter(User.id == record.user_id).first()
                if user:
                    logger.warning(f"DELAY DETECTED for user {user.email} (Passport ID: {record.id})")
                    
                    # 1. Generate Grievance Draft (Sync for background job)
                    draft = "Dear RPO, My passport application has exceeded the standard processing time of 30 days. Please provide an update. Regards, " + user.name
                    
                    # 2. Send Email
                    email_success = send_delay_email(user.email, user.name, draft)
                    
                    # 3. Trigger Call
                    call_success = False
                    if user.phone:
                        call_success = trigger_voice_call(user.phone, user.name)
                    
                    if email_success or call_success:
                        record.notified_delay = True
                        db.commit()
                        logger.info(f"Notifications sent to {user.email}")
        db.close()
    except Exception as e:
        logger.error(f"Error in scheduler job: {e}")

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
    if not scheduler.running:
        scheduler.add_job(check_passport_delays, 'interval', minutes=1) # Run every minute for testing, normally 24 hours
        scheduler.start()
        logger.info("Background Scheduler started for Passport Tracking.")

# --- Request Models ---
class QueryRequest(BaseModel):
    question: str

class LoginRequest(BaseModel):
    email: str
    password: str

class QuestionRequest(BaseModel):
    question: str

class ProcessExplainRequest(BaseModel):
    query: str

class RefundRequest(BaseModel):
    issue: str

class PassportTrackRequest(BaseModel):
    application_date: str
    application_type: str
    police_verification: str

# ===== PASSPORT TRACKING ENDPOINTS =====

@app.post("/api/track_passport")
async def track_passport(
    payload: PassportTrackRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        from datetime import datetime
        app_date = datetime.strptime(payload.application_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")

    existing = db.query(PassportTracking).filter(PassportTracking.user_id == current_user.id).first()
    
    if existing:
        existing.application_date = app_date
        existing.application_type = payload.application_type
        existing.police_verification = payload.police_verification
        existing.passport_received = False
        existing.notified_delay = False
    else:
        new_track = PassportTracking(
            user_id=current_user.id,
            application_date=app_date,
            application_type=payload.application_type,
            police_verification=payload.police_verification,
            passport_received=False,
            notified_delay=False
        )
        db.add(new_track)

    db.commit()
    return {"success": True, "message": "Passport tracking active."}

@app.get("/api/passport_status")
async def get_passport_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    record = db.query(PassportTracking).filter(PassportTracking.user_id == current_user.id).first()
    if not record:
        return {"tracking": False}
        
    delayed = is_passport_delayed(record)
    return {
        "tracking": True,
        "application_date": record.application_date.isoformat(),
        "application_type": record.application_type,
        "police_verification": record.police_verification,
        "delayed": delayed,
        "notified": record.notified_delay,
        "passport_received": record.passport_received
    }

@app.post("/api/resolve_passport")
async def resolve_passport(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    record = db.query(PassportTracking).filter(PassportTracking.user_id == current_user.id).first()
    if record:
        record.passport_received = True
        db.commit()
        return {"success": True, "message": "Passport marked as received."}
    raise HTTPException(status_code=404, detail="No active tracking found.")

@app.get("/api/generate_passport_grievance")
async def generate_passport_grievance(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    record = db.query(PassportTracking).filter(PassportTracking.user_id == current_user.id).first()
    if not record:
        raise HTTPException(status_code=400, detail="No passport tracking record found.")

    prompt = f"""
    Generate a formal grievance letter for a delayed passport application.
    Applicant Name: {current_user.name}
    Application Date: {record.application_date.strftime('%d %b %Y')}
    Application Type: {record.application_type}
    Police Status: {record.police_verification}

    Rules:
    - Keep tone extremely professional and polite.
    - Do not claim wrongdoing by the passport office.
    - Request a timeline or status update respectfully.
    - Omit placeholders for addresses, start directly with "Subject: Request for Status Update...".
    """
    
    try:
        response = ollama.chat(
            model='llama3.2:1b',
            messages=[{'role': 'user', 'content': prompt}]
        )
        draft = response['message']['content']
        return {"draft": draft}
    except Exception as e:
        logger.error(f"Grievance generation failed: {e}")
        return {"draft": "Could not generate draft. Please write a formal letter requesting a status update for your application."}

@app.get("/api/test_passport_alert")
async def test_passport_alert(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """FOR HACKATHON DEMO: Immediately triggers Call + Email alert."""
    record = db.query(PassportTracking).filter(PassportTracking.user_id == current_user.id).first()
    if not record:
        # Create a dummy record if none exists for demo
        from datetime import date, timedelta
        record = PassportTracking(
            user_id=current_user.id,
            application_date=date.today() - timedelta(days=40),
            application_type="Normal",
            police_verification="Pending",
            passport_received=False,
            notified_delay=False
        )
        db.add(record)
        db.commit()

    # 1. Generate Draft
    prompt = f"Draft a formal grievance for {current_user.name} regarding passport delay."
    try:
        response = ollama.chat(model='llama3.2:1b', messages=[{'role': 'user', 'content': prompt}])
        draft = response['message']['content']
    except:
        draft = "Dear RPO, I am writing to request a status update on my passport application which has been pending for over 30 days. Kindly expedite the process. Regards, " + current_user.name

    # 2. Send Email
    email_sent = send_delay_email(current_user.email, current_user.name, draft)
    
    # 3. Trigger Call
    call_sent = False
    if current_user.phone:
        call_sent = trigger_voice_call(current_user.phone, current_user.name)
    
    return {
        "success": True,
        "email_sent": email_sent,
        "call_sent": call_sent,
        "message": "Demo alert initiated! Check your phone and email (ensure credentials are set in backend/services/notifier.py)"
    }

# ===== OTHER ENDPOINTS =====

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
def build_profile_context(profile: CitizenProfile) -> str:
    if not profile:
        return "No user profile provided."
    
    return f"""
USER PROFILE CONTEXT:
Employment Type: {profile.employment_type or "N/A"}
Salary Range: {profile.salary_range or "N/A"}
Senior Citizen: {profile.senior_citizen}
ITR Filed Last Year: {profile.itr_filed_last_year}
Past Notices: {profile.past_notice_types or "None"}
"""

def process_custom_rag(user_query: str, context_override: str = None, profile: CitizenProfile = None):
    if context_override:
        context = context_override
    else:
        context_chunks = retrieve_knowledge(user_query)
        context = "\n---\n".join([c["text"] for c in context_chunks])
    
    profile_context = build_profile_context(profile)
    prompt = MASTER_PROMPT.format(context=context, profile_context=profile_context, user_query=user_query)
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
def ask(request: QuestionRequest, db: Session = Depends(get_db), current_user: Optional[User] = Depends(get_current_user_optional)):
    profile = db.query(CitizenProfile).filter(CitizenProfile.user_id == current_user.id).first() if current_user else None
    return {"response": civic_assist(request.question, build_profile_context(profile))}

@app.post("/api/ask_tax_question")
def ask_tax_question(request: QueryRequest, db: Session = Depends(get_db), current_user: Optional[User] = Depends(get_current_user_optional)):
    profile = db.query(CitizenProfile).filter(CitizenProfile.user_id == current_user.id).first() if current_user else None
    return process_custom_rag(request.question, profile=profile)

@app.post("/ask_tax_question")
def ask_tax_question_legacy(request: QuestionRequest, db: Session = Depends(get_db), current_user: Optional[User] = Depends(get_current_user_optional)):
    profile = db.query(CitizenProfile).filter(CitizenProfile.user_id == current_user.id).first() if current_user else None
    return process_custom_rag(request.question, profile=profile)

@app.post("/api/explain_notice")
async def explain_notice_endpoint(file: UploadFile = File(...), db: Session = Depends(get_db), current_user: Optional[User] = Depends(get_current_user_optional)):
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
    profile = db.query(CitizenProfile).filter(CitizenProfile.user_id == current_user.id).first() if current_user else None
    
    # Store past notice history if profile exists
    if profile:
        past_notices = []
        if profile.past_notice_types:
            try:
                past_notices = json.loads(profile.past_notice_types)
            except:
                pass
        if notice_type not in past_notices:
            past_notices.append(notice_type)
            profile.past_notice_types = json.dumps(past_notices)
            db.commit()

    prompt = ENHANCED_NOTICE_PROMPT.format(
        extracted_text=extracted_text,
        notice_type=notice_type,
        context=context,
        profile_context=build_profile_context(profile),
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
async def explain_notice_remote(file: UploadFile = File(...), db: Session = Depends(get_db), current_user: Optional[User] = Depends(get_current_user_optional)):
    return await explain_notice_endpoint(file, db, current_user)

@app.get("/tax_guides/{guide_id}")
def get_guide(guide_id: str, db: Session = Depends(get_db), current_user: Optional[User] = Depends(get_current_user_optional)):
    profile = db.query(CitizenProfile).filter(CitizenProfile.user_id == current_user.id).first() if current_user else None
    return process_custom_rag(f"Step by step guide for: {guide_id}", profile=profile)

@app.get("/tax_forms/{form_name}")
def get_form(form_name: str, db: Session = Depends(get_db), current_user: Optional[User] = Depends(get_current_user_optional)):
    profile = db.query(CitizenProfile).filter(CitizenProfile.user_id == current_user.id).first() if current_user else None
    return process_custom_rag(f"I need to fill {form_name}. Explain it and provide the download link if available.", profile=profile)

@app.post("/refund_guidance")
def refund_guidance(request: RefundRequest, db: Session = Depends(get_db), current_user: Optional[User] = Depends(get_current_user_optional)):
    profile = db.query(CitizenProfile).filter(CitizenProfile.user_id == current_user.id).first() if current_user else None
    return process_custom_rag(f"My tax refund issue: {request.issue}", profile=profile)

# --------- PROFILE ENDPOINTS ---------

class ProfileSaveRequest(BaseModel):
    employment_type: str = ""
    salary_range: str = ""
    senior_citizen: bool = False
    itr_filed_last_year: bool = False

@app.post("/profile/save")
def save_profile(request: ProfileSaveRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    profile = db.query(CitizenProfile).filter(CitizenProfile.user_id == current_user.id).first()
    if not profile:
        profile = CitizenProfile(user_id=current_user.id)
        db.add(profile)
    
    profile.employment_type = request.employment_type
    profile.salary_range = request.salary_range
    profile.senior_citizen = request.senior_citizen
    profile.itr_filed_last_year = request.itr_filed_last_year
    db.commit()
    return {"message": "Context saved successfully.", "success": True}

@app.get("/profile/get")
def get_profile(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    profile = db.query(CitizenProfile).filter(CitizenProfile.user_id == current_user.id).first()
    if not profile:
        return {}
    
    past_notices = []
    if profile.past_notice_types:
        try:
            past_notices = json.loads(profile.past_notice_types)
        except:
            pass

    return {
        "employment_type": profile.employment_type,
        "salary_range": profile.salary_range,
        "senior_citizen": profile.senior_citizen,
        "itr_filed_last_year": profile.itr_filed_last_year,
        "past_notice_types": past_notices
    }

def find_official_forms(query: str, domain: Optional[str] = None):
    """Scan local directories for forms related to the query, filtered by domain."""
    it_dir = r"C:\Users\Goutham\OneDrive\Desktop\IT Forms"
    pf_dir = r"C:\Users\Goutham\OneDrive\Desktop\pf forms"
    found = []
    
    # Simple keyword search in filenames
    q = query.lower()
    
    # Select target directory based on domain or query context
    targets = []
    if domain == "EPFO" or "epf" in q or "uan" in q or "pf" in q:
        targets.append(pf_dir)
    elif domain == "Income Tax" or "tax" in q or "itr" in q:
        targets.append(it_dir)
    else:
        # Fallback to both if ambiguous
        targets = [it_dir, pf_dir]

    for directory in targets:
        if not os.path.exists(directory): continue
        for filename in os.listdir(directory):
            # Key form numbers or specific keywords
            if any(word in filename.lower() for word in q.split() if len(word) >= 2) or \
               (re.search(r'form\s*(\d+)', q) and re.search(r'form\s*(\d+)', filename.lower())):
                file_url = f"/api/view_form/{filename}"
                found.append({"name": filename, "url": file_url})
    
    return found[:5]

@app.get("/api/view_form/{filename}")
def view_form(filename: str):
    it_dir = r"C:\Users\Goutham\OneDrive\Desktop\IT Forms"
    pf_dir = r"C:\Users\Goutham\OneDrive\Desktop\pf forms"
    for d in [it_dir, pf_dir]:
        path = os.path.join(d, filename)
        if os.path.exists(path):
            return StreamingResponse(open(path, "rb"), media_type="application/pdf")
    raise HTTPException(status_code=404, detail="Form not found")

@app.post("/process_explain")
def process_explain(request: ProcessExplainRequest, db: Session = Depends(get_db), current_user: Optional[User] = Depends(get_current_user_optional)):
    profile = db.query(CitizenProfile).filter(CitizenProfile.user_id == current_user.id).first() if current_user else None
    profile_context = build_profile_context(profile)
    
    # 0. Check if this is a specific field question (e.g., "field 3 of Form 19" or "field 1 of ITR-2")
    field_match = re.search(r'field\s*(\d+)\s*of\s*(form|itr)\s*[\-]?\s*(\w+)', request.query.lower())
    if field_match:
        field_num = int(field_match.group(1))
        form_name = field_match.group(3)
        prefix = field_match.group(2) # "form" or "itr"
        
        # Scan data/forms directories for this form
        for dept in ["epfo", "income-tax"]:
            # Try multiple naming patterns
            patterns = [
                f"{prefix}{form_name}.json",
                f"{form_name}.json",
                f"form{form_name}.json"
            ]
            
            for p in patterns:
                guide_path = os.path.join("backend", "data", "forms", dept, p)
                if os.path.exists(guide_path):
                    with open(guide_path, "r") as f:
                        guide_data = json.load(f)
                        field = next((fl for fl in guide_data.get("fields", []) if fl["number"] == field_num), None)
                        if field:
                            return {
                                "overview": f"In **{guide_data['form_name']}**, Field {field_num} is **{field['name']}**.\n\nExplanation: {field['description']}",
                                "official_forms": [{"name": guide_data["form_name"], "url": guide_data["pdf"]}]
                            }

    # 1. Map query to graph nodes
    matches = map_query_to_graph_nodes(request.query)
    
    # Unpack first match safely for domain hint
    domain_hint: Optional[str] = None
    node_id = None
    if matches and isinstance(matches, list) and len(matches) > 0:
        first_match = matches[0]
        if isinstance(first_match, (list, tuple)) and len(first_match) >= 2:
            domain_hint = str(first_match[0])
            node_id = first_match[1]

    # 0. Find any physical forms matching the query (use domain hint if available)
    related_forms = find_official_forms(request.query, domain=domain_hint)
    
    if not matches:
        # Fallback to standard RAG but include forms
        rag_res = process_custom_rag(request.query, profile=profile)
        # Ensure it's a dict and cast to common structure
        if isinstance(rag_res, str): rag_res = {"overview": rag_res}
        final_res = dict(rag_res) # Copy to be safe
        final_res["official_forms"] = related_forms
        return final_res
    
    # 2. Get reasoning chain/path
    reasoning_chain = graph_service.get_reasoning_chain(domain_hint, node_id)
    domain_nodes = graph_service.get_domain_graph(domain_hint)["nodes"]
    
    chain_labels = []
    for cid in reasoning_chain:
        node = next((n for n in domain_nodes if n["id"] == cid), None)
        if node: chain_labels.append(node["label"])
    
    path_str = " → ".join(chain_labels)
    
    # 3. Retrieve RAG context
    context_chunks = retrieve_knowledge(f"{request.query} {node_id} process guidelines")
    context = "\n---\n".join([c["text"] for c in context_chunks])
    
    # 4. Generate structured explanation
    prompt = ENHANCED_PROCESS_PROMPT.format(
        process_path=path_str,
        context=context,
        profile_context=profile_context,
        user_query=request.query
    )
    
    try:
        response = ollama.chat(
            model="llama3",
            messages=[{"role":"user", "content": prompt}],
            options={"temperature": 0.0, "format": "json"}
        )
        result = clean_json_response(response["message"]["content"])
        result["process_chain"] = chain_labels
        result["current_step"] = next((n["label"] for n in domain_nodes if n["id"] == node_id), node_id)
        result["official_forms"] = related_forms
        return safety_check(result)
    except Exception as e:
        logger.error(f"Process Explain failure: {e}")
        return process_custom_rag(request.query, profile=profile)

@app.delete("/profile/delete")
def delete_profile(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    profile = db.query(CitizenProfile).filter(CitizenProfile.user_id == current_user.id).first()
    if profile:
        db.delete(profile)
        db.commit()
    return {"message": "Memory deleted successfully.", "success": True}


# --- SMART FORM FILLING & GUIDES API ---

@app.get("/api/forms/epfo")
def get_epfo_forms():
    """Returns a list of available EPFO forms with metadata."""
    forms_dir = os.path.join("backend", "data", "forms", "epfo")
    forms = []
    if os.path.exists(forms_dir):
        for filename in os.listdir(forms_dir):
            if filename.endswith(".json"):
                with open(os.path.join(forms_dir, filename), "r") as f:
                    data = json.load(f)
                    forms.append({
                        "id": filename.replace(".json", ""),
                        "name": data.get("form_name", filename),
                        "description": data.get("description", ""),
                        "pdf": data.get("pdf", "")
                    })
    return forms

@app.get("/api/forms/income-tax")
def get_it_forms():
    """Returns a list of available Income Tax forms with metadata."""
    forms_dir = os.path.join("backend", "data", "forms", "income-tax")
    forms = []
    if os.path.exists(forms_dir):
        for filename in os.listdir(forms_dir):
            if filename.endswith(".json"):
                with open(os.path.join(forms_dir, filename), "r") as f:
                    data = json.load(f)
                    forms.append({
                        "id": filename.replace(".json", ""),
                        "name": data.get("form_name", filename),
                        "description": data.get("description", ""),
                        "pdf": data.get("pdf", "")
                    })
    return forms

@app.get("/api/form-guide/{department}/{form_id}")
def get_form_guide(department: str, form_id: str):
    """Returns the detailed field explanation guide for a specific form."""
    # Department mapping
    dept_map = {
        "epfo": "epfo",
        "income-tax": "income-tax"
    }
    
    dept_folder = dept_map.get(department.lower())
    if not dept_folder:
        raise HTTPException(status_code=404, detail="Department not found")
        
    file_path = os.path.join("backend", "data", "forms", dept_folder, f"{form_id}.json")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Form guide not found")
        
    with open(file_path, "r") as f:
        return json.load(f)

app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
