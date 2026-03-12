import easyocr
import cv2
import numpy as np
import fitz  # PyMuPDF
import json
import ollama

# Initialize EasyOCR Reader (English + Hindi)
# Using lazy load so it doesn't crash on import if weights take a second
reader = None

def get_reader():
    global reader
    if reader is None:
        reader = easyocr.Reader(['en', 'hi'])
    return reader

NOTICE_REGISTRY = {
    # Tax Notices
    "143(1)": {
        "name": "Intimation u/s 143(1)",
        "explanation": "Demand/Refund notice after processing",
        "forms": ["ITR computation response"],
        "download_links": ["https://www.incometax.gov.in/downloads"],
        "action_site": "https://eportal.incometax.gov.in/iec/foservices/"
    },
    "139(9)": {
        "name": "Defective Return Notice",
        "explanation": "Return is defective, needs correction",
        "forms": ["Revised ITR"],
        "download_links": ["https://www.incometax.gov.in/downloads"],
        "action_site": "https://eportal.incometax.gov.in/iec/foservices/"
    },
    "148": {
        "name": "Reassessment Notice",
        "explanation": "Income escaped assessment",
        "forms": ["Response to 148"],
        "download_links": ["https://www.incometax.gov.in/downloads"],
        "action_site": "https://eportal.incometax.gov.in/iec/foservices/"
    },
    # EPFO Rejections
    "claim_rejected": {
        "name": "EPFO Claim Rejection",
        "explanation": "PF/Pension claim rejected",
        "forms": ["Form 19", "Form 10C", "Form 31"],
        "download_links": [
            "https://www.epfindia.gov.in/site_docs/PDFs/Downloads_PDFs/Form19.pdf",
            "https://www.epfindia.gov.in/site_docs/PDFs/Downloads_PDFs/Form10C.pdf"
        ],
        "action_site": "https://unifiedportal-mem.epfindia.gov.in/memberinterface/"
    },
    "kyc_pending": {
        "name": "KYC Pending Rejection",
        "explanation": "UAN KYC incomplete",
        "forms": ["KYC Update"],
        "download_links": ["https://unifiedportal-mem.epfindia.gov.in/memberinterface/"],
        "action_site": "https://unifiedportal-mem.epfindia.gov.in/memberinterface/"
    },
    # Passport
    "passport_delay": {
        "name": "Passport Application Delay/Hold",
        "explanation": "Passport application held due to incomplete documents or police verification",
        "forms": ["Document Submission Form"],
        "download_links": ["https://www.passportindia.gov.in"],
        "action_site": "https://portal2.passportindia.gov.in/"
    },
    "penalty_271": {
        "name": "Penalty Notice u/s 271(1)(c)",
        "explanation": "Notice for imposing penalty for concealment of income or furnishing inaccurate particulars.",
        "forms": ["Penalty Response"],
        "download_links": ["https://eportal.incometax.gov.in"],
        "action_site": "https://www.incometax.gov.in/iec/foportal/"
    }
}

def preprocess_image(image_bytes):
    """Enhance blurry/low-quality notice photos"""
    try:
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None:
            return image_bytes
            
        # Denoise + Sharpen
        img = cv2.fastNlMeansDenoisingColored(img, None, 10, 10, 7, 21)
        kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
        img = cv2.filter2D(img, -1, kernel)
        
        # Contrast enhance
        img = cv2.convertScaleAbs(img, alpha=1.2, beta=10) # Slightly less aggressive
        
        # Deskew (fix rotation)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        # Threshold to find text areas
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        coords = np.column_stack(np.where(thresh > 0))
        
        if len(coords) > 0:
            angle = cv2.minAreaRect(coords)[-1]
            if angle < -45:
                angle = -(90 + angle)
            else:
                angle = -angle
            
            if abs(angle) > 0.5: # Only rotate if significant
                (h, w) = img.shape[:2]
                center = (w // 2, h // 2)
                M = cv2.getRotationMatrix2D(center, angle, 1.0)
                img = cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
        
        return cv2.imencode('.jpg', img)[1].tobytes()
    except Exception as e:
        print(f"Preprocessing failed: {e}")
        return image_bytes

def extract_text(content: bytes, content_type: str):
    """OCR for image or PDF"""
    if "pdf" in content_type.lower():
        # PDF: Use PyMuPDF (faster/more accurate than OCR)
        doc = fitz.open(stream=content, filetype="pdf")
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
    else:
        # Image: Pre-process + EasyOCR
        r = get_reader()
        
        # Try with enhanced image
        enhanced = preprocess_image(content)
        result = r.readtext(enhanced, detail=0, paragraph=True)
        text = ' '.join(result)
        
        # Fallback to raw if enhanced failed to find text
        if len(text.strip()) < 10:
            result = r.readtext(content, detail=0, paragraph=True)
            text = ' '.join(result)
            
    return text.strip()

def classify_notice(text):
    """Hybrid classification"""
    text_lower = text.lower()
    
    # Keyword first pass
    for notice_type, data in NOTICE_REGISTRY.items():
        if any(kw in text_lower for kw in [notice_type, data["name"].lower()]):
            return notice_type
            
    if "reject" in text_lower and ("pf" in text_lower or "epf" in text_lower):
        return "claim_rejected"
        
    if "passport" in text_lower and "delay" in text_lower:
        return "passport_delay"
    
    # LLM refinement (fallback)
    prompt = f"Classify this notice/document: {text[:500]} Possible: {list(NOTICE_REGISTRY.keys())} or unknown."
    try:
        resp = ollama.chat(model="llama3", messages=[{"role":"user", "content":prompt}])
        content = resp["message"]["content"].strip().lower()
        for k in NOTICE_REGISTRY.keys():
            if k in content:
                return k
    except:
        pass
    return "unknown"

ENHANCED_NOTICE_PROMPT = """
Explain this government notice. Extracted text: {extracted_text}

Classified as: {notice_type}

Official registry: {registry}

CONTEXT from knowledge base: {context}

════════════════════════════════════════════════════════════════════════════════
OUTPUT SCHEMA (MANDATORY):
{{
  "notice_type": "{notice_type}",
  "urgency": "normal / attention / urgent",
  "deadline": "DD/MM/YYYY or N/A",
  "explanation": "What this means in simple words (1-2 sentences)",
  "why_received": "Common reasons or exact reasons if explicitly mentioned",
  "steps": ["Step 1...", "Step 2..."],
  "forms_needed": ["Link to specific specific form / action needed"],
  "official_links": ["Link to official portal (from registry)"],
  "what_if_ignore": "Consequences",
  "helpline": "1800-103-0025 (IT) / 1800-118-005 (EPFO) / 1800-258-1800 (Passport)"
}}

Return ONLY valid JSON.
"""
