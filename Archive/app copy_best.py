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
# API keys
# -------------------------------------------------
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not GEMINI_API_KEY:
    st.error("Gemini API key not found.")
    st.stop()

if not OPENAI_API_KEY:
    st.error("OpenAI API key not found.")
    st.stop()

# -------------------------------------------------
# Gemini client (NEW SDK – unchanged)
# -------------------------------------------------
genai_client = genai.Client(api_key=GEMINI_API_KEY)
TEXT_MODEL = "models/gemini-flash-latest"

# -------------------------------------------------
# OpenAI client
# -------------------------------------------------
openai_client = OpenAI(api_key=OPENAI_API_KEY)

IMAGE_DIR = Path("generated_images")
IMAGE_DIR.mkdir(exist_ok=True)

# -------------------------------------------------
# FIX 2: Helper to clean explanation text
# -------------------------------------------------
def clean_explanation_text(text: str) -> str:
    """
    Remove any accidental illustration or instruction leakage
    from explanation text before displaying to the child.
    """
    lines = text.splitlines()
    cleaned = []

    for line in lines:
        l = line.lower()
        if any(word in l for word in [
            "illustration",
            "illustrate",
            "picture",
            "image",
            "drawing",
            "shows",
            "depicts"
        ]):
            continue
        cleaned.append(line)

    return " ".join(cleaned).strip()

# -------------------------------------------------
# OpenAI image generation (unchanged)
# -------------------------------------------------
def generate_image(prompt: str):
    filename = hashlib.sha1(prompt.encode()).hexdigest()[:12] + ".png"
    path = IMAGE_DIR / filename

    if path.exists():
        return path

    try:
        full_prompt = (
            "Children's picture book illustration. "
            "Soft watercolor style. Simple shapes. "
            "Pastel colors. No text. Kid-safe. "
            f"Scene to illustrate: {prompt}"
        )

        result = openai_client.images.generate(
            model="gpt-image-1",
            prompt=full_prompt,
            size="512x512"
        )

        image_bytes = base64.b64decode(result.data[0].b64_json)
        path.write_bytes(image_bytes)
        return path

    except Exception as e:
        st.error("Image generation failed")
        st.code(str(e))
        return None

# -------------------------------------------------
# Styling (UNCHANGED)
# -------------------------------------------------
st.markdown(
    """
    <style>
    body { background-color: #FFF8F0; }

    .page-card {
        background-color: #FFFFFF;
        padding: 26px;
        border-radius: 18px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
    }

    .page-text {
        font-size: 18px;
        line-height: 1.7;
        color: #333333;
    }

    .nav-text {
        text-align: center;
        color: #666;
        font-size: 14px;
    }

    .stButton > button {
        background-color: #88B04B;
        color: white;
        font-size: 18px;
        padding: 10px 28px;
        border-radius: 14px;
        border: none;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# -------------------------------------------------
# UI (UNCHANGED)
# -------------------------------------------------
st.title("🌙 A Thousand Whys Before Bedtime")

st.write(
    "✨ A cozy, colorful place where moms turn little **“why?”** questions "
    "into gentle, illustrated storybook explanations."
)

st.divider()

age = st.selectbox("Child's age", list(range(3, 11)))

question = st.text_input(
    "What is your child asking?",
    placeholder="Why is the sea salty?"
)

tone = st.selectbox(
    "Choose the story tone",
    ["Gentle & soothing", "Funny", "Curious explorer", "Simple & direct"]
)

st.divider()

# -------------------------------------------------
# Session state (UNCHANGED)
# -------------------------------------------------
if "pages" not in st.session_state:
    st.session_state.pages = []
    st.session_state.page_index = 0

# -------------------------------------------------
# Generate story
# -------------------------------------------------
if st.button("🌟 Explain this question"):
    if not question:
        st.warning("Please type a question first.")
    else:
        st.session_state.page_index = 0

        # -------------------------------------------------
        # FIX 1: Prompt hardening
        # -------------------------------------------------
        prompt = f"""
You are creating a CHILDREN'S PICTURE BOOK.

Explain the question below clearly for a child.

Question: {question}
Child age: {age}
Tone: {tone}

RULES:
- Simple, age-appropriate language
- Short sentences
- Focus on WHAT → WHY → HOW
- Do NOT mention pictures, illustrations, drawings, or visuals in the explanation text
- No parents, no bedtime framing
- No emojis, no extra commentary

BOOK STRUCTURE:
Create 4–6 pages.

Each page MUST follow this EXACT format:

<PAGE>
<TEXT>
2–3 simple sentences explaining ONE idea.
</TEXT>
<IMAGE>
Describe ONE clear picture that matches the text.
</IMAGE>

Do not deviate from this format.
"""

        try:
            response = genai_client.models.generate_content(
                model=TEXT_MODEL,
                contents=prompt
            )

            raw = response.text

            pages = []
            page_blocks = re.findall(
                r"<PAGE>\s*<TEXT>(.*?)</TEXT>\s*<IMAGE>(.*?)</IMAGE>",
                raw,
                re.DOTALL | re.IGNORECASE
            )

            for text, image in page_blocks:
                pages.append({
                    "text": text.strip(),
                    "illustration": image.strip()
                })

            if not pages:
                st.error("Story format error. Raw output below:")
                st.code(raw)
            else:
                st.session_state.pages = pages
                st.rerun()

        except Exception as e:
            st.error("Text generation failed")
            st.code(str(e))

# -------------------------------------------------
# Render storybook pages
# -------------------------------------------------
if st.session_state.pages:
    page = st.session_state.pages[st.session_state.page_index]

    col_text, col_img = st.columns([1, 1])

    with col_text:
        # -------------------------------------------------
        # FIX 3: Render ONLY cleaned explanation text
        # -------------------------------------------------
        st.markdown(
            f"""
            <div class="page-card">
                <div class="page-text">
                    {clean_explanation_text(page["text"])}
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col_img:
        with st.spinner("Creating illustration…"):
            img_path = generate_image(page["illustration"])
        if img_path:
            st.image(str(img_path), use_container_width=True)

    st.divider()

    col_prev, col_mid, col_next = st.columns([1, 2, 1])

    with col_prev:
        if st.button(
            "⬅ Previous",
            disabled=(st.session_state.page_index == 0)
        ):
            st.session_state.page_index -= 1
            st.rerun()

    with col_mid:
        st.markdown(
            f"<p class='nav-text'>Page {st.session_state.page_index + 1} of {len(st.session_state.pages)}</p>",
            unsafe_allow_html=True
        )

    with col_next:
        if st.button(
            "Next ➡",
            disabled=(st.session_state.page_index == len(st.session_state.pages) - 1)
        ):
            st.session_state.page_index += 1
            st.rerun()

# -------------------------------------------------
# Footer
# -------------------------------------------------
st.markdown("---")
st.caption("💛 Built to help curious kids understand the world")
