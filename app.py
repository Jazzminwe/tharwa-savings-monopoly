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
        return json.load(f)

def first_number_in_text(text):
    m = re.search(r"(-?\d+)", text)
    if m:
        return int(m.group(1))
    return None

def apply_effects(state, option):
    state["savings"] = max(0, state["savings"] + option.get("money", 0))
    state["emotion"] = max(0, min(10, state["emotion"] + option.get("wellbeing", 0)))
    state["time"] = max(0, min(10, state["time"] + option.get("time", 0)))
    return state

def summary_code(team_name, player_name, percent_goal, emotion, time_val):
    t = re.sub(r"\s+", "", team_name)[:6]
    p = re.sub(r"\s+", "", player_name)[:6]
    return f"{t}_{p}_{int(percent_goal)}p_E{int(emotion)}_T{int(time_val)}"

# -------------------------
# Streamlit UI
# -------------------------
st.set_page_config(page_title="Savings Monopoly - Prototype", layout="centered")

# Load cards
cards = load_cards()

# -------------------------
# Session state initialization
# -------------------------
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

# -------------------------
# Sidebar - facilitator / settings
# -------------------------
with st.sidebar:
    st.header("Facilitator / Settings")
    rounds = st.number_input("Rounds per game (months)", min_value=1, max_value=12,
                             value=st.session_state.settings["rounds"])
    income_default = st.number_input("Monthly income (SAR)", min_value=1000, max_value=20000,
                                     value=st.session_state.settings["income_default"])
    goal_amount = st.number_input("Savings goal amount (SAR)", min_value=500, max_value=200000,
                                  value=st.session_state.settings["goal_amount"])
    start_new = st.button("Start new game")
    st.session_state.settings.update({"rounds": rounds, "income_default": income_default, "goal_amount": goal_amount})

if start_new:
    st.session_state.round = 0
    st.session_state.history = []
    st.session_state.current_card = None
    st.session_state.game_started = False

# -------------------------
# Player / Team Setup
# -------------------------
with st.form("player_setup", clear_on_submit=False):
    st.subheader("Player / Team Setup")
    team_name = st.text_input("Team name", value="TeamA")
    player_name = st.text_input("Player name", value="Player1")
    goal_desc = st.text_input("Savings goal description", value="Trip / Purchase")
    income = st.number_input("Monthly income (SAR)", min_value=100, max_value=20000,
                             value=st.session_state.settings["income_default"])
    col1, col2, col3 = st.columns(3)
    with col1:
        needs = st.number_input("Needs (SAR)", min_value=0, value=int(income*0.5))
    with col2:
        wants = st.number_input("Wants (SAR)", min_value=0, value=int(income*0.3))
    with col3:
        savings_alloc = st.number_input("Savings (SAR)", min_value=0, value=int(income*0.2))
    submit_setup = st.form_submit_button("Confirm setup and start game")

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
    st.session_state.game_started = True
    st.session_state.history = []
    st.session_state.current_card = None

if not st.session_state.get("game_started"):
    st.info("Fill the Player / Team setup and press 'Confirm setup and start game' to begin.")
    st.stop()

player = st.session_state.player

# -------------------------
# Main UI
# -------------------------
left, right = st.columns([2, 1])

with right:
    st.subheader("Player Stats")
    st.write(f"**Team:** {player['team_name']}  \n**Player:** {player['player_name']}")
    st.write(f"**Goal:** {player['goal_desc']} — SAR {player['goal_amount']}")
    st.metric("Round", f"{st.session_state.round}/{st.session_state.settings['rounds']}")
    st.write(f"**Savings so far:** SAR {player['savings']}")
    st.write(f"💙 Well-being: {player['emotion']}/10")
    st.write(f"⏳ Time/Energy: {player['time']}/10")
    pct = min(100, int(player['savings']/player['goal_amount']*100))
    st.progress(pct)

with left:
    st.subheader("Game Area")
    if st.session_state.round >= st.session_state.settings["rounds"]:
        st.success("Game finished")
    else:
        if st.session_state.current_card is None:
            if st.button("Draw Card"):
                st.session_state.current_card = random.choice(cards)
        else:
            card = st.session_state.current_card
            st.markdown(f"**Card:** {card['title']} ({card['type']})")
            st.write("---")
            # show options
            option_labels = [opt["text"] for opt in card.get("options", [])]
            selected_label = st.radio("Choose an option", option_labels)
            if st.button("Confirm choice"):
                # apply effects
                selected_option = next(opt for opt in card["options"] if opt["text"] == selected_label)
                player = apply_effects(player, selected_option)
                st.session_state.player = player
                st.session_state.history.append({
                    "round": st.session_state.round+1,
                    "card": card,
                    "choice": selected_option
                })
                st.session_state.round += 1
                st.session_state.current_card = None

# -------------------------
# History and Summary
# -------------------------
st.write("---")
st.subheader("Recent Actions")
for h in st.session_state.history[-5:][::-1]:
    st.write(f"Round {h['round']}: {h['card']['title']} ({h['card']['type']})")
    st.write(f"Chose: {h['choice']['text']} → Savings: {player['savings']}, 💙 {player['emotion']}, ⏳ {player['time']}")
    st.write("---")

if st.session_state.round >= st.session_state.settings["rounds"]:
    st.subheader("Game Summary")
    pct_goal = min(100, int(player['savings']/player['goal_amount']*100))
    st.write(f"Final savings: SAR {player['savings']} ({pct_goal}% of goal)")
    st.write(f"Well-being: {player['emotion']}/10")
    st.write(f"Time/Energy: {player['time']}/10")
    st.code(summary_code(player['team_name'], player['player_name'], pct_goal, player['emotion'], player['time']))
