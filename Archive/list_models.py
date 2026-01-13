import google.generativeai as genai
import os

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

models = genai.list_models()

for m in models:
    print("MODEL:", m.name)
    print("  supports:", m.supported_generation_methods)
    print("-----")
