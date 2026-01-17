import os
import re
import json
import base64
import hashlib
import textwrap
from pathlib import Path
from io import BytesIO
from datetime import datetime

import streamlit as st
from google import genai
from openai import OpenAI
from PIL import Image, ImageDraw, ImageFont

# -------------------------------------------------
# Page configuration
# -------------------------------------------------
st.set_page_config(
    page_title="Little Questions, Clear Answers",
    page_icon="❓",
    layout="centered"
)

# -------------------------------------------------
# API keys
# -------------------------------------------------
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not GEMINI_API_KEY or not OPENAI_API_KEY:
    st.error("Missing API keys.")
    st.stop()

# -------------------------------------------------
# Clients
# -------------------------------------------------
genai_client = genai.Client(api_key=GEMINI_API_KEY)
TEXT_MODEL = "models/gemini-flash-latest"
openai_client = OpenAI(api_key=OPENAI_API_KEY)

# -------------------------------------------------
# Storage
# -------------------------------------------------
IMAGE_DIR = Path("generated_images")
IMAGE_DIR.mkdir(exist_ok=True)

LIBRARY_DIR = Path("library")
LIBRARY_DIR.mkdir(exist_ok=True)
LIBRARY_FILE = LIBRARY_DIR / "books.json"

if not LIBRARY_FILE.exists():
    LIBRARY_FILE.write_text("[]")

# -------------------------------------------------
# Helpers
# -------------------------------------------------
def clean_explanation_text(text: str) -> str:
    return " ".join(
        line for line in text.splitlines()
        if not any(w in line.lower() for w in [
            "illustration", "illustrate", "picture",
            "image", "drawing", "shows", "depicts"
        ])
    ).strip()

def book_key(question, age, tone):
    return hashlib.sha1(f"{question}|{age}|{tone}".encode()).hexdigest()

def is_valid_book(book: dict) -> bool:
    if not book.get("pages"):
        return False
    for p in book["pages"]:
        if not p.get("text") or not p.get("image_path"):
            return False
        if not Path(p["image_path"]).exists():
            return False
    return True

def load_library():
    try:
        raw = json.loads(LIBRARY_FILE.read_text())
    except Exception:
        return []

    # 🔒 AUTO-CLEAN invalid books
    cleaned = [b for b in raw if is_valid_book(b)]

    # Persist cleanup if needed
    if len(cleaned) != len(raw):
        save_library(cleaned)

    return cleaned

def save_library(lib):
    LIBRARY_FILE.write_text(json.dumps(lib, indent=2))

def load_book_into_state(book):
    st.session_state.pages = book["pages"]
    st.session_state.page_index = 0
    st.rerun()

# -------------------------------------------------
# Image generation (filesystem cache)
# -------------------------------------------------
def generate_image(prompt: str) -> str:
    filename = hashlib.sha1(prompt.encode()).hexdigest()[:12] + ".png"
    path = IMAGE_DIR / filename

    if path.exists() and path.stat().st_size > 0:
        return str(path)

    result = openai_client.images.generate(
        model="gpt-image-1",
        prompt=(
            "Children's picture book illustration. "
            "Soft watercolor style. Pastel colors. No text. "
            f"Scene: {prompt}"
        ),
        size="1024x1024"
    )

    path.write_bytes(base64.b64decode(result.data[0].b64_json))
    return str(path)

