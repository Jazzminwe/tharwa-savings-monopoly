# app.py
import streamlit as st
import json
import random
import re
from pathlib import Path

# -------------------------
# Utility functions
# -------------------------
def load_cards(path="data/life_cards.json"):
    p = Path(path)
    if not p.exists():
        st.error(f"Cards file not found at {path}. Please add data/life_cards.json")
        return []
    with open(p, "r", encoding="utf-8") as f:
        cards = json.load(f)
    # ensure each card has required fields
    for c in cards:
        c.setdefault("type", "Neutral")
        c.setdefault("title", "")
        c.setdefault("options", [])
    return cards

def apply_effects(state, option):
    """Apply the effects from a chosen card option."""
    state["savings"] = max(0, state["savings"] + option.get("money", 0))
    state["emotion"] = max(0, min(10, state["emotion"] + option.get("wellbeing", 0)))
    state["time"] = max(0, min(10, state["time"] + option.get("time", 0)))
    return state

def summary_code(team_name, player_name, percent_goal, emotion, time_val):
    t = re.sub(r"\s+", "", team_name)[:6]
    p = re.sub(r"\s+", "", player_name)[:6]
    return f"{t}_{p}_{int(percent_goal)}p_E{int(emotion)}_T{int(time_val)}"

# -------------------------
# Streamlit UI and state
# -------------------------
st.set_page_config(page_title="Savings Monopoly", layout="centered")

# Load cards
cards = load_cards()
if not cards:
    st.stop()

# Initialize session state
if "initialized" not in st.session_state:
    st.session_state.initialized = True
    st.session_state.round = 0
    st.session_state.history = []
    st.session_state.current_card = None
    st.session_state.game_started = False
    st.session_state.settings = {
        "rounds": 4,
        "income_default": 4000,
        "goal_amount": 10000
    }

# Sidebar - facilitator / settings
with st.sidebar:
    st.header("Facilitator / Settings")
    rounds = st.number_input("Rounds per game (months)", min_value=1, max_value=12,
                             value=st.session_state.settings["rounds"])
    income_default = st.number_input("Monthly income (SAR)", min_value=1000, max_value=20000,
                                     value=st.session_state.settings["income_default"], step=100)
    goal_amount = st.number_input("Savings goal amount (SAR, same for all)", min_value=500, max_value=200000,
                                  value=st.session_state.settings["goal_amount"], step=100)
    start_new = st.button("Start new game (resets session)")
    st.session_state.settings.update({
        "rounds": rounds,
        "income_default": income_default,
        "goal_amount": goal_amount
    })

# Safely handle "Start new game"
if start_new:
    st.session_state.round = 0
    st.session_state.history = []
    st.session_state.current_card = None
    st.session_state.game_started = False
    st.session_state.player = None
    st.experimental_rerun()

# --- Player setup ---
if not st.session_state.get("game_started"):
    st.subheader("Player / Team Setup")
    team_name = st.text_input("Team name (for your device)", value="TeamA")
    player_name = st.text_input("Player name", value="Player1")
    goal_desc = st.text_input("Savings goal description", value="Trip / Purchase")
    income = st.number_input("Monthly income (SAR)", min_value=100, max_value=20000,
                             value=st.session_state.settings["income_default"], step=100)
    col1, col2, col3 = st.columns(3)
    with col1:
        needs = st.number_input("Needs (SAR)", min_value=0, value=int(income*0.5), step=50)
    with col2:
        wants = st.number_input("Wants (SAR)", min_value=0, value=int(income*0.3), step=50)
    with col3:
        savings_alloc = st.number_input("Savings (SAR)", min_value=0, value=int(income*0.2), step=50)
    submit_setup = st.button("Confirm setup and start game")

    if submit_setup:
        st.session_state.player = {
            "team_name": team_name,
            "player_name": player_name,
            "goal_desc": goal_desc,
            "goal_amount": st.session_state.settings["goal_amount"],
            "income": income,
            "needs_alloc": needs,
            "wants_alloc": wants,
            "savings": savings_alloc,
            "emotion": 5,
            "time": 5
        }
        st.session_state.round = 0
        st.session_state.history = []
        st.session_state.current_card = None
        st.session_state.game_started = True
        st.experimental_rerun()

