import os
import re
import base64
import hashlib
from pathlib import Path

import streamlit as st
from google import genai
from openai import OpenAI

# -------------------------------------------------
# Page configuration
# -------------------------------------------------
st.set_page_config(
    page_title="Little Questions, Clear Answers",
    page_icon="❓",
    layout="centered"
)

# -------------------------------------------------
# Secrets (works locally + deployed)
# -------------------------------------------------
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or st.secrets.get("GEMINI_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") or st.secrets.get("OPENAI_API_KEY")

if not GEMINI_API_KEY or not OPENAI_API_KEY:
    st.error("API keys not found.")
    st.stop()

# -------------------------------------------------
# Clients
# -------------------------------------------------
gemini_client = genai.Client(api_key=GEMINI_API_KEY)
openai_client = OpenAI(api_key=OPENAI_API_KEY)

TEXT_MODEL = "models/gemini-flash-latest"

IMAGE_DIR = Path("generated_images")
IMAGE_DIR.mkdir(exist_ok=True)

# -------------------------------------------------
# Image generation (cached on disk)
# -------------------------------------------------
def generate_image(prompt: str):
    filename = hashlib.sha1(prompt.encode()).hexdigest()[:12] + ".png"
    path = IMAGE_DIR / filename

    if path.exists():
        return path

    full_prompt = (
        "Children's picture book illustration. "
        "Soft watercolor style. Simple shapes. "
        "Pastel colors. No text. Kid-safe. "
        f"Scene: {prompt}"
    )

    result = openai_client.images.generate(
        model="gpt-image-1",
        prompt=full_prompt,
        size="1024x1024"
    )

    image_bytes = base64.b64decode(result.data[0].b64_json)
    path.write_bytes(image_bytes)
    return path

# -------------------------------------------------
# Styling
# -------------------------------------------------
st.markdown(
    """
    <style>
    body { background-color: #FFF8F0; }
    .page-card {
        background-color: white;
        padding: 24px;
        border-radius: 18px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
    }
    .page-text {
        font-size: 18px;
        line-height: 1.7;
        color: #333;
    }
    .nav {
        text-align: center;
        font-size: 14px;
        color: #666;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# -------------------------------------------------
# UI
# -------------------------------------------------
st.title("🌙 A Thousand Whys Before Bedtime")

age = st.selectbox("Child's age", list(range(3, 11)))
question = st.text_input("What is your child asking?", "Why is the sea salty?")
tone = st.selectbox(
    "Tone",
    ["Gentle & soothing", "Funny", "Curious explorer", "Simple & direct"]
)

# -------------------------------------------------
# Session state
# -------------------------------------------------
if "pages" not in st.session_state:
    st.session_state.pages = []
    st.session_state.page_index = 0

# -------------------------------------------------
# Generate story + ALL images upfront
# -------------------------------------------------
if st.button("🌟 Explain this question", key="generate"):
    st.session_state.page_index = 0

    prompt = f"""
You are creating a children's STORYBOOK.

Question: {question}
Child age: {age}
Tone: {tone}

Rules:
- Age-appropriate language
- Simple, clear explanations
- No parents, no bedtime framing

Structure:
Page 1: WHAT it is
Page 2: WHY it happens
Page 3–4: HOW it works
Final page: What it means for the child

FORMAT (STRICT):
[Page]
2–3 simple sentences.

[Illustration idea]
Describe one picture.

Repeat for 4–6 pages.
"""

    response = gemini_client.models.generate_content(
        model=TEXT_MODEL,
        contents=prompt
    )

    raw = response.text

    pages = []
    chunks = re.split(r"\[Page\]", raw, flags=re.IGNORECASE)

    with st.spinner("Creating your storybook…"):
        for chunk in chunks:
            if not chunk.strip():
                continue

            parts = re.split(r"\[Illustration idea\]", chunk, flags=re.IGNORECASE)
            if len(parts) != 2:
                continue

            text = parts[0].strip()
            illustration_prompt = parts[1].strip()

            img_path = generate_image(illustration_prompt)

            pages.append({
                "text": text,
                "image_path": str(img_path)
            })

    st.session_state.pages = pages
    st.rerun()

# -------------------------------------------------
# Render storybook
# -------------------------------------------------
if st.session_state.pages:
    page = st.session_state.pages[st.session_state.page_index]

    col1, col2 = st.columns(2)

    with col1:
        st.markdown(
            f"""
            <div class="page-card">
                <div class="page-text">
                    {page["text"]}
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col2:
        st.image(page["image_path"], use_container_width=True)

    st.divider()

    col_prev, col_mid, col_next = st.columns([1, 2, 1])

    with col_prev:
        if st.button("⬅ Previous", disabled=st.session_state.page_index == 0):
            st.session_state.page_index -= 1
            st.rerun()

    with col_mid:
        st.markdown(
            f"<div class='nav'>Page {st.session_state.page_index + 1} of {len(st.session_state.pages)}</div>",
            unsafe_allow_html=True
        )

    with col_next:
        if st.button(
            "Next ➡",
            disabled=st.session_state.page_index == len(st.session_state.pages) - 1
        ):
            st.session_state.page_index += 1
            st.rerun()
