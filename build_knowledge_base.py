import os
import re
import requests
import logging
import time
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constants
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
TIMEOUT = 15
RETRIES = 3

# Mapping of file keywords to search terms and start URLs
TOPIC_MAP = {
    "epfo": {
        "url": "https://www.epfindia.gov.in/site_en/Index.php",
        "keywords": ["withdrawal", "kyc", "nominee", "transfer", "claim", "rejection", "grievance", "support", "faq"]
    },
    "passport": {
        "url": "https://www.passportindia.gov.in/AppOnlineProject/welcomeLink",
        "keywords": ["application", "documents", "verification", "delay", "lost", "renewal", "fee", "reissue", "grievance", "faq"]
    },
    "income_tax": {
        "url": "https://www.incometax.gov.in/iec/foportal/",
        "keywords": ["itr", "filing", "refund", "deduction", "notice", "143", "148", "grievance", "faq"]
    },
    "aadhaar": {
        "url": "https://uidai.gov.in/",
        "keywords": ["enrollment", "address", "mobile", "correction", "lost", "download", "linking", "faq"]
    },
    "pan": {
        "url": "https://www.onlineservices.nsdl.com/paam/endUserRegisterContact.html",
        "keywords": ["application", "correction", "lost", "link", "status", "faq"]
    },
    "voter": {
        "url": "https://voters.eci.gov.in/",
        "keywords": ["application", "correction", "address", "status", "faq"]
    },
    "license": {
        "url": "https://parivahan.gov.in/parivahan/",
        "keywords": ["application", "learner", "renewal", "duplicate", "test", "faq"]
    }
}

def fetch_page(url):
    """Fetch HTML content with retries and timeout."""
    headers = {"User-Agent": USER_AGENT}
    for attempt in range(RETRIES):
        try:
            logger.info(f"Fetching data from {url} (Attempt {attempt+1})")
            response = requests.get(url, headers=headers, timeout=TIMEOUT)
            response.raise_for_status()
            return response.text
        except requests.exceptions.RequestException as e:
            logger.warning(f"Error fetching {url}: {e}")
            if attempt < RETRIES - 1:
                time.sleep(2 ** attempt)
    return None

def clean_text(html_content):
    """Extract meaningful text and clean whitespace."""
    if not html_content:
        return ""
    
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Remove unwanted elements
    for script_or_style in soup(["script", "style", "header", "footer", "nav", "aside"]):
        script_or_style.decompose()
        
    text = soup.get_text(separator='\n')
    
    # Clean whitespace
    lines = (line.strip() for line in text.splitlines())
    # Remove short lines and navigation remnants
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    cleaned_text = '\n'.join(chunk for chunk in chunks if len(chunk) > 30)
    
    return cleaned_text

def extract_sections(text, filename, folder_name):
    """Structure the text into the requested format."""
    # Basic logic to split text into sections based on headers or keywords if found
    # For now, we'll create a structured response with available info
    
    service_name = filename.replace('_', ' ').replace('.txt', '').title()
    department = folder_name.upper()
    
    sections = {
        "SERVICE NAME": service_name,
        "DEPARTMENT": department,
        "DESCRIPTION": "Auto-extracted information about " + service_name,
        "PROCESS": "Information extracted from official portal. See sections below.",
        "REQUIRED DOCUMENTS": "Please refer to the official portal links provided.",
        "COMMON PROBLEMS": "Details found in FAQ sections of the portal.",
        "SOLUTION": "Check the grievance system or contact support.",
        "EXPECTED TIMELINE": "Varies by state/service. Check service timelines.",
        "OFFICIAL PORTAL": TOPIC_MAP.get(folder_name, {}).get("url", "https://india.gov.in")
    }
    
    # Rudimentary logic to fill sections from text
    if text:
        # Example: look for keywords to populate DESCRIPTION or PROCESS
        # This is a placeholder for more advanced NLP/Regex logic
        sections["DESCRIPTION"] = text[:1000] + "..." if len(text) > 1000 else text
        
    output = ""
    for header, content in sections.items():
        output += f"{header}\n{'-'*len(header)}\n{content}\n\n"
    
    return output

def download_pdfs(html_content, base_url, target_dir):
    """Find and download PDF links in the content."""
    if not html_content:
        return
    
    soup = BeautifulSoup(html_content, 'html.parser')
    for link in soup.find_all('a', href=re.compile(r'\.pdf$')):
        pdf_url = urljoin(base_url, link.get('href'))
        pdf_name = os.path.basename(urlparse(pdf_url).path)
        pdf_path = os.path.join(target_dir, pdf_name)
        
        if not os.path.exists(pdf_path):
            try:
                logger.info(f"Downloading form: {pdf_name}")
                headers = {"User-Agent": USER_AGENT}
                r = requests.get(pdf_url, headers=headers, stream=True, timeout=TIMEOUT)
                r.raise_for_status()
                with open(pdf_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
            except Exception as e:
                logger.error(f"Failed to download {pdf_url}: {e}")

def process_directory(root_dir):
    """Recursively process empty files in the knowledge base."""
    for subdir, dirs, files in os.walk(root_dir):
        folder_name = os.path.basename(subdir)
        for file in files:
            if file.endswith(".txt"):
                file_path = os.path.join(subdir, file)
                
                # Check if file is empty
                if os.path.getsize(file_path) == 0:
                    logger.info(f"Processing {folder_name}/{file}")
                    
                    # Determine source URL based on folder and filename
                    source_info = TOPIC_MAP.get(folder_name)
                    if not source_info:
                        # Fallback for general folders
                        source_url = "https://www.india.gov.in/gsearch?s=" + file.replace(".txt", "")
                    else:
                        source_url = source_info["url"]
                    
                    # In a real scenario, we might want to search specifically for the file's topic
                    # For this script, we'll fetch the main page or search page
                    html = fetch_page(source_url)
                    
                    if html:
                        # Extract PDFs/Forms first
                        download_pdfs(html, source_url, subdir)
                        
                        # Clean and structure text
                        raw_text = clean_text(html)
                        content = extract_sections(raw_text, file, folder_name)
                        
                        # Write to file
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(content)
                        logger.info(f"Writing content to {file}")
                    else:
                        logger.warning(f"Could not fetch data for {file}")

if __name__ == "__main__":
    KB_ROOT = os.path.join(os.getcwd(), "knowledge_base")
    if not os.path.exists(KB_ROOT):
        logger.error(f"Knowledge base directory not found at {KB_ROOT}")
    else:
        logger.info("Starting knowledge base population...")
        process_directory(KB_ROOT)
        logger.info("Knowledge base population complete.")