st.title("Savings Monopoly — Workshop Prototype")

# Stop if game not started
if not st.session_state.get("game_started"):
    st.info("Fill the Player / Team setup and press 'Confirm setup and start game' to begin.")
    st.stop()

player = st.session_state.player

# --- Main game UI ---
left, right = st.columns([2, 1])

with right:
    st.subheader("Player Stats")
    st.markdown(f"**Team:** {player['team_name']}  \n**Player:** {player['player_name']}")
    st.markdown(f"**Goal:** {player['goal_desc']} — SAR {player['goal_amount']}")
    st.metric("Round", f"{st.session_state.round}/{st.session_state.settings['rounds']}")
    st.write("---")
    st.write(f"**Income (monthly):** SAR {player['income']}")
    st.write(f"**Allocations:** Needs: SAR {player['needs_alloc']}, Wants: SAR {player['wants_alloc']}, Savings: SAR {player['savings']}")
    st.write("---")
    st.write(f"**Savings so far:** SAR {player['savings']}")
    st.write(f"**Well-being (💙):** {player['emotion']} / 10")
    st.write(f"**Time/Energy (⏳):** {player['time']} / 10")
    pct = min(100, int(player['savings'] / max(1, player['goal_amount']) * 100))
    st.progress(pct)
    st.write(f"% goal: {pct}%")
    st.write("---")
    if st.button("Reset this game"):
        st.session_state.game_started = False
        st.experimental_rerun()

with left:
    st.subheader("Game Area")
    rounds_total = st.session_state.settings["rounds"]

    if st.session_state.round >= rounds_total:
        st.success("Game finished — see summary on the right and at the bottom.")
    else:
        if st.session_state.current_card is None:
            if st.button("Draw Card"):
                card = random.choice(cards)
                st.session_state.current_card = card
                st.experimental_rerun()
        else:
            card = st.session_state.current_card
            st.markdown(f"**Card type: {card['type']}**")
            st.markdown(f"**{card['title']}**")
            st.write("---")
            st.markdown("**Choose one response:**")
            options = card.get("options", [])
            labels = [opt["text"] for opt in options]
            choice = st.radio("Response", labels, index=0)
            if st.button("Confirm choice"):
                chosen_option = options[labels.index(choice)]
                player = apply_effects(player, chosen_option)
                st.session_state.history.append({
                    "round": st.session_state.round + 1,
                    "card": card,
                    "choice": chosen_option,
                    "resulting_state": {"savings": player["savings"], "emotion": player["emotion"], "time": player["time"]}
                })
                st.session_state.round += 1
                st.session_state.current_card = None
                st.session_state.player = player
                st.experimental_rerun()

# --- History and summary ---
st.write("---")
st.subheader("Recent actions")
if st.session_state.history:
    last = st.session_state.history[-5:][::-1]
    for h in last:
        st.write(f"Round {h['round']}: {h['card']['type']} — {h['card']['title']}")
        st.write(f"Chose: {h['choice']['text']} → Savings now SAR {h['resulting_state']['savings']} — 💙 {h['resulting_state']['emotion']} — ⏳ {h['resulting_state']['time']}")
        st.write("----")
else:
    st.write("No actions yet this game.")

if st.session_state.round >= st.session_state.settings["rounds"]:
    st.markdown("## Game Summary")
    percent_goal = min(100, (player["savings"] / max(1, player["goal_amount"])) * 100)
    st.write(f"**Final savings:** SAR {player['savings']}")
    st.write(f"**% of goal achieved:** {int(percent_goal)}%")
    st.write(f"**Final well-being (💙):** {player['emotion']} / 10")
    st.write(f"**Final time/energy (⏳):** {player['time']} / 10")
    code = summary_code(player["team_name"], player["player_name"], percent_goal, player["emotion"], player["time"])
    st.write("Shareable summary code:")
    st.code(code)
