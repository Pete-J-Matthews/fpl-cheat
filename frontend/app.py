import os
import requests
import streamlit as st

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

st.set_page_config(page_title="FPL Cheat", page_icon="⚽")

st.title("FPL Cheat - MVP")
st.caption("Streamlit UI connected to Django backend")

col1, col2 = st.columns(2)
with col1:
    if st.button("Health check backend"):
        try:
            resp = requests.get(f"{BACKEND_URL}/health/", timeout=10)
            st.success(resp.json())
        except Exception as exc:  # noqa: BLE001
            st.error(f"Failed to reach backend: {exc}")

with col2:
    st.write("More UI coming soon…")

