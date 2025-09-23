import os
import streamlit as st
import requests

st.set_page_config(page_title="FPL Cheat", page_icon="⚽")

st.title("FPL Cheat - MVP")
st.caption("Compare your Fantasy Premier League team with content creators")

# Health check using the API
try:
    # Test API connection
    response = requests.get("https://fpl-cheat.vercel.app/api/", timeout=5)
    if response.status_code == 200:
        st.success("✅ Backend API connected successfully!")
    else:
        st.warning("⚠️ Backend API responded but with unexpected status")
except Exception as e:
    st.error(f"❌ Backend API connection failed: {e}")

# Main UI
st.write("### Team Comparison Tool")
st.write("Enter your FPL team name to compare with content creators...")

# Placeholder for team input
team_name = st.text_input("Enter your FPL team name:")
if st.button("Compare Teams"):
    if team_name:
        st.info(f"Comparing team: {team_name}")
        st.write("This feature will be implemented once we add the FPL API integration.")
    else:
        st.warning("Please enter a team name.")

st.write("### Development Status")
st.info("""
**Current Setup:**
- ✅ Django backend with database models
- ✅ Streamlit frontend deployed on Vercel
- ✅ API endpoint available at /api/
- ⏳ FPL API integration (coming next)
- ⏳ Team comparison logic (coming next)
""")

st.write("### API Endpoints")
st.code("""
GET  /api/           - Health check
POST /api/compare/   - Compare teams (coming soon)
""")
