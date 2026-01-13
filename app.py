import os
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
    st.error("Gemini API key not found. Please set GEMINI_API_KEY.")
    st.stop()

if not OPENAI_API_KEY:
    st.error("OpenAI API key not found. Please set OPENAI_API_KEY.")
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
# OpenAI image generator
# -------------------------------------------------
def generate_image(prompt: str):
    """
    Generate a child-safe illustration using OpenAI Images.
    Images are cached locally to avoid repeat costs.
    """
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
            size="1024x1024"
        )

        image_base64 = result.data[0].b64_json
        image_bytes = base64.b64decode(image_base64)

        with open(path, "wb") as f:
            f.write(image_bytes)

        return path

    except Exception as e:
        st.error("Image generation failed (OpenAI)")
        st.code(str(e))
        return None

# -------------------------------------------------
# Styling (UNCHANGED)
# -------------------------------------------------
st.markdown(
    """
    <style>
    body { background-color: #FFF8F0; }

    .main {
        padding: 2rem;
        max-width: 720px;
        margin: auto;
    }

    h1 {
        color: #FF6F61;
        text-align: center;
        font-family: "Comic Sans MS", "Trebuchet MS", sans-serif;
    }

    .explain-card {
        background-color: #FFFFFF;
        padding: 22px;
        border-radius: 16px;
        margin-bottom: 20px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
    }

    .explain-text {
        font-size: 18px;
        line-height: 1.6;
        color: #333333;
    }

    .illustration-text {
        font-size: 14px;
        color: #777777;
        margin-top: 10px;
        font-style: italic;
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
    "into gentle, illustrated explanations using AI."
)

st.divider()

st.subheader("👶 Tell us about your little explorer")

child_name = st.text_input("Child's name (optional)")

age = st.selectbox(
    "Select your child's age",
    options=list(range(3, 11))
)

st.divider()

st.subheader("❓ What question came today?")

question = st.text_input(
    "What is your child asking?",
    placeholder="E.g., Why does a lion roar?"
)

st.divider()

st.subheader("🎨 How should the answer feel?")

tone = st.selectbox(
    "Choose the story tone",
    options=[
        "Gentle & soothing",
        "Funny",
        "Curious explorer",
        "Simple & direct"
    ]
)

st.divider()

# -------------------------------------------------
# Generate explanation
# -------------------------------------------------
if st.button("🌟 Explain this question"):
    if not question:
        st.warning("Please type a question first.")
    else:
        prompt = f"""
You are creating an illustrated explanation for a young child.

Explain the following question in a SIMPLE, CHILD-FRIENDLY way.

You are explaining a child’s “why” question the way a good children’s book would.

Your job is to help a child truly understand the idea — not to tell a story, and not to talk to parents.

Question: {question}
Child age: {age}
Tone: {tone}

AGE RULES (very important):
- Use words, examples, and sentence length appropriate for a {age}-year-old
- Younger children (3–5): very simple words, short sentences, familiar objects
- Older children (6–10): slightly more detail, but still simple and concrete
- Avoid abstract terms unless they are explained using everyday examples

STRUCTURE RULE (must follow):
The explanation must flow like this:
1. WHAT it is (what the thing or idea is)
2. WHY it exists or happens (the main reason, simply explained)
3. HOW it works (in simple steps or cause-and-effect)

CONTENT RULES:
- Do NOT include bedtime, parents, or story framing
- Do NOT include characters like mommy, daddy, or teachers
- Do NOT ask questions back to the child
- Focus only on the idea being explained
- Be calm, curious, and reassuring
- Avoid unnecessary details or side facts

FORMAT RULES (strict):
- Write 4–6 short sections
- Each section explains ONE clear idea
- Each section should be 2–3 simple sentences

For EACH section:
1. Write the explanation text
2. On the very next line, write exactly:
[Illustration idea: describe what should be drawn in a child-friendly picture]

Example style (not content):
Water is all around us in the world.
We drink it, wash with it, and see it in rivers.
[Illustration idea: a child looking at rain, a river, and a glass of water]

Do not add titles, summaries, or anything extra.
Do not include emojis.
Do not include explanations outside this format.

"""

        try:
            response = gemini_client.models.generate_content(
                model=TEXT_MODEL,
                contents=prompt
            )

            explanation_text = response.text

            st.subheader("📘 Illustrated Explanation")

            sections = explanation_text.split("[Illustration idea:")

            for section in sections:
                if not section.strip():
                    continue

                parts = section.split("]")
                text_part = parts[0].strip()
                illustration = parts[1].strip() if len(parts) > 1 else ""

                st.markdown(
                    f"""
                    <div class="explain-card">
                        <div class="explain-text">{text_part}</div>
                        <div class="illustration-text">
                            🎨 Illustration idea: {illustration}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                if illustration:
                    with st.spinner("Creating illustration…"):
                        img_path = generate_image(illustration)

                    if img_path:
                        st.image(str(img_path), use_container_width=True)

        except Exception as e:
            st.error("Something went wrong while generating the explanation.")
            st.code(str(e), language="text")

# -------------------------------------------------
# Footer
# -------------------------------------------------
st.markdown("---")
st.caption("💛 Built to help curious kids understand the world")
