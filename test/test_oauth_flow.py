import asyncio
from fastapi.testclient import TestClient
from app.main import app
import httpx
from unittest.mock import patch, MagicMock

client = TestClient(app)

def test_login_flow():
    print("1. Testing /auth/google/login...")
    response = client.get("/auth/google/login", follow_redirects=False)
    assert response.status_code == 302
    redirect_url = response.headers["location"]
    print(f"   Redirects to Google: {redirect_url.split('?')[0]}?...")

    print("2. Simulating Google Callback...")
    
    mock_post_resp = MagicMock()
    mock_post_resp.json.return_value = {"access_token": "fake_access_token"}
    
    mock_get_resp = MagicMock()
    mock_get_resp.json.return_value = {
        "email": "testuser@example.com",
        "name": "Test User"
    }

    class MockAsyncClient:
        async def __aenter__(self):
            return self
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass
        async def post(self, url, **kwargs):
            return mock_post_resp
        async def get(self, url, **kwargs):
            return mock_get_resp

    with patch('httpx.AsyncClient', return_value=MockAsyncClient()):
        response = client.get("/auth/google/callback?code=FAKE_CODE", follow_redirects=False)
        
        print(f"   Callback Status: {response.status_code}")
        print(f"   Redirects to: {response.headers.get('location')}")
        
        if response.status_code in [303, 302]:
            print("   SUCCESS! Authentication flow completed smoothly.")
        else:
            print("   FAILED! Response body:", response.text)

if __name__ == "__main__":
    test_login_flow()
