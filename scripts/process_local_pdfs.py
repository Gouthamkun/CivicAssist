import os
import json
import time
import requests
import fitz  # PyMuPDF
from tqdm import tqdm

DOMAIN = "epfo"
PDF_DIR = "epfo_pdfs"
OUTPUT_DIR = os.path.join("knowledge_base", DOMAIN)
OLLAMA_API_URL = "http://127.0.0.1:11434/api/generate"
MODEL = "llama3"

# Ensure output directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

def extract_text_from_pdf(pdf_path, max_pages=15):
    """Extracts text from a PDF. Limits to `max_pages` for LLM context window safety."""
    text = ""
    try:
        doc = fitz.open(pdf_path)
        num_pages = min(len(doc), max_pages)
        for i in range(num_pages):
            text += doc[i].get_text() + "\n"
        return text.strip()
    except Exception as e:
        print(f"Error reading {pdf_path}: {e}")
        return ""

def ask_ollama_to_categorize(text, filename):
    """Asks Ollama to determine the category and a strict, clean title for the document."""
    # We only send the first ~2000 characters to the LLM to save time and VRAM since
    # the title and purpose of Gov docs are usually on the first page.
    prompt = f"""
Analyze the following text extracted from an Indian Government EPFO document named '{filename}'.
Categorize it into exactly one of these categories: 'rules', 'manual', 'circular', 'faq', 'form', 'general'.
Also, generate a clean, human-readable Title for this document.

Respond EXACTLY in this JSON format, nothing else:
{{"category": "category_name", "title": "Document Title"}}

Document Text snippet:
{text[:2000]}
"""

    try:
        response = requests.post(OLLAMA_API_URL, json={
            "model": MODEL,
            "prompt": prompt,
            "stream": False,
            "format": "json"
        }, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            return json.loads(data["response"])
    except Exception as e:
        print(f"  [!] Ollama API Error on {filename}: {e}")
    
    # Fallback if LLM fails
    return {"category": "general", "title": filename.replace(".pdf", "").replace("_", " ")}


def save_rag_text(filename, category, title, content):
    """Saves the extracted text into the structured RAG format."""
    base_name = filename.replace(".pdf", "")
    out_path = os.path.join(OUTPUT_DIR, f"{base_name}.txt")
    
    formatted_content = f"""---
SOURCE: local_offline_pdf
DOMAIN: {DOMAIN}
CATEGORY: {category}
LAST_UPDATED: {time.strftime('%Y-%m-%d')}
LANGUAGE: English
---

[{title}]

[CONTENT]
{content}

[FORMS_REFERENCED]
None

[RELATED_QUERIES]
None
---
"""
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(formatted_content)


def process_pdfs():
    if not os.path.exists(PDF_DIR):
        print(f"Directory {PDF_DIR} does not exist.")
        return

    pdf_files = [f for f in os.listdir(PDF_DIR) if f.lower().endswith(".pdf")]
    print(f"Found {len(pdf_files)} PDF files in {PDF_DIR}. Starting extraction...")

    for file in tqdm(pdf_files):
        pdf_path = os.path.join(PDF_DIR, file)
        
        print(f"\nProcessing: {file}")
        
        # 1. Extract text (limited to 50 pages max so we don't blow up text files)
        extracted_text = extract_text_from_pdf(pdf_path, max_pages=50)
        
        if not extracted_text:
            print(f"  [-] Skipped {file}: No text extracted.")
            continue
            
        # 2. Ask Ollama to classify it based on the first page
        meta = ask_ollama_to_categorize(extracted_text, file)
        category = meta.get("category", "general")
        title = meta.get("title", file)
        
        print(f"  [+] Classified as: [{category}] {title}")
        
        # 3. Save to knowledge base
        save_rag_text(file, category, title, extracted_text)

    print("\n✅ All PDFs processed and segregated into knowledge_base/epfo/")

if __name__ == "__main__":
    process_pdfs()
