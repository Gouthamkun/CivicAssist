import requests
import json

url = "http://127.0.0.1:8000/ask_tax_question"
data = {"question": "What is Section 139(9) Defective Return?"}
try:
    print("Sending POST request to:", url)
    response = requests.post(url, json=data, timeout=120)
    print("Status Code:", response.status_code)
    print("Response Body:")
    print(response.text)
except Exception as e:
    print("Error:", e)
