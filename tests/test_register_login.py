import requests
import uuid

BASE_URL = "http://localhost:8000"

def test_registration_and_login():
    unique_id = str(uuid.uuid4())[:8]
    email = f"test_{unique_id}@example.com"
    password = "testpassword123"
    name = "Test User"
    phone = "1234567890"

    # 1. Register
    print(f"Registering user: {email}")
    reg_data = {
        "name": name,
        "email": email,
        "phone": phone,
        "password": password
    }
    response = requests.post(f"{BASE_URL}/api/register", data=reg_data)
    print(f"Register Status: {response.status_code}")
    print(f"Register Response: {response.json()}")
    assert response.status_code == 200
    assert response.json()["success"] == True

    # 2. Login
    print(f"Logging in user: {email}")
    login_data = {
        "email": email,
        "password": password
    }
    response = requests.post(f"{BASE_URL}/api/login", json=login_data)
    print(f"Login Status: {response.status_code}")
    print(f"Login Response: {response.json()}")
    assert response.status_code == 200
    assert response.json()["success"] == True
    token = response.json()["token"]
    assert token is not None
    
    # 3. Get Me
    print("Fetching /api/me")
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/api/me", headers=headers)
    print(f"Me Status: {response.status_code}")
    print(f"Me Response: {response.json()}")
    assert response.status_code == 200
    assert response.json()["email"] == email

if __name__ == "__main__":
    try:
        test_registration_and_login()
        print("\nIntegration test passed!")
    except Exception as e:
        print(f"\nIntegration test failed: {e}")
        print("Make sure the backend is running: uvicorn backend.main:app --reload")
