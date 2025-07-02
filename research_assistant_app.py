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

# === Upload PDF ===
uploaded_file = st.file_uploader("📄 Upload PDF Paper", type="pdf")

# === Session state setup ===
if "summaries" not in st.session_state:
    st.session_state.summaries = {}
if "analysis" not in st.session_state:
    st.session_state.analysis = ""

if uploaded_file:
    try:
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

        # === Summarize Each Section Once ===
        if not st.session_state.summaries:
            summaries = {}
            with st.expander("📘 Summarized Sections", expanded=True):
                for title, content in sections.items():
                    prompt = f"""You are a helpful research assistant.

Summarize the following '{title}' section of a research paper in 4–6 bullet points:

\"\"\"{content}\"\"\""""
                    try:
                        response = client.chat.completions.create(
                            model="gpt-4",
                            messages=[{"role": "user", "content": prompt}],
                            temperature=0.4,
                            max_tokens=600
                        )
                        summary = response.choices[0].message.content.strip()
                        summaries[title] = summary
                        st.markdown(f"### {title.capitalize()}")
                        st.write(summary)
                    except Exception as e:
                        st.error(f"❌ Failed to summarize {title}: {e}")
                st.session_state.summaries = summaries
        else:
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
        
            with st.spinner("🔎 Analyzing your research question..."):
                analysis = analyze_research_opportunities(combined_summary, research_question)
        
            st.subheader("📌 Research Assistant Analysis")
            st.write(analysis)


    else:
        st.warning("⚠️ No recognizable academic sections found in this paper.")

