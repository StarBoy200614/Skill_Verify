
import google.generativeai as genai
import os

GEMINI_API_KEY = "AIzaSyAk0Rxl3-e96BTkdAN1xkhauPjVoGqs5Rg"
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-flash-latest")

try:
    response = model.generate_content("Hello, can you hear me?")
    print(f"SUCCESS: {response.text}")
except Exception as e:
    print(f"FAILURE: {e}")
