import os
import google.generativeai as genai
from dotenv import load_dotenv
import sys

# Redirect output to file
log_file = open("debug_gemini_output.txt", "w")
sys.stdout = log_file
sys.stderr = log_file

print("Starting Debug Script...")

# Load environment variables
load_dotenv()
print("Environment loaded.")

api_key = os.getenv("GEMINI_API_KEY")

print(f"DEBUG: API Key found: {'Yes' if api_key else 'No'}")
if api_key:
    print(f"DEBUG: API Key length: {len(api_key)}")
    print(f"DEBUG: API Key preview: {api_key[:5]}...{api_key[-5:]}")
else:
    print("CRITICAL: GEMINI_API_KEY not found in environment variables.")

try:
    if not api_key:
        print("Cannot proceed without API key.")
    else:
        genai.configure(api_key=api_key)
        # Using a model from the available list
        model = genai.GenerativeModel("gemini-2.0-flash")
        
        print("\n--- Sending Test Request to Gemini ---")
        response = model.generate_content("Hello")
        
        if response.text:
            print(f"SUCCESS: Received response from Gemini: {response.text}")
        else:
            print("FAILURE: Response object was empty or invalid.")
        
except Exception as e:
    print(f"\nCRITICAL ERROR: {e}")

log_file.close()
