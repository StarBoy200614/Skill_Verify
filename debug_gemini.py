import os
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

print(f"DEBUG: API Key found: {'Yes' if api_key else 'No'}")
if api_key:
    print(f"DEBUG: API Key length: {len(api_key)}")
    print(f"DEBUG: API Key preview: {api_key[:5]}...{api_key[-5:]}")
else:
    print("CRITICAL: GEMINI_API_KEY not found in environment variables.")

try:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-1.5-flash")
    
    print("\n--- Sending Test Request to Gemini ---")
    response = model.generate_content("Hello, this is a test. Are you working?")
    
    if response.text:
        print(f"SUCCESS: Received response from Gemini: {response.text}")
    else:
        print("FAILURE: Response object was empty or invalid.")
        
except Exception as e:
    print(f"\nCRITICAL ERROR: {e}")
