import logging
from datetime import datetime
from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional
import io
import os

# Pipeline modules
from backend.rag.retrieval_pipeline import retrieve
from backend.services.response_builder import build_response
from backend.services.file_processor import process_file
from backend.classifier.document_classifier import classify_document
from backend.services.notice_explainer import explain_notice
from backend.services.logger import log_pipeline_event
from backend.services.identity_service import extract_info_from_doc, extract_uan_from_passbook

# Legacy assistant (backward compat)
from backend.services.assistant import civic_assist

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


# ===== AUTH ENDPOINTS =====

@app.post("/api/register")
async def register(
    name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    """Register a new user (basic info only). Documents are uploaded later in the dashboard."""
    # Normalize email
    email = email.strip().lower()

    # Check if user already exists
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise HTTPException(status_code=400, detail="An account with this email already exists.")

    # Validate password length
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters.")

    # Create user
    user = User(
        name=name.strip(),
        email=email,
        phone=phone.strip(),
        hashed_password=hash_password(password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    logger.info(f"[/api/register] New user registered: {email}")
    return {"success": True, "message": "Registration successful!"}


@app.post("/api/upload_document")
async def upload_document(
    doc_type: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload and encrypt a user document (Aadhaar/PAN)."""
    if doc_type not in ["aadhaar", "pan"]:
        raise HTTPException(status_code=400, detail="Invalid document type.")

    # Read and encrypt file
    file_bytes = await file.read()
    
    # --- Blockchain: Generate hash of raw bytes ---
    doc_hash = generate_hash(file_bytes)
    record_on_blockchain(db, current_user.id, doc_type, doc_hash)
    
    encrypted = encrypt_document(file_bytes)

    # Save to disk
    user_dir = os.path.join(UPLOAD_DIR, str(current_user.id))
    os.makedirs(user_dir, exist_ok=True)
    file_path = os.path.join(user_dir, f"{doc_type}.enc")
    
    with open(file_path, "wb") as f:
        f.write(encrypted["ciphertext"])

    # Check if document already exists for this user (update or create)
    existing = db.query(Document).filter(
        Document.user_id == current_user.id,
        Document.doc_type == doc_type
    ).first()

    # Ensure filename has extension if missing
    filename = file.filename or doc_type
    if "." not in filename:
        ext_map = {
            "application/pdf": ".pdf",
            "image/png": ".png",
            "image/jpeg": ".jpg",
            "image/jpg": ".jpg",
        }
        filename += ext_map.get(file.content_type, "")

    if existing:
        existing.filename = filename
        existing.content_type = file.content_type or "application/octet-stream"
        # existing.file_data = encrypted["ciphertext"] # Moved to disk
        existing.encryption_nonce = encrypted["nonce"]
        existing.uploaded_at = datetime.utcnow()
    else:
        new_doc = Document(
            user_id=current_user.id,
            doc_type=doc_type,
            filename=filename,
            content_type=file.content_type or "application/octet-stream",
            file_data=b"", # Placeholder
            encryption_nonce=encrypted["nonce"],
            is_encrypted=True,
        )
        db.add(new_doc)

    db.commit()
    logger.info(f"[/api/upload_document] {doc_type} saved and hashed for user: {current_user.email}")
    return {"success": True, "message": f"{doc_type.capitalize()} uploaded and secured with blockchain integrity!"}


@app.get("/api/verify_integrity/{doc_type}")
async def verify_document_integrity(
    doc_type: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Verify the integrity of a document by comparing its current hash
    with the hash stored on the simulated blockchain.
    """
    doc = db.query(Document).filter(
        Document.user_id == current_user.id,
        Document.doc_type == doc_type
    ).first()

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    file_path = os.path.join(UPLOAD_DIR, str(current_user.id), f"{doc_type}.enc")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Physical file missing.")

    with open(file_path, "rb") as f:
        ciphertext = f.read()

    # Decrypt to get raw bytes for hashing
    try:
        plaintext = decrypt_document(ciphertext, doc.encryption_nonce)
        # Use blockchain service to verify
        result = verify_integrity(db, current_user.id, doc_type, plaintext)
    except Exception as e:
        logger.error(f"Decryption failed during integrity check: {e}")
        # If decryption fails, the file is definitely tampered or corrupted
        result = {
            "authentic": False,
            "error": "Decryption failed - Document content is corrupted or tampered.",
            "current_hash": "ERROR",
            "stored_hash": db.query(BlockchainRecord).filter(
                BlockchainRecord.user_id == current_user.id,
                BlockchainRecord.doc_type == doc_type
            ).first().doc_hash
        }
    
    logger.info(f"[/api/verify_integrity] Verified {doc_type} for user {current_user.email}: Authentic={result['authentic']}")
    return result


@app.get("/api/view_document/{doc_type}")
async def view_document(
    doc_type: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """View an uploaded document (decrypt on the fly)."""
    doc = db.query(Document).filter(
        Document.user_id == current_user.id,
        Document.doc_type == doc_type
    ).first()

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    file_path = os.path.join(UPLOAD_DIR, str(current_user.id), f"{doc_type}.enc")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Physical file missing.")

    with open(file_path, "rb") as f:
        ciphertext = f.read()

    plaintext = decrypt_document(ciphertext, doc.encryption_nonce)
    
    return StreamingResponse(
        io.BytesIO(plaintext),
        media_type=doc.content_type
    )


@app.get("/api/download_document/{doc_type}")
async def download_document(
    doc_type: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Download an uploaded document."""
    doc = db.query(Document).filter(
        Document.user_id == current_user.id,
        Document.doc_type == doc_type
    ).first()

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    file_path = os.path.join(UPLOAD_DIR, str(current_user.id), f"{doc_type}.enc")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Physical file missing.")

    with open(file_path, "rb") as f:
        ciphertext = f.read()

    plaintext = decrypt_document(ciphertext, doc.encryption_nonce)
    
    # Use double quotes for filename in Content-Disposition to handle spaces
    headers = {
        "Content-Disposition": f'attachment; filename="{doc.filename}"',
        "Access-Control-Expose-Headers": "Content-Disposition"
    }
    
    return StreamingResponse(
        io.BytesIO(plaintext),
        media_type=doc.content_type,
        headers=headers
    )


@app.get("/api/user_documents")
def get_user_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List document types already uploaded by the user."""
    docs = db.query(Document).filter(Document.user_id == current_user.id).all()
    return {
        "uploaded_types": [d.doc_type for d in docs]
    }


@app.post("/api/login")
def login(request: LoginRequest, db: Session = Depends(get_db)):
    """Authenticate user and return JWT token."""
    email = request.email.strip().lower()

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=401, detail="Account not found. Please register first.")

    if not verify_password(request.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect password. Please try again.")

    token = create_access_token(user.id, user.email)

    logger.info(f"[/api/login] User logged in: {email}")
    return {
        "success": True,
        "token": token,
        "user": {
            "name": user.name,
            "email": user.email,
            "phone": user.phone,
        },
    }


@app.get("/api/me")
def get_me(current_user: User = Depends(get_current_user)):
    """Protected endpoint: returns current user details."""
    return {
        "id": current_user.id,
        "name": current_user.name,
        "email": current_user.email,
        "phone": current_user.phone,
    }


# ===== EXISTING ENDPOINTS =====

# --- Legacy Endpoint ---

@app.post("/ask")
def ask(request: QueryRequest):
    """Legacy endpoint using Ollama LLM."""
    response = civic_assist(request.question)
    return {"response": response}


# --- Tax Question Pipeline ---

@app.post("/api/ask_tax_question")
def ask_tax_question(request: QueryRequest):
    """Query → Classification → Retrieval → Structured Response (no LLM)."""
    retrieval_result = retrieve(request.question)
    response = build_response(retrieval_result)

    log_pipeline_event(
        query=request.question,
        query_type=response["query_type"],
        num_docs=len(retrieval_result["documents"]),
        response_preview=response["explanation"],
    )
    return response


# --- Government Notice Explanation Pipeline ---

@app.post("/api/explain_notice")
async def explain_notice_endpoint(file: UploadFile = File(...)):
    """
    Full pipeline:
      Upload (PDF/PNG/JPG) → Text Extraction → Department Classification
      → Notice Type Detection → Knowledge Retrieval → Structured Explanation
    """
    # Step 1: Read file
    file_bytes = await file.read()
    content_type = file.content_type or ""
    filename = file.filename or "unknown"

    logger.info(f"[/explain_notice] File received: {filename} ({content_type})")

    # Step 2: Extract text
    processed = process_file(file_bytes, content_type, filename)
    if processed.get("error"):
        return {"error": processed["error"]}

    raw_text = processed["raw_text"]
    logger.info(f"[/explain_notice] Extracted {len(raw_text)} chars from {processed['file_type']}")

    # Step 3: Classify department + notice type
    classification = classify_document(raw_text)
    department = classification["department"]
    notice_type = classification["notice_type"]
    logger.info(f"[/explain_notice] Department: {department}, Notice: {notice_type}")

    # Step 4: Generate explanation
    response = explain_notice(raw_text, department, notice_type)

    # Step 5: Log
    log_pipeline_event(
        query=f"[Notice Upload] {filename}",
        query_type=f"{department}/{notice_type}",
        num_docs=len(response.get("sources", [])),
        response_preview=response.get("explanation", ""),
    )

    return response


# --- EPFO PF Withdrawal Extension ---

@app.get("/api/epfo/user-info")
async def get_epfo_user_info(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieve Name and DOB from uploaded Aadhaar or PAN."""
    # Find Aadhaar first, then PAN
    doc = db.query(Document).filter(
        Document.user_id == current_user.id,
        Document.doc_type == "aadhaar"
    ).first()
    
    if not doc:
        doc = db.query(Document).filter(
            Document.user_id == current_user.id,
            Document.doc_type == "pan"
        ).first()
        
    if not doc:
        # Fallback to User model data if no documents uploaded
        return {
            "name": current_user.name,
            "dob": "Not available (Please upload Aadhaar/PAN)",
            "source": "registration"
        }

    # Decrypt and extract
    file_path = os.path.join(UPLOAD_DIR, str(current_user.id), f"{doc.doc_type}.enc")
    if not os.path.exists(file_path):
        return {"name": current_user.name, "dob": "File missing", "source": "error"}

    with open(file_path, "rb") as f:
        ciphertext = f.read()
    
    plaintext = decrypt_document(ciphertext, doc.encryption_nonce)
    info = extract_info_from_doc(plaintext, doc.doc_type)
    
    return {
        "name": info.get("name") or current_user.name,
        "dob": info.get("dob") or "Not found in document",
        "source": doc.doc_type
    }

@app.post("/api/epfo/verify-passbook")
async def verify_passbook(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Verify uploaded UAN passbook against Aadhaar/PAN data with robust checks."""
    from backend.services.identity_service import normalize_name, normalize_dob
    
    file_bytes = await file.read()
    
    # 1. Extract info from passbook
    pb_info = extract_uan_from_passbook(file_bytes)
    pb_name_norm = normalize_name(pb_info["name"])
    pb_dob_norm = normalize_dob(pb_info["dob"])
    
    # 2. Get baseline info from all uploaded documents
    docs = db.query(Document).filter(
        Document.user_id == current_user.id,
        Document.doc_type.in_(["aadhaar", "pan"])
    ).all()
    
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
        # Fallback to registration data
        baselines.append({
            "name": normalize_name(current_user.name),
            "dob": None,
            "source": "registration"
        })

    # 3. Compare
    name_mismatch = False
    dob_mismatch = False
    
    # Name Check: Check if passbook name words match ANY baseline words
    # (Handling reversed names via set comparison)
    if pb_name_norm:
        matched_any_name = False
        for bl in baselines:
            if pb_name_norm == bl["name"]:
                matched_any_name = True
                break
        if not matched_any_name:
            name_mismatch = True
    else:
        name_mismatch = True # Could not extract name from passbook

    # DOB Check: Check if passbook DOB matches ANY baseline DOB (if available)
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
        # We have a DOB in records but failed to extract or find a match
        dob_mismatch = True

    # 4. Results
    issues = []
    if name_mismatch:
        issues.append("Name mismatch between UAN and Aadhaar/PAN")
    if dob_mismatch:
        issues.append("Date of Birth mismatch")
        
    status = "Verified Successfully" if not issues else "Issues Detected"
    
    if is_success := (not issues):
        fix = "You can proceed with the PF claim."
    else:
        fix = "Please update KYC details in the EPFO portal before submitting the claim."

    return {
        "status": status,
        "problems_found": issues,
        "suggested_fix": fix,
        "extracted_details": pb_info
    }


# Keep old endpoint for backward compat
@app.post("/explain_tax_notice")
async def explain_tax_notice(file: UploadFile = File(...)):
    """Backward-compatible tax notice endpoint — delegates to /explain_notice."""
    return await explain_notice_endpoint(file)


# Mount frontend (must be last)
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
