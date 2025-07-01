# === research_assistant_app.py ===

import streamlit as st
import fitz  # PyMuPDF
import re
from openai import OpenAI

# === CONFIG ===
st.set_page_config(page_title="AI Research Assistant", layout="wide")
st.title("📚 AI-Powered Research Assistant")
st.markdown("Upload a research paper and get summarized insights + research guidance.")

# === OpenAI client from secrets ===
api_key = st.secrets["OPENAI_API_KEY"]
client = OpenAI(api_key=api_key)

# === File Upload ===
uploaded_file = st.file_uploader("📄 Upload PDF Paper", type="pdf")

if uploaded_file:
    # === Extract Text from PDF ===
    doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
    full_text = "".join([page.get_text() for page in doc])
    st.success("✅ PDF extracted successfully!")

    # === Split by Sections ===
    def chunk_by_sections(text):
        pattern = r'\n(?=\s*(Abstract|Introduction|Background|Methodology|Methods|Results|Findings|Discussion|Conclusion|References))'
        chunks = re.split(pattern, text, flags=re.IGNORECASE)
        return {chunks[i].strip().lower(): chunks[i+1].strip() for i in range(1, len(chunks)-1, 2)}

    sections = chunk_by_sections(full_text)

    if sections:
        st.subheader("📑 Detected Sections")
        st.write(list(sections.keys()))

        # === Summarize Each Section ===
        def summarize_section(title, content):
            prompt = f"""You are a helpful research assistant.

Summarize the following '{title}' section of a research paper in 4–6 bullet points:

\"\"\"{content}\"\"\""""

            response = client.chat.completions.create(
                model="gpt-4",  # default model
                messages=[{"role": "user", "content": prompt}],
                temperature=0.4,
                max_tokens=600
            )
            return response.choices[0].message.content.strip()

        summaries = {}
        with st.expander("📘 Summarized Sections", expanded=True):
            for title, content in sections.items():
                summary = summarize_section(title, content)
                summaries[title] = summary
                st.markdown(f"### {title.capitalize()}")
                st.write(summary)

        # === Research Question Input ===
        st.subheader("🧠 Your Research Question")
        research_question = st.text_area("Enter your research question or area of interest:")

        if st.button("🔍 Analyze My Research Question") and research_question:
            combined_summary = "\n\n".join(
                [f"{k.capitalize()}:\n{v}" for k, v in summaries.items()]
            )

            def analyze_research_opportunities(summary_text, research_question):
                prompt = f"""
You are an expert academic research assistant.

The following is a summarized paper:
\"\"\"{summary_text}\"\"\"

And here is a research question:
\"{research_question}\"

Please:
1. List 3–5 limitations in the original paper.
2. Identify 3 gaps or unexplored issues.
3. Suggest how this research question can be explored in a new study.

Use bullet points.
"""
                response = client.chat.completions.create(
                    model="gpt-4",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,
                    max_tokens=1000
                )
                return response.choices[0].message.content.strip()

            analysis = analyze_research_opportunities(combined_summary, research_question)
            st.subheader("📌 Research Assistant Analysis")
            st.write(analysis)
    else:
        st.warning("⚠️ No standard sections (Abstract, Introduction, etc.) found in this PDF.")

        analysis = analyze_research_opportunities(combined_summary, research_question)
        st.subheader("📌 Research Assistant Analysis")
        st.write(analysis)
