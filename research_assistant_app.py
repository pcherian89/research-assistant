import streamlit as st
import fitz  # PyMuPDF
import re
from openai import OpenAI

# === Load OpenAI key from Streamlit secrets ===
api_key = st.secrets["OPENAI_API_KEY"]
client = OpenAI(api_key=api_key)

# === SETUP ===
st.set_page_config(page_title="AI Research Assistant", layout="wide")
st.title("📚 AI-Powered Research Assistant")
mode = st.radio("Choose Mode", ["📄 Analyze One Paper", "📚 Build Literature Review"])
if mode == "📄 Analyze One Paper":
    # all your existing code

    st.markdown("Upload a research paper and get summarized insights + research guidance.")
    
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
                        prompt = f"""You are an expert academic research assistant specializing in synthesizing scholarly literature.
    
                        Carefully read the following '{title}' section from a research paper and produce a **high-quality summary** in 4–6 bullet points that:
                        - Identifies key arguments, findings, or methodologies
                        - Uses precise academic language
                        - Highlights nuanced points or theoretical insights where relevant
                        - Omits redundant or general filler content
                        
                        Text to summarize:
                        \"\"\"{content}\"\"\"
                        """
    
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
            You are an experienced academic research advisor.
            
            Below is a summary of a research paper:
            \"\"\"{combined_summary}\"\"\"
            
            And here is a new research question proposed by the user:
            \"{research_question}\"
            
            Your task is to critically analyze the summary and offer insights that will help the user refine or extend their research idea. Specifically:
            
            1. Identify 3–5 **methodological or conceptual limitations** in the original study. Be specific (e.g., sample issues, lack of longitudinal data, theoretical bias, etc.).
            2. Point out 3 **gaps, blind spots, or underexplored dimensions** that are either unaddressed or only weakly examined.
            3. Offer **clear, researchable suggestions** for how the new research question can be pursued in a future study (e.g., potential data sources, methods, populations, frameworks).
            
            Ensure your response is structured, precise, and uses formal academic tone.
            Use bullet points under each section.
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

elif mode == "📚 Build Literature Review":
    st.subheader("📚 Upload 2–5 Research Papers for Literature Review")
    uploaded_files = st.file_uploader("Upload multiple PDFs", type="pdf", accept_multiple_files=True)

    if uploaded_files and len(uploaded_files) <= 5:
        if "lit_summaries" not in st.session_state:
            st.session_state.lit_summaries = []

        if st.button("✏️ Generate Summaries for Each Paper"):
            import fitz
            st.info("⏳ Summarizing papers one by one. Please wait...")

            st.session_state.lit_summaries = []

            for idx, file in enumerate(uploaded_files):
                try:
                    doc = fitz.open(stream=file.read(), filetype="pdf")
                    full_text = "".join([page.get_text() for page in doc])
                    # === Extract Author and Year from Metadata or First Page ===
                    metadata = doc.metadata
                    title = metadata.get("title", "Untitled Paper")
                    author = metadata.get("author", "Unknown Author")
                    
                    # Try to find year from metadata or fallback to first page
                    year = "Unknown Year"
                    first_page_text = doc[0].get_text()
                    import re
                    year_match = re.search(r"(19|20)\d{2}", first_page_text)
                    if year_match:
                        year = year_match.group()
                    
                    # Create citation string for this paper
                    citation_info = f"{author} ({year})"

                    chunks = [full_text[i:i+8000] for i in range(0, len(full_text), 8000)]

                    partial_summaries = []
                    for i, chunk in enumerate(chunks):
                        chunk_prompt = f'''
You are an academic assistant.

This section is from a paper authored by {citation_info}.

Summarize the section in bullet points, and **include the author name and year once** so the summary can be cited in APA format.

Focus on:
- Main topic and purpose
- Research question (if stated)
- Methodology
- Key findings
- Limitations
- Contribution to the field

Use formal academic tone.

\"\"\"{chunk}\"\"\"
'''

                        response = client.chat.completions.create(
                            model="gpt-3.5-turbo",
                            messages=[{"role": "user", "content": chunk_prompt}],
                            temperature=0.4,
                            max_tokens=700
                        )
                        partial_summaries.append(response.choices[0].message.content.strip())

                    full_summary = "\n".join(partial_summaries)
                    st.session_state.lit_summaries.append(full_summary)

                    st.markdown(f"### 📘 Summary of Paper {idx + 1}")
                    st.markdown(full_summary)

                except Exception as e:
                    st.error(f"❌ Failed to summarize paper {idx + 1}: {e}")

        # Show research question input regardless of summaries
        st.markdown("🧠 **What is your research question or focus?**")
        research_question_multi = st.text_area(
            "Enter your research question to guide the literature review synthesis.",
            key="lit_review_question"
        )

        if st.button("📌 Build Literature Review") and research_question_multi and st.session_state.lit_summaries:
            summaries_text = "\n\n".join(st.session_state.lit_summaries)
            synth_prompt = f"""
You are an academic assistant.

Based on the following summaries of academic papers:
\"\"\"{summaries_text}\"\"\"

And the research question:
\"{research_question_multi}\"

Write a 300–500 word literature review using proper APA style, with:
- Author-year **in-text citations** integrated naturally within sentences (e.g., "Liao and Craig (2023) found that..." or "...as shown in recent studies (Willson & Kerr, 2023)")
- Avoid repeating the same citation multiple times in one paragraph
- Cite each paper only when relevant to a specific point
- Do **not** include page numbers
- Include a “References” section at the end, formatted in APA style using the filenames provided:
{[file.name for file in uploaded_files]}

The review should include:
- Common themes across the papers
- Conflicting findings or disagreements
- Methodological similarities or differences
- Gaps in current literature
- How these studies relate to the research question

Use a formal academic tone and clear structure.
"""


            with st.spinner("🧠 Synthesizing literature review..."):
                try:
                    final_response = client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=[{"role": "user", "content": synth_prompt}],
                        temperature=0.4,
                        max_tokens=1000
                    )
                    lit_review_output = final_response.choices[0].message.content.strip()
                    st.subheader("📌 Literature Review")
                    st.write(lit_review_output)

                    st.download_button(
                        label="⬇️ Download Literature Review",
                        data=lit_review_output,
                        file_name="literature_review.txt",
                        mime="text/plain"
                    )

                    # Re-show all summaries for reference
                    st.subheader("📘 Summaries Recap")
                    for i, summary in enumerate(st.session_state.lit_summaries):
                        st.markdown(f"**Summary of Paper {i + 1}**")
                        st.markdown(summary)

                except Exception as e:
                    st.error(f"❌ Failed to generate literature review: {e}")

    elif uploaded_files and len(uploaded_files) > 5:
        st.warning("Please upload 5 or fewer PDFs.")



