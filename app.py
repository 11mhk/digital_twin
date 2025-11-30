# main entry file for the Streamlit app
import streamlit as st

st.title("CO₂ Capture Digital Twin")
st.write("This is the main app file. Pages will load from the pages/ folder.")


from pathlib import Path

st.set_page_config(
    page_title="VayuVision",
    layout="wide",
    initial_sidebar_state="expanded",
)

def load_local_css(css_path: str):
    css_path = Path(css_path)
    if css_path.exists():
        with open(css_path) as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# 🔥 load global CSS
load_local_css("assets/style.css")