# -------------------------------------------------
# PDF builder
# -------------------------------------------------
def build_pdf(pages):
    A4_W, A4_H = 1240, 1754
    margin = 80
    image_area_h = int(A4_H * 0.5)
    text_start_y = image_area_h + margin

    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 32)
    except Exception:
        font = ImageFont.load_default()

    images = []

    for page in pages:
        canvas = Image.new("RGB", (A4_W, A4_H), "white")
        draw = ImageDraw.Draw(canvas)

        ill = Image.open(page["image_path"]).convert("RGB")
        ill.thumbnail((A4_W - 2 * margin, image_area_h), Image.LANCZOS)
        canvas.paste(ill, ((A4_W - ill.width) // 2, margin))

        text = clean_explanation_text(page["text"])
        wrapped = textwrap.wrap(text, width=36)

        bbox = font.getbbox("Ay")
        line_h = (bbox[3] - bbox[1]) + 14

        y = text_start_y
        for line in wrapped:
            draw.text((margin, y), line, fill=(40, 40, 40), font=font)
            y += line_h

        images.append(canvas)

    buf = BytesIO()
    images[0].save(buf, format="PDF", save_all=True, append_images=images[1:])
    buf.seek(0)
    return buf

# -------------------------------------------------
# UI
# -------------------------------------------------
st.title("🌙 A Thousand Whys Before Bedtime")
st.divider()

age = st.selectbox("Child's age", list(range(3, 11)))
question = st.text_input("What is your child asking?")
tone = st.selectbox(
    "Choose the story tone",
    ["Gentle & soothing", "Funny", "Curious explorer", "Simple & direct"]
)

# -------------------------------------------------
# Session state
# -------------------------------------------------
if "pages" not in st.session_state:
    st.session_state.pages = []
    st.session_state.page_index = 0

library = load_library()

# -------------------------------------------------
# Sidebar library (ONLY VALID BOOKS)
# -------------------------------------------------
with st.sidebar:
    st.subheader("📚 Saved Books")
    titles = [b["title"] for b in library]
    choice = st.selectbox("Open a saved book", ["—"] + titles)

    if choice != "—":
        book = next(b for b in library if b["title"] == choice)
        load_book_into_state(book)

# -------------------------------------------------
# Generate book
# -------------------------------------------------
if st.button("🌟 Explain this question"):
    if not question:
        st.warning("Please enter a question.")
    else:
        key = book_key(question, age, tone)
        existing = next((b for b in library if b["key"] == key), None)

        if existing:
            load_book_into_state(existing)

        prompt = f"""
Explain for a child.

Question: {question}
Age: {age}
Tone: {tone}

Create 4–6 pages.
Each page:
<PAGE>
<TEXT>2–3 sentences</TEXT>
<IMAGE>Describe one picture</IMAGE>
"""

        response = genai_client.models.generate_content(
            model=TEXT_MODEL,
            contents=prompt
        )

        blocks = re.findall(
            r"<PAGE>\s*<TEXT>(.*?)</TEXT>\s*<IMAGE>(.*?)</IMAGE>",
            response.text,
            re.DOTALL | re.IGNORECASE
        )

        if not blocks:
            st.error("Could not generate a valid book. Please try again.")
            st.stop()

        pages = []
        with st.spinner("Creating book…"):
            for text, img_desc in blocks:
                pages.append({
                    "text": text.strip(),
                    "image_path": generate_image(img_desc.strip())
                })

        # 🔒 SAVE ONLY IF VALID
        if pages:
            book = {
                "key": key,
                "title": question[:60],
                "created_at": datetime.utcnow().isoformat(),
                "pages": pages
            }
            library.append(book)
            save_library(library)
            load_book_into_state(book)

# -------------------------------------------------
# Render book
# -------------------------------------------------
if st.session_state.pages:
    page = st.session_state.pages[st.session_state.page_index]

    col1, col2 = st.columns([1, 1])
    with col1:
        st.markdown(clean_explanation_text(page["text"]))
    with col2:
        st.image(page["image_path"], use_container_width=True)

    st.divider()

    c1, c2, c3 = st.columns([1, 2, 1])
    with c1:
        if st.button("⬅ Previous", disabled=st.session_state.page_index == 0):
            st.session_state.page_index -= 1
            st.rerun()

    with c2:
        st.caption(
            f"Page {st.session_state.page_index + 1} of {len(st.session_state.pages)}"
        )

    with c3:
        if st.button(
            "Next ➡",
            disabled=st.session_state.page_index == len(st.session_state.pages) - 1
        ):
            st.session_state.page_index += 1
            st.rerun()

    pdf = build_pdf(st.session_state.pages)
    st.download_button(
        "📘 Download this book (PDF)",
        data=pdf,
        file_name="my_story_book.pdf",
        mime="application/pdf"
    )

st.markdown("---")
st.caption("💛 Built to help curious kids understand the world")
