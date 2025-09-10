
import streamlit as st

st.set_page_config(page_title="Math Games Hub", page_icon="🎮", layout="centered")

st.title("🎮 Math Games Hub")
st.write("Welcome! Choose a game below, or use the sidebar.")

try:
    # Streamlit 1.30+ only
    st.page_link("pages/01_Slope_Showdown.py", label="📈 Slope Showdown — Identify Positive/Negative/Zero/Undefined", icon="➡️")
except Exception:
    st.info("Use the left sidebar to open: 📈 Slope Showdown")

st.divider()
st.caption("Tip: Each game has a Results page where you can download progress CSVs.")
