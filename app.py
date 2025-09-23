import streamlit as st

st.set_page_config(page_title="FPL Cheat", page_icon="⚽")

st.title("FPL Cheat - MVP")
st.caption("Compare your Fantasy Premier League team with content creators")

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
- ✅ Streamlit frontend deployed on Vercel
- ⏳ Backend API integration (coming next)
- ⏳ FPL API integration (coming next)
- ⏳ Team comparison logic (coming next)
""")

st.write("### About FPL Cheat")
st.write("""
This app will help you compare your Fantasy Premier League team with popular content creators 
to see how similar your squad is to theirs. Enter your team name above to get started!
""")
