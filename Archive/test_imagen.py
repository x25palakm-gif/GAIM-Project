import os
import base64
from google import genai

API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise RuntimeError("Set GEMINI_API_KEY first")

client = genai.Client(api_key=API_KEY)

MODEL_ID = "models/imagen-4.0-generate-001"

prompt = (
    "Children's picture book illustration of rivers flowing into the ocean, "
    "soft watercolor style, simple shapes, smiling waves, pastel colors, "
    "no text, kid-safe"
)

response = client.models.generate_images(
    model=MODEL_ID,
    prompt=prompt,
    config={
        "image_size": "1K"   # ✅ MUST be "1K" or "2K"
    }
)

image = response.images[0]
image_bytes = base64.b64decode(image.image_base64)

with open("imagen_test.png", "wb") as f:
    f.write(image_bytes)

print("✅ Image saved as imagen_test.png")
