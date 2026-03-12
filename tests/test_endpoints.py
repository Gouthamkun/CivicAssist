import requests
import json
import os

API_BASE = "http://localhost:8000"

# Note: This requires the server to be running and a valid user to exist.
# For this automated check, we'll try to hit the endpoints directly if possible,
# or just verify the logic if the server isn't running.

def test_ask_tax_question():
    print("Testing /api/ask_tax_question...")
    url = f"{API_BASE}/api/ask_tax_question"
    payload = {"question": "How to withdraw PF?"}
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            data = response.json()
            print("Success! Received structured data:")
            print(json.dumps(data, indent=2))
        else:
            print(f"Failed with status code: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"Error connecting to server: {e}")

def test_explain_notice():
    print("\nTesting /api/explain_notice...")
    url = f"{API_BASE}/api/explain_notice"
    # Create a dummy text file to simulate a notice
    with open("dummy_notice.txt", "w") as f:
        f.write("Income Tax Department Notice under Section 143(1). Please pay the demand.")
    
    try:
        with open("dummy_notice.txt", "rb") as f:
            files = {"file": ("dummy_notice.txt", f, "text/plain")}
            response = requests.post(url, files=files, timeout=10)
            if response.status_code == 200:
                data = response.json()
                print("Success! Received structured data:")
                print(json.dumps(data, indent=2))
            else:
                print(f"Failed with status code: {response.status_code}")
                print(response.text)
    except Exception as e:
        print(f"Error connecting to server: {e}")
    finally:
        if os.path.exists("dummy_notice.txt"):
            os.remove("dummy_notice.txt")

if __name__ == "__main__":
    # We can't easily start the server and run tests in one go without backgrounding,
    # so we'll just try to hit it if it's already up.
    test_ask_tax_question()
    test_explain_notice()
