import os
import fitz  # PyMuPDF
from tqdm import tqdm

DOMAIN = "epfo"
PDF_DIR = "frontend/forms"
OUTPUT_DIR = os.path.join("knowledge_base", DOMAIN, "processed_forms")

# Ensure output directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

def extract_text_from_pdf(pdf_path):
    """Extracts all text from a PDF form."""
    text = ""
    try:
        doc = fitz.open(pdf_path)
        for i in range(len(doc)):
            text += doc[i].get_text() + "\n"
        return text.strip()
    except Exception as e:
        print(f"Error reading {pdf_path}: {e}")
        return ""

def save_rag_text(filename, content):
    """Saves the extracted form text into the structured RAG format."""
    base_name = filename.replace(".pdf", "")
    out_path = os.path.join(OUTPUT_DIR, f"{base_name}.txt")
    
    formatted_content = f"""---
SOURCE: local_offline_form_pdf
DOMAIN: {DOMAIN}
CATEGORY: form_instructions
---

[{base_name} Official Form Instructions]

[CONTENT]
{content}

[FORMS_REFERENCED]
If the user needs to download this form, you MUST provide them with this exact action:
Action Label: Download {base_name} Form
Action URL: forms/{filename}
"""
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(formatted_content)

def process_forms():
    if not os.path.exists(PDF_DIR):
        print(f"Directory {PDF_DIR} does not exist.")
        return

    pdf_files = [f for f in os.listdir(PDF_DIR) if f.lower().endswith(".pdf")]
    print(f"Found {len(pdf_files)} PDF forms in {PDF_DIR}. Starting extraction...")

    for file in tqdm(pdf_files):
        pdf_path = os.path.join(PDF_DIR, file)
        
        print(f"\nProcessing Form: {file}")
        
        # Extract text (Forms contain critical instructions for the AI)
        extracted_text = extract_text_from_pdf(pdf_path)
        
        if not extracted_text:
            print(f"  [-] Warning: {file} contains no readable text (likely a scanned image). Injecting bare metadata framework.")
            extracted_text = f"This document is the official government form for {file.replace('.pdf', '')}."
            
        print(f"  [+] Saved explicit form instructions for {file}")
        
        # Save to knowledge base
        save_rag_text(file, extracted_text)

    print("\n✅ All form PDFs processed and segregated into knowledge_base/epfo/processed_forms/")

if __name__ == "__main__":
    process_forms()
