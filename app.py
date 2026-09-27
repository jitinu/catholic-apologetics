import json

import streamlit as st
from google.genai import errors

from apologetics.answer import answer
from apologetics.config import GEMINI_MODEL, MANIFEST, TOP_K

st.set_page_config(page_title="Catholic Apologetics Q&A", layout="wide")


def _manifest():
    try:
        return json.loads(MANIFEST.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}


if "history" not in st.session_state:
    st.session_state.history = []

with st.sidebar:
    top_k = st.slider("Top-k passages", 4, 15, TOP_K)
    st.caption(f"Model: {GEMINI_MODEL}")
    manifest = _manifest()
    if manifest:
        st.subheader("Library status")
        for source_id, item in manifest.items():
            st.write(f"{source_id}: {item.get('chunks', 0)} chunks")
    else:
        st.warning("Library is empty — run `python -m apologetics.ingest`")

for prior_input, prior_answer in reversed(st.session_state.history):
    st.markdown(f"**You:** {prior_input}")
    st.markdown(prior_answer.text)
    with st.expander("Retrieved passages"):
        for hit in prior_answer.hits:
            st.markdown(f"**[{hit.tag}]** [{hit.source_title} — {hit.section}]({hit.url})")
            st.markdown("> " + hit.text.replace("\n", "\n> "))

user_text = st.text_area("Ask a question or paste an argument to rebut", height=160)
if st.button("Answer"):
    if not user_text.strip():
        st.warning("Enter a question or an argument first.")
    else:
        try:
            with st.spinner("Building an evidence-based answer..."):
                result = answer(user_text, top_k)
            st.session_state.history.append((user_text, result))
            st.rerun()
        except (errors.APIError, RuntimeError, OSError, ValueError) as exc:
            st.error(str(exc))
