import google.generativeai as genai
import os
from dotenv import load_dotenv
import sys

# Redirect output to file
log_file = open("list_models_output.txt", "w")
sys.stdout = log_file
sys.stderr = log_file

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=api_key)

try:
    print("Listing available models...")
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(m.name)
except Exception as e:
    print(f"Error listing models: {e}")

log_file.close()
