# === research_assistant_app.py ===

import streamlit as st
import fitz  # PyMuPDF
import re
from openai import OpenAI

# === CONFIG ===
st.set_page_config(page_title="AI Research Assistant", layout="wide")
st.title("📚 AI-Powered Research Assistant")
st.markdown("Upload a research paper and get summarized insights + research guidance.")

# === OpenAI client using Streamlit secrets ===
api_key = st.secrets["OPENAI_API_KEY"]
client = OpenAI(api_key=api_key)

# === Upload PDF ===
uploaded_file = st.file_uploader("📄 Upload PDF Paper", type="pdf")

if uploaded_file:
    # === Extract Text from PDF ===
    try:
        doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        full_text = "".join([page.get_text() for page in doc])
        st.success("✅ PDF extracted successfully!")
    except Exception as e:
        st.error(f"❌ Failed to read PDF: {e}")
        st.stop()

    # === Dynamic Section Chunking ===
    def chunk_by_dynamic_headings(text):
        lines = text.split("\n")
        section_starts = []
        for i, line in enumerate(lines):
            if 2 <= len(line.split()) <= 6 and line.strip().istitle():
                section_starts.append((i, line.strip()))

        sections = {}
        for idx in range(len(section_starts)):
            title = section_starts[idx][1].lower()
            start = section_starts[idx][0]
            end = section_starts[idx + 1][0] if idx + 1 < len(section_starts) else len(lines)
            content = "\n".join(lines[start + 1:end]).strip()
            sections[title] = content
        return sections

    sections = chunk_by_dynamic_headings(full_text)

    if sections:
        st.subheader("📑 Detected Sections")
        st.write(list(sections.keys()))

        # === Summarize Each Section ===
        def summarize_section(title, content):
            prompt = f"""You are a helpful research assistant.

Summarize the following '{title}' section of a research paper in 4–6 bullet points:

\"\"\"{content}\"\"\""""

            response = client.chat.completions.create(
                model="gpt-4",
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
        st.warning("⚠️ No valid section headings detected. Try a more structured academic paper.")

