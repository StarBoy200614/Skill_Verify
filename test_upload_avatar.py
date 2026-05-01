import requests

url = "http://127.0.0.1:5000/api/login"
session = requests.Session()
login_data = {
    "email": "test@example.com",
    "password": "password"
}
import uuid
unique_id = str(uuid.uuid4())
test_email = f"test_{unique_id}@example.com"

# We need an existing user or we'll register one first
r_req = session.post("http://127.0.0.1:5000/api/register", json={
    "email": test_email,
    "password": "password",
    "name": "Test Avatar"
})

r_login = session.post("http://127.0.0.1:5000/api/login", json={
    "email": test_email,
    "password": "password"
})

if r_login.status_code == 200:
    print("Login successful")
    
    # Create fake image
    with open("fake_avatar.jpg", "wb") as f:
        f.write(b"fake image data")
        
    with open("fake_avatar.jpg", "rb") as f:
        files = {"file": ("fake_avatar.jpg", f, "image/jpeg")}
        r_upload = session.post("http://127.0.0.1:5000/api/user/upload-avatar", files=files)
        
    print("Upload Status:", r_upload.status_code)
    print("Upload Response:", r_upload.text)
else:
    print("Login failed:", r_login.text)
