import json

import streamlit as st

from apologetics.answer import answer
from apologetics.config import CLAUDE_MODEL, MANIFEST, TOP_K

st.set_page_config(page_title="Catholic Apologetics Q&A", layout="wide")


def _manifest():
    try:
        return json.loads(MANIFEST.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}


if "history" not in st.session_state:
    st.session_state.history = []

with st.sidebar:
    mode_label = st.radio("Mode", ["Ask", "Rebut"])
    top_k = st.slider("Top-k passages", 4, 15, TOP_K)
    st.caption(f"Model: {CLAUDE_MODEL}")
    manifest = _manifest()
    if manifest:
        st.subheader("Library status")
        for source_id, item in manifest.items():
            st.write(f"{source_id}: {item.get('chunks', 0)} chunks")
    else:
        st.warning("Library is empty — run `python -m apologetics.ingest`")

mode = "rebut" if mode_label == "Rebut" else "ask"
label = "Paste the argument to rebut" if mode == "rebut" else "Your question"
for prior_mode, prior_input, prior_answer in reversed(st.session_state.history):
    st.markdown(f"**{prior_mode.title()}:** {prior_input}")
    st.markdown(prior_answer.text)
    with st.expander("Retrieved passages"):
        for hit in prior_answer.hits:
            st.markdown(f"**[{hit.tag}]** [{hit.source_title} — {hit.section}]({hit.url})")
            st.markdown("> " + hit.text.replace("\n", "\n> "))

user_text = st.text_area(label, height=160)
if st.button("Rebut" if mode == "rebut" else "Answer") and user_text.strip():
    try:
        with st.spinner("Building an evidence-based answer..."):
            result = answer(mode, user_text, top_k)
        st.session_state.history.append((mode, user_text, result))
        st.rerun()
    except (RuntimeError, OSError, ValueError) as exc:
        st.error(str(exc))
