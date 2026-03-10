import requests
from bs4 import BeautifulSoup

url = "https://incometaxindia.gov.in/pages/downloads/forms.aspx"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

try:
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    
    # Try to find the forms table or list
    # Look for download links
    forms = []
    
    # Just printing some snippets to understand the DOM
    print("Page Title:", soup.title.string)
    
    # Find links ending with .pdf
    pdf_links = soup.find_all('a', href=lambda href: href and ('.pdf' in href.lower() or '.zip' in href.lower()))
    
    for i, a in enumerate(pdf_links[:5]):
        print(f"\\n--- Found Link {i+1} ---")
        print("Text:", a.get_text(strip=True))
        print("Href:", a.get('href'))
        
        # See parent elements to find description and form name
        row = a.find_parent('tr')
        if row:
            cells = row.find_all('td')
            print("Row cells:")
            for j, cell in enumerate(cells):
                print(f"  Col {j}:", cell.get_text(strip=True))
        else:
            div = a.find_parent('div', class_='row') or a.find_parent('div')
            if div:
                print("Div content:", div.get_text(separator=' | ', strip=True)[:200])
                
except Exception as e:
    print(f"Error fetching page: {e}")
