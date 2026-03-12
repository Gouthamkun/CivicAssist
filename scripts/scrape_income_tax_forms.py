import os
import json
import logging
import requests
import time
import random
from urllib.parse import urljoin, urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constants
BASE_URL = "https://incometaxindia.gov.in/Pages/downloads/forms.aspx"
MAX_PAGES = 37 # User specified
DATASET_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dataset", "income_tax_forms")
MAX_WORKERS = 5 # Number of parallel threads

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
}

def create_directory(path):
    """Creates a directory if it does not exist."""
    if not os.path.exists(path):
        os.makedirs(path)

def setup_driver():
    """Initializes a headless Selenium Chrome WebDriver."""
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument(f"user-agent={HEADERS['User-Agent']}")
    
    # Enable automatic downloads without prompting
    prefs = {
        "download.default_directory": DATASET_DIR,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "plugins.always_open_pdf_externally": True # Download PDFs instead of viewing
    }
    options.add_experimental_option("prefs", prefs)
    options.add_experimental_option('excludeSwitches', ['enable-logging'])
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.set_page_load_timeout(30)
    return driver

def save_metadata(form_name, description, filename, folder_path):
    """Saves the metadata.json inside the specific form folder."""
    metadata_path = os.path.join(folder_path, "metadata.json")
    
    clean_data = {
        "form_name": form_name.strip(),
        "description": description.replace(" | ", " ").strip(),
        "source": "Income Tax India",
        "filename": filename,
        "category": "income_tax_form"
    }
    
    with open(metadata_path, 'w', encoding='utf-8') as f:
        json.dump(clean_data, f, indent=4, ensure_ascii=False)

def crawl_and_download():
    """Main crawler entry point using human click emulation."""
    logger.info("Starting Selenium Income Tax Forms Crawler...")
    create_directory(DATASET_DIR)
    
    driver = None
    successful_downloads = 0
    total_forms_found = 0
    
    try:
        driver = setup_driver()
        logger.info("Navigating to the Income Tax Forms Portal...")
        
        # Load the initial base page
        driver.get(BASE_URL)
        
        for page in tqdm(range(1, MAX_PAGES + 1), desc="Navigating Pages"):
            logger.info(f"--- Processing Page {page} ---")
            
            try:
                # Wait for the forms container to load
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Form No.')]"))
                )
                time.sleep(3) # Let all JS bundles properly map the onclicks
            except Exception:
                logger.warning(f"Timeout waiting for elements on page {page}. Trying to proceed anyway...")

            # Parse DOM once per page to understand how many forms are visible
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            
            # Find all visible PDF download links
            pdf_buttons = driver.find_elements(By.XPATH, "//a[contains(text(), 'PDF') or contains(@class, 'form-pdf-icon') or contains(@class, 'pdf')]")
            
            if not pdf_buttons:
                logger.warning("No PDF buttons found on this page! DOM may have shifted.")
                
            for button_index in range(len(pdf_buttons)):
                # Re-fetch the elements in case DOM refreshed after a click
                try:
                    current_buttons = driver.find_elements(By.XPATH, "//a[contains(text(), 'PDF') or contains(@class, 'form-pdf-icon') or contains(@class, 'pdf')]")
                    if button_index >= len(current_buttons):
                        continue
                        
                    btn = current_buttons[button_index]
                    
                    # Ensure it's not a hidden button
                    if not btn.is_displayed():
                        continue
                        
                    # Extract Form Name and Description before clicking
                    # We climb the DOM tree to find the parent container 
                    parent = btn.find_element(By.XPATH, "..")
                    for _ in range(4): # climb up to 4 levels looking for recognizable text
                        text = parent.text
                        if 'Form' in text and len(text) > 15:
                            break
                        try:
                            parent = parent.find_element(By.XPATH, "..")
                        except:
                            break
                            
                    context_text = parent.text
                    lines = [line.strip() for line in context_text.split('\n') if line.strip() and 'PDF' not in line and 'Fillable Form' not in line]
                    
                    form_name = lines[0] if lines else f"Unknown_Form_Pg{page}_Idx{button_index}"
                    description = " ".join(lines[1:]) if len(lines) > 1 else "Income Tax Form"
                    
                    if len(form_name) > 50: # fallback if it grabbed too much
                        form_name = f"Form_Pg{page}_Idx{button_index}"
                        
                    safe_form_name = "".join([c if c.isalnum() else "_" for c in form_name]).strip("_")
                    folder_path = os.path.join(DATASET_DIR, safe_form_name)
                    create_directory(folder_path)
                    
                    # Track files before click
                    files_before = set(os.listdir(DATASET_DIR))
                    
                    # Click using JS to avoid elements overlapping interception
                    driver.execute_script("arguments[0].click();", btn)
                    total_forms_found += 1
                    logger.info(f"Clicked download for: {form_name}")
                    
                    # Wait for Chrome to physically drop the file into the dataset dir
                    wait_time = 0
                    success = False
                    downloaded_temp_path = None
                    
                    while wait_time < 15:
                        files_after = set(os.listdir(DATASET_DIR))
                        new_files = files_after - files_before
                        
                        # Filter out chrome temporary download files
                        valid_new_files = [f for f in new_files if not f.endswith('.crdownload') and not f.endswith('.tmp')]
                        
                        if valid_new_files:
                            filename = valid_new_files[0]
                            downloaded_temp_path = os.path.join(DATASET_DIR, filename)
                            file_path = os.path.join(folder_path, filename)
                            
                            try:
                                # Move it from root dataset folder to the specific form folder
                                os.replace(downloaded_temp_path, file_path)
                                save_metadata(form_name, description, filename, folder_path)
                                success = True
                                successful_downloads += 1
                                logger.info(f"Successfully saved {filename}")
                                break
                            except PermissionError:
                                # File is still being written by Chrome
                                pass
                        time.sleep(1)
                        wait_time += 1
                        
                    if not success:
                        logger.warning(f"Download timeout or failure for {form_name}")
                        
                    time.sleep(random.uniform(1.0, 2.0))
                    
                except Exception as e:
                    logger.error(f"Error clicking button {button_index} on page {page}: {e}")
                    
            # Navigate to the Next Page
            if page < MAX_PAGES:
                try:
                    # Find pagination buttons
                    pagination = driver.find_elements(By.XPATH, "//a[contains(@class, 'paginate_button') or contains(text(), 'Next') or contains(text(), '>')]")
                    
                    # Often it's an arrow icon or > symbol. Let's try to find an anchor with title "Next Page" or text containing >
                    next_buttons = driver.find_elements(By.XPATH, "//a[@title='Next Page' or contains(text(), '>')]")
                    
                    if next_buttons:
                        driver.execute_script("arguments[0].click();", next_buttons[0])
                        logger.info("Clicked Pagination: Next Page")
                        time.sleep(3) # Wait for SPA transition
                    else:
                        logger.warning("Could not find the 'Next' pagination button! Crawler might be stuck.")
                        break
                        
                except Exception as e:
                    logger.error(f"Failed to click next page: {e}")
                    break

        logger.info("====================================")
        logger.info("Income Tax Crawler Finished!")
        logger.info(f"Forms Encountered: {total_forms_found}")
        logger.info(f"Successfully Downloaded: {successful_downloads}")
        logger.info(f"Dataset securely saved to: {DATASET_DIR}")

    finally:
        if driver:
            driver.quit()

if __name__ == "__main__":
    crawl_and_download()
