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
        "department": "Income Tax Department",
        "seriousness": "Medium (Informational or Demand)",
        "explanation": "Demand/Refund notice after processing",
        "forms": ["ITR computation response"],
        "download_links": ["https://www.incometax.gov.in/downloads"],
        "action_site": "https://eportal.incometax.gov.in/iec/foservices/"
    },
    "139(9)": {
        "name": "Defective Return Notice",
        "department": "Income Tax Department",
        "seriousness": "High (Action Required)",
        "explanation": "Return is defective, needs correction",
        "forms": ["Revised ITR"],
        "download_links": ["https://www.incometax.gov.in/downloads"],
        "action_site": "https://eportal.incometax.gov.in/iec/foservices/"
    },
    "148": {
        "name": "Reassessment Notice",
        "department": "Income Tax Department",
        "seriousness": "Critical (Investigation)",
        "explanation": "Income escaped assessment",
        "forms": ["Response to 148"],
        "download_links": ["https://www.incometax.gov.in/downloads"],
        "action_site": "https://eportal.incometax.gov.in/iec/foservices/"
    },
    # EPFO Rejections
    "claim_rejected": {
        "name": "EPFO Claim Rejection",
        "department": "EPFO (Employees' Provident Fund Organization)",
        "seriousness": "Medium (Financial Delay)",
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
        "department": "EPFO",
        "seriousness": "Medium (Action Required for Withdrawal)",
        "explanation": "UAN KYC incomplete",
        "forms": ["KYC Update"],
        "download_links": ["https://unifiedportal-mem.epfindia.gov.in/memberinterface/"],
        "action_site": "https://unifiedportal-mem.epfindia.gov.in/memberinterface/"
    },
    # Passport
    "passport_delay": {
        "name": "Passport Application Delay/Hold",
        "department": "Passport Seva (MEA)",
        "seriousness": "High (Travel Impact)",
        "explanation": "Passport application held due to incomplete documents or police verification",
        "forms": ["Document Submission Form"],
        "download_links": ["https://www.passportindia.gov.in"],
        "action_site": "https://portal2.passportindia.gov.in/"
    },
    "penalty_271": {
        "name": "Penalty Notice u/s 271(1)(c)",
        "department": "Income Tax Department",
        "seriousness": "Critical (Financial Penalty)",
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
You are the "CivicAssist Notice Intelligence Engine". 
Government portals show notices but do not interpret them deeply. Your job is deep notice reasoning.

Analyze this government notice text. 
Extracted text: {extracted_text}

Classified as: {notice_type}
Official registry hints: {registry}
CONTEXT from knowledge base: {context}

════════════════════════════════════════════════════════════════════════════════
OUTPUT SCHEMA (MANDATORY JSON):
{{
  "notice_type": "{notice_type}",
  "department": "The specific government wing (e.g. Income Tax CPC, EPFO Gwalior, etc.)",
  "urgency": "normal / attention / urgent / critical",
  "severity_index": "Low / Medium / High / Critical",
  "deadline": "Extract deadline date (e.g. 15 days or 31/03/2024). Calculate if relative.",
  "risk_analysis": "Deep analysis of the risk if this notice is ignored. What is the legal/financial impact?",
  "consequence": "Direct outcome (e.g. Return invalid, Penalty of INR 5000, Application cancelled)",
  "explanation": "Simple summary for a common person (1-2 sentences)",
  "strategy": "Strategic action plan to resolve this perfectly. Not just steps, but 'Strategy'.",
  "steps": ["Action 1", "Action 2", "..."],
  "forms_needed": ["Names of forms or actions (e.g. Revised ITR u/s 139(5))"],
  "official_links": ["Link to the portal for taking action"],
  "helpline": "Relevant contact number"
}}

Return ONLY valid JSON.
"""
