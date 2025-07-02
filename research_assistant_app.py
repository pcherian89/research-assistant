import streamlit as st
import fitz  # PyMuPDF
import re
from openai import OpenAI

# === SETUP ===
st.set_page_config(page_title="AI Research Assistant", layout="wide")
st.title("📚 AI-Powered Research Assistant")
st.markdown("Upload a research paper and get summarized insights + research guidance.")

# === Load OpenAI key from Streamlit secrets ===
api_key = st.secrets["OPENAI_API_KEY"]
client = OpenAI(api_key=api_key)

# === Session state setup ===
if "summaries" not in st.session_state:
    st.session_state.summaries = {}
if "analysis" not in st.session_state:
    st.session_state.analysis = ""

# === Upload PDF ===
uploaded_file = st.file_uploader("📄 Upload PDF Paper", type="pdf")

if uploaded_file:
    try:
        # === Extract text from PDF ===
        doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        full_text = "".join([page.get_text() for page in doc])
        st.success("✅ PDF extracted successfully!")
    except Exception as e:
        st.error(f"❌ Failed to read PDF: {e}")
        st.stop()

    # === Chunk by Known Academic Headings ===
    def chunk_by_standard_sections(text):
        pattern = r"\n(?=\s*(Abstract|Introduction|Background|Literature Review|Theoretical Framework|Methodology|Methods|Results|Findings|Discussion|Conclusion|References))"
        chunks = re.split(pattern, text, flags=re.IGNORECASE)
        section_dict = {}
        for i in range(1, len(chunks), 2):
            section = chunks[i].strip().lower()
            content = chunks[i + 1].strip()
            section_dict[section] = content
        return section_dict

    sections = chunk_by_standard_sections(full_text)

    if sections:
        st.subheader("📑 Detected Sections")
        st.write(list(sections.keys()))

        # === Summarize Button ===
        if st.button("🧾 Summarize Sections"):
            with st.spinner("📝 Summarizing..."):
                def summarize_section(title, content):
                    prompt = f"""You are a helpful research assistant.

Summarize the following '{title}' section of a research paper in 4–6 bullet points:

\"\"\"{content}\"\"\""""
                    response = client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.4,
                        max_tokens=600
                    )
                    return response.choices[0].message.content.strip()

                summaries = {}
                for title, content in sections.items():
                    summaries[title] = summarize_section(title, content)
                st.session_state.summaries = summaries
                st.success("✅ Summarization complete!")

    else:
        st.warning("⚠️ No recognizable academic sections found in this paper.")

# === Display Summarized Sections ===
if st.session_state.summaries:
    with st.expander("📘 Summarized Sections", expanded=True):
        for title, summary in st.session_state.summaries.items():
            st.markdown(f"### {title.capitalize()}")
            st.write(summary)

    # === Research Question Input ===
    st.subheader("🧠 Your Research Question")
    research_question = st.text_area("Enter your research question or area of interest:")

    if st.button("🔍 Analyze My Research Question") and research_question:
        combined_summary = "\n\n".join(
            [f"{k.capitalize()}:\n{v}" for k, v in st.session_state.summaries.items()]
        )

        prompt = f"""
You are an expert academic research assistant.

The following is a summarized paper:
\"\"\"{combined_summary}\"\"\"

And here is a research question:
\"{research_question}\"

Please:
1. List 3–5 limitations in the original paper.
2. Identify 3 gaps or unexplored issues.
3. Suggest how this research question can be explored in a new study.

Use bullet points.
"""
        with st.spinner("🔎 Analyzing your research question..."):
            try:
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,
                    max_tokens=1000
                )
                st.session_state.analysis = response.choices[0].message.content.strip()
                st.success("✅ Analysis complete!")
            except Exception as e:
                st.error(f"❌ Failed to analyze research question: {e}")

# === Show analysis if already done ===
if st.session_state.analysis:
    st.subheader("📌 Research Assistant Analysis")
    st.write(st.session_state.analysis)

from io import BytesIO
from reportlab.lib.pagesizes import LETTER
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch

# === PDF Download ===
if st.session_state.summaries and st.session_state.analysis:
    st.subheader("📥 Download Summary + Analysis as PDF")

    # Generate content
    summary_text = "\n\n".join(
        [f"{k.upper()}\n{v}" for k, v in st.session_state.summaries.items()]
    )

    full_text = f"""AI Research Assistant Output

--- SECTION SUMMARIES ---

{summary_text}

--- RESEARCH QUESTION ---

{research_question}

--- ANALYSIS ---

{st.session_state.analysis}
"""

    # Generate PDF in memory
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=LETTER)
    width, height = LETTER

    # Function to split long text into lines
    def draw_wrapped_text(c, text, x, y, max_width, line_height):
        from textwrap import wrap
        lines = text.split("\n")
        for line in lines:
            wrapped = wrap(line, width=100)
            for wrap_line in wrapped:
                if y < 1 * inch:
                    c.showPage()
                    y = height - 1 * inch
                c.drawString(x, y, wrap_line)
                y -= line_height
        return y

    pdf.setFont("Helvetica", 11)
    y = height - 1 * inch
    x = 1 * inch
    y = draw_wrapped_text(pdf, full_text, x, y, width - 2 * inch, 14)
    pdf.save()

    buffer.seek(0)

    # Show download button
    st.download_button(
        label="⬇️ Download as PDF",
        data=buffer,
        file_name="research_summary_analysis.pdf",
        mime="application/pdf"
    )
