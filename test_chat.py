import urllib.request
import json
req = urllib.request.Request('http://127.0.0.1:5000/api/chat', method='POST', data=b'{"message":"hi"}', headers={'Content-Type': 'application/json'})
try:
    urllib.request.urlopen(req)
except Exception as e:
    print(e.read().decode())
