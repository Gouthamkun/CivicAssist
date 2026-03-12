import requests
import uuid
import os

BASE_URL = "http://localhost:8000"

def test_secure_document_flow():
    unique_id = str(uuid.uuid4())[:8]
    email = f"secure_test_{unique_id}@example.com"
    password = "testpassword123"
    
    # 1. Register & Login
    requests.post(f"{BASE_URL}/api/register", data={
        "name": "Secure Tester",
        "email": email,
        "phone": "9876543210",
        "password": password
    })
    login_resp = requests.post(f"{BASE_URL}/api/login", json={"email": email, "password": password})
    token = login_resp.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Upload Dummy Document
    print("Uploading document...")
    dummy_content = b"SECURE CONTENT"
    files = {"file": ("secure.pdf", dummy_content, "application/pdf")}
    upload_resp = requests.post(f"{BASE_URL}/api/upload_document", headers=headers, data={"doc_type": "aadhaar"}, files=files)
    assert upload_resp.status_code == 200

    # 3. Verify Header-based Access (EXPECT SUCCESS)
    print("Testing header-based access (Success case)...")
    view_resp = requests.get(f"{BASE_URL}/api/view_document/aadhaar", headers=headers)
    print(f"Header Access Status: {view_resp.status_code}")
    assert view_resp.status_code == 200
    assert view_resp.content == dummy_content

    # 4. Verify Query-parameter Access (EXPECT FAILURE)
    print("Testing query-parameter access (Failure case)...")
    download_url = f"{BASE_URL}/api/download_document/aadhaar?token={token}"
    fail_resp = requests.get(download_url)
    print(f"Query Param Access Status: {fail_resp.status_code}")
    assert fail_resp.status_code == 401
    print("Access correctly blocked without Authorization header.")

if __name__ == "__main__":
    try:
        test_secure_document_flow()
        print("\nSecurity verification test passed!")
    except Exception as e:
        print(f"\nSecurity verification test failed: {e}")
