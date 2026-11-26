import streamlit as st
from wikipedia_extractor_core import (
    WikipediaExtractor, safe_filename, numbered_filename, format_txt,
)

st.set_page_config(page_title="Wikipedia Extractor", layout="wide")

for k, default in {
    "topic": None, "article": None, "titles": [], "selected": [],
    "sections": [], "downloaded_filenames": [],
}.items():
    if k not in st.session_state:
        st.session_state[k] = default

with st.sidebar:
    st.header("Controls")
    if st.button("Start Over"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

c1, c2, c3, c4 = st.columns(4)
c1.caption(("✅ " if st.session_state.topic else "⬜ ") + "Search")
c2.caption(("✅ " if st.session_state.titles else "⬜ ") + "Select")
c3.caption(("✅ " if st.session_state.sections else "⬜ ") + "Extract")
c4.caption(("✅ " if st.session_state.downloaded_filenames else "⬜ ") + "Download")

st.title("Wikipedia Article Extractor")
with st.expander("How to use this app"):
    st.markdown("1. Enter a topic\n2. Select sections from the list\n3. Click Extract\n4. Click Download")

with st.form("search_form"):
    topic = st.text_input("Enter a topic")
    submitted = st.form_submit_button("Search")

if submitted and topic.strip():
    st.session_state.topic = topic.strip()
    article = WikipediaExtractor(st.session_state.topic)
    st.session_state.article = article
    if article.error:
        st.error(article.error)
        st.session_state.titles = []
        st.session_state.selected = []
        st.session_state.sections = []
    else:
        st.success(f"Found: {article.title}")
        st.write(article.url)
        st.session_state.titles = article.section_titles()
        st.session_state.selected = []
        st.session_state.sections = []
        if len(st.session_state.titles) <= 1:
            st.warning("This article has no usable sections.")

if st.session_state.titles:
    st.session_state.selected = st.multiselect(
        "Select sections",
        options=st.session_state.titles,
        default=st.session_state.selected,
    )

if st.button("Extract"):
    if not st.session_state.selected:
        st.warning("Select at least one section before extracting.")
    else:
        st.session_state.sections = [
            st.session_state.article.extract(t) for t in st.session_state.selected
        ]

if st.session_state.sections:
    with st.container(border=True):
        for section in st.session_state.sections:
            st.markdown(f"### {section['title']}")
            if not section["blocks"]:
                st.caption("(no extractable content)")
            for block in section["blocks"]:
                if block["type"] == "paragraph":
                    st.write(block["text"])
                elif block["type"] == "subheading":
                    st.markdown(f"#### {block['text']}")
                elif block["type"] == "list":
                    marker = "1." if block.get("ordered") else "-"
                    for item in block["items"]:
                        st.markdown(f"{marker} {item}")
                elif block["type"] == "table":
                    st.dataframe(block["rows"])

if st.session_state.sections:
    article = st.session_state.article
    base = safe_filename(article.title)
    proposed = base + ".txt"
    if proposed in st.session_state.downloaded_filenames:
        st.warning("You already downloaded this name this session. A (2) suffix will be added.")
    fname = numbered_filename(base, st.session_state.downloaded_filenames, ".txt")
    content = format_txt(article.title, article.url, st.session_state.sections)
    if st.download_button(
        "Download .txt",
        data=content,
        file_name=fname,
        mime="text/plain",
        key="download_btn",
        on_click="ignore",
    ):
        if fname not in st.session_state.downloaded_filenames:
            st.session_state.downloaded_filenames.append(fname)

st.caption("Content from Wikipedia, CC BY-SA 4.0.")
st.write(st.session_state)