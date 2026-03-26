import os
from google import genai
from dotenv import load_dotenv

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

def list_models():
    client = genai.Client(api_key=GEMINI_API_KEY)
    print("Listing models...")
    for model in client.models.list():
        print(f"Name: {model.name}")
        # print(f"Full Model: {model}") # To see all fields if needed

if __name__ == "__main__":
    list_models()
