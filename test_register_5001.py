import requests
try:
    res = requests.post("http://127.0.0.1:5001/api/register", json={
        "email": "akgaming2@gmail.com", 
        "password": "123", 
        "name": "Akshay Kumar"
    })
    print("STATUS:", res.status_code)
    print("TEXT:", res.text)
except Exception as e:
    print("ERROR:", str(e))
