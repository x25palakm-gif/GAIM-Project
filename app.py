import os
import re
import json
import base64
import hashlib
from pathlib import Path

import streamlit as st
from openai import OpenAI

# -------------------------------------------------
# Page configuration
# -------------------------------------------------
st.set_page_config(
    page_title="Little Questions, Clear Answers",
    page_icon="📖",
    layout="centered"
)

# -------------------------------------------------
# API key
# -------------------------------------------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") or st.secrets.get("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    st.error("OpenAI API key not found.")
    st.stop()

client = OpenAI(api_key=OPENAI_API_KEY, timeout=30)

# -------------------------------------------------
# Directories
# -------------------------------------------------
IMAGE_DIR = Path("generated_images")
IMAGE_DIR.mkdir(exist_ok=True)

CACHE_DIR = Path("story_cache")
CACHE_DIR.mkdir(exist_ok=True)

# -------------------------------------------------
# Cache helpers
# -------------------------------------------------
def make_cache_key(question: str, age: int, tone: str) -> str:
    key = f"{question.lower().strip()}|{age}|{tone}"
    return hashlib.sha1(key.encode()).hexdigest()

def load_from_cache(cache_key: str):
    path = CACHE_DIR / f"{cache_key}.json"
    if path.exists():
        with open(path, "r") as f:
            return json.load(f)
    return None

def save_to_cache(cache_key: str, pages: list):
    path = CACHE_DIR / f"{cache_key}.json"
    with open(path, "w") as f:
        json.dump(pages, f)

# -------------------------------------------------
# Generate story text (SAFE)
# -------------------------------------------------
def generate_story_text(prompt: str) -> str:
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You write short, child-friendly storybook explanations."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.6,
        )
        if not response or not response.choices:
            return ""
        return response.choices[0].message.content or ""
    except Exception as e:
        st.error("Text generation failed.")
        st.code(str(e))
        return ""

# -------------------------------------------------
# Generate image (cached)
# -------------------------------------------------
def generate_image(prompt: str):
    filename = hashlib.sha1(prompt.encode()).hexdigest()[:12] + ".png"
    path = IMAGE_DIR / filename

    if path.exists():
        return path

    result = client.images.generate(
        model="gpt-image-1",
        prompt=(
            "Children's picture book illustration. "
            "Soft watercolor style. Pastel colors. "
            "No text. Kid-safe. "
            f"Scene: {prompt}"
        ),
        size="1024x1024"
    )

    image_bytes = base64.b64decode(result.data[0].b64_json)
    path.write_bytes(image_bytes)
    return path

# -------------------------------------------------
# Styling (unchanged, safe)
# -------------------------------------------------
st.markdown(
    """
    <style>
    body { background: linear-gradient(180deg, #FFF8F0, #FDEBD0); }
    h1 { text-align: center; color: #6C3483; }
    .subtitle { text-align: center; font-size: 18px; color: #7D6608; }
    .page-card {
        background: white;
        padding: 28px;
        border-radius: 22px;
        box-shadow: 0 10px 25px rgba(0,0,0,0.08);
    }
    .page-text { font-size: 18px; line-height: 1.7; }
    .nav { text-align: center; font-size: 14px; color: #555; }
    </style>
    """,
    unsafe_allow_html=True
)

# -------------------------------------------------
# UI
# -------------------------------------------------
st.title("🌙 A Thousand Whys Before Bedtime")
st.markdown("<div class='subtitle'>Gentle explanations for curious little minds</div>", unsafe_allow_html=True)

age = st.selectbox("👶 Child's age", list(range(3, 11)))
question = st.text_input("❓ What is your child asking?", "Why is the sea salty?")
tone = st.selectbox("🎨 Tone", ["Gentle & soothing", "Funny", "Curious explorer", "Simple & direct"])

# -------------------------------------------------
# Session state
# -------------------------------------------------
if "pages" not in st.session_state:
    st.session_state.pages = []
    st.session_state.page_index = 0

# -------------------------------------------------
# Generate / Load storybook
# -------------------------------------------------
if st.button("✨ Create storybook", key="generate"):
    cache_key = make_cache_key(question, age, tone)

    cached_pages = load_from_cache(cache_key)
    if cached_pages:
        st.session_state.pages = cached_pages
        st.session_state.page_index = 0
        st.success("Loaded instantly from saved stories ✨")
        st.stop()

    prompt = f"""
Explain the question for a {age}-year-old child.

Question: {question}
Tone: {tone}

Structure:
[Page]
2–3 simple sentences.
[Illustration idea]
Describe one picture.

Create 4–6 pages.
"""

    with st.spinner("📖 Writing your storybook…"):
        raw = generate_story_text(prompt)

    if not raw.strip():
        st.error("The AI did not return any story text.")
        st.stop()

    pages = []
    chunks = re.split(r"\[Page\]", raw)

    with st.spinner("🎨 Creating illustrations…"):
        for chunk in chunks:
            if not chunk.strip():
                continue
            parts = re.split(r"\[Illustration idea\]", chunk)
            if len(parts) != 2:
                continue

            img = generate_image(parts[1].strip())
            pages.append({
                "text": parts[0].strip(),
                "image_path": str(img)
            })

    st.session_state.pages = pages
    st.session_state.page_index = 0
    save_to_cache(cache_key, pages)
    st.rerun()

# -------------------------------------------------
# Render pages
# -------------------------------------------------
if st.session_state.pages:
    page = st.session_state.pages[st.session_state.page_index]

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"<div class='page-card'><div class='page-text'>{page['text']}</div></div>", unsafe_allow_html=True)
    with col2:
        st.image(page["image_path"], width="stretch")

    st.divider()

    col_prev, col_mid, col_next = st.columns([1, 2, 1])
    with col_prev:
        if st.button("⬅ Previous", disabled=st.session_state.page_index == 0):
            st.session_state.page_index -= 1
            st.rerun()
    with col_mid:
        st.markdown(f"<div class='nav'>Page {st.session_state.page_index+1} of {len(st.session_state.pages)}</div>", unsafe_allow_html=True)
    with col_next:
        if st.button("Next ➡", disabled=st.session_state.page_index == len(st.session_state.pages)-1):
            st.session_state.page_index += 1
            st.rerun()
