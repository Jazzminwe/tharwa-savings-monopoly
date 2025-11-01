import streamlit as st

st.title("🏁 Game Results")

if "player" not in st.session_state:
    st.warning("No player data found. Please start a game first.")
    st.stop()

player = st.session_state.player
fs = st.session_state.facilitator_settings

st.markdown(f"### Congratulations, {player['name']} from Team {player['team']}!")
st.markdown(f"**Total Savings:** SAR {player['savings']:,}")
st.markdown(f"**Savings Goal:** SAR {fs['goal']:,}")
pct = int((player["savings"] / max(1, fs["goal"])) * 100)
st.progress(min(pct / 100, 1))
st.markdown(f"**Goal Achievement:** {pct}%")
st.markdown(f"**Rounds Played:** {player['rounds_played']} of {fs['rounds']}")
st.markdown(f"**Final Energy:** {player['time']} ⚡")
st.markdown(f"**Final Well-being:** {player['emotion']} ❤️")

st.info("📊 A summary or leaderboard for all players can go here later.")
