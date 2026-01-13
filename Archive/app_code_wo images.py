import os
import streamlit as st
from google import genai

# -------------------------------------------------
# Page configuration
# -------------------------------------------------
st.set_page_config(
    page_title="Little Questions, Clear Answers",
    page_icon="❓",
    layout="centered"
)

# -------------------------------------------------
# API key check
# -------------------------------------------------
API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    st.error(
        "Gemini API key not found.\n\n"
        "Run this in Terminal:\n"
        "export GEMINI_API_KEY='your_api_key_here'\n"
        "Then restart Streamlit."
    )
    st.stop()

# -------------------------------------------------
# Gemini client
# -------------------------------------------------
client = genai.Client(api_key=API_KEY)
MODEL_ID = "models/gemini-flash-latest"

# -------------------------------------------------
# Styling (clean, child-friendly explainer look)
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
# UI
# -------------------------------------------------
st.title("🌙 A Thousand Whys Before Bedtime")

st.write(
    "✨ A cozy, colorful place where moms turn little **“why?”** questions "
    "into gentle, bedtime-ready stories using AI."
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

Question: {question}
Child age: {age}

Rules:
- Do NOT include bedtime, parents, or story framing
- Do NOT include characters like mommy or daddy
- Focus only on explaining the idea
- Use simple, concrete language
- 4–6 short sections maximum
- Each section explains ONE idea
- Friendly, imaginative, but clear

VERY IMPORTANT FORMAT:
For EACH section:
1. Write 2–3 simple sentences explaining the idea
2. On the next line, write exactly:
[Illustration idea: describe what should be drawn]

Example format:
Water moves around the Earth in big loops.
It falls as rain and flows into rivers.
[Illustration idea: clouds raining over hills and a river flowing to the sea]

Do not add anything else.
"""

        try:
            response = client.models.generate_content(
                model=MODEL_ID,
                contents=prompt
            )

            explanation_text = response.text

            st.subheader("📘 Illustrated Explanation")

            # Split sections using illustration markers
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
                        <div class="explain-text">
                            {text_part}
                        </div>
                        <div class="illustration-text">
                            🎨 Illustration idea: {illustration}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

        except Exception as e:
            st.error("Something went wrong while generating the explanation.")
            st.code(str(e), language="text")

# -------------------------------------------------
# Footer
# -------------------------------------------------
st.markdown("---")
st.caption("💛 Built to help curious kids understand the world")
