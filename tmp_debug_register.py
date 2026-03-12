import requests

url = "http://localhost:8001/api/register"
data = {
    "name": "Debug User",
    "email": "debug@example.com",
    "phone": "1234567890",
    "password": "password123"
}

try:
    response = requests.post(url, data=data)
    print(f"Status Code: {response.status_code}")
    print(f"Response Body: {response.text}")
except Exception as e:
    print(f"Request failed: {e}")
