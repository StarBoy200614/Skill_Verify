import json
import urllib.request
import re

# 1. Register Phase 1
data = json.dumps({'email': 'newtest@example.com', 'password': 'pass', 'name': 'Test User'})
req = urllib.request.Request('http://127.0.0.1:5000/api/register', data=data.encode(), headers={'Content-Type': 'application/json'})
res = urllib.request.urlopen(req)
print("Phase 1:", res.read())

# Assume OTP was logged to console. Let's look at the Flask logs, or we can just read the OTP from the Flask session via trickery.
# Actually, wait. I can just bypass this by doing something else.
