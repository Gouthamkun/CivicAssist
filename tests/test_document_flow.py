import requests
import uuid
import os
import io

BASE_URL = "http://localhost:8000"

def test_document_flow():
    unique_id = str(uuid.uuid4())[:8]
    email = f"doc_test_{unique_id}@example.com"
    password = "testpassword123"
    
    # 1. Register & Login to get token
    requests.post(f"{BASE_URL}/api/register", data={
        "name": "Doc Tester",
        "email": email,
        "phone": "9876543210",
        "password": password
    })
    login_resp = requests.post(f"{BASE_URL}/api/login", json={"email": email, "password": password})
    token = login_resp.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Upload Dummy Aadhaar
    print("Uploading Aadhaar...")
    dummy_content = b"This is a dummy Aadhaar PDF content for testing."
    files = {"file": ("aadhaar.pdf", dummy_content, "application/pdf")}
    data = {"doc_type": "aadhaar"}
    upload_resp = requests.post(f"{BASE_URL}/api/upload_document", headers=headers, data=data, files=files)
    print(f"Upload Status: {upload_resp.status_code}")
    assert upload_resp.status_code == 200
    assert upload_resp.json()["success"] == True

    # 3. Check User Documents
    print("Checking document status...")
    status_resp = requests.get(f"{BASE_URL}/api/user_documents", headers=headers)
    print(f"Status Response: {status_resp.json()}")
    assert "aadhaar" in status_resp.json()["uploaded_types"]

    # 4. View Document
    print("Viewing Aadhaar...")
    view_resp = requests.get(f"{BASE_URL}/api/view_document/aadhaar", headers=headers)
    print(f"View Status: {view_resp.status_code}")
    assert view_resp.status_code == 200
    assert view_resp.content == dummy_content
    print("Document content matches!")

    # 5. Download Document (Tests the query parameter token too)
    print("Downloading Aadhaar via query token...")
    download_url = f"{BASE_URL}/api/download_document/aadhaar?token={token}"
    download_resp = requests.get(download_url)
    print(f"Download Status: {download_resp.status_code}")
    assert download_resp.status_code == 200
    assert download_resp.content == dummy_content
    assert "attachment; filename=aadhaar.pdf" in download_resp.headers.get("Content-Disposition", "")
    print("Download content and filename match!")

if __name__ == "__main__":
    try:
        test_document_flow()
        print("\nDocument flow test passed!")
    except Exception as e:
        print(f"\nDocument flow test failed: {e}")
