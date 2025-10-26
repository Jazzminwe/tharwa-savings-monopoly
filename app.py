import streamlit as st
import random
import json
import os

# --------------------------------
# Initialize session state
# --------------------------------
if "players" not in st.session_state:
    st.session_state.players = []

if "current_player" not in st.session_state:
    st.session_state.current_player = 0

if "current_card" not in st.session_state:
    st.session_state.current_card = None

if "facilitator_settings" not in st.session_state:
    st.session_state.facilitator_settings = {"goal": 5000, "income": 2000}

# --------------------------------
# Load cards
# --------------------------------
cards_file = "data/life_cards.json"
if not os.path.exists(cards_file):
    st.error(f"Card file not found: {cards_file}")
    st.stop()

with open(cards_file, "r") as f:
    cards = json.load(f)

# --------------------------------
# Helper functions
# --------------------------------
def apply_effects(player, option):
    player["savings"] += option.get("money", 0)
    player["emotion"] += option.get("wellbeing", 0)
    player["time"] += option.get("time", 0)
    return player

def is_valid_option(player, option):
    if player["savings"] + option.get("money", 0) < 0:
        return False, "Not enough savings for this option!"
    if player["time"] + option.get("time", 0) < 0:
        return False, "Not enough energy/time for this option!"
    if not (0 <= player["emotion"] + option.get("wellbeing", 0) <= 10):
        return False, "Well-being out of range!"
    return True, ""

def format_option_text(opt):
    return f"{opt['text']} → Money: {opt['money']}, Wellbeing: {opt['wellbeing']}, Time: {opt['time']}"

# --------------------------------
# Facilitator setup
# --------------------------------
st.sidebar.header("Facilitator Setup")
goal = st.sidebar.number_input("Savings goal for all", value=st.session_state.facilitator_settings["goal"])
income = st.sidebar.number_input("Monthly income for all", value=st.session_state.facilitator_settings["income"])

# Save facilitator settings
st.session_state.facilitator_settings = {
    "goal": goal,
    "income": income
}

# --------------------------------
# Player setup
# --------------------------------
st.header("Players")
with st.form("add_player_form"):
    team_name = st.text_input("Team Name")
    player_name = st.text_input("Player Name")
    savings_goal_desc = st.text_input("Savings Goal Description")
    needs = st.number_input("Needs allocation", value=int(st.session_state.facilitator_settings["income"]*0.5))
    wants = st.number_input("Wants allocation", value=int(st.session_state.facilitator_settings["income"]*0.25))
    savings_alloc = st.number_input("Savings allocation", value=int(st.session_state.facilitator_settings["income"]*0.25))
    total_alloc = needs + wants + savings_alloc

    if st.form_submit_button("Add Player"):
        if not player_name or not team_name:
            st.warning("Team Name and Player Name are required!")
        elif total_alloc != st.session_state.facilitator_settings["income"]:
            st.warning(f"Total allocation ({total_alloc}) must equal income ({st.session_state.facilitator_settings['income']})")
        else:
            st.session_state.players.append({
                "team_name": team_name,
                "name": player_name,
                "savings_goal_desc": savings_goal_desc,
                "savings": savings_alloc,
                "emotion": 5,
                "time": 5,
                "income": st.session_state.facilitator_settings["income"],
                "allocation": {"needs": needs, "wants": wants, "savings": savings_alloc},
            })
            st.success(f"Player {player_name} added!")

# --------------------------------
# Game logic
# --------------------------------
if st.session_state.players:
    player = st.session_state.players[st.session_state.current_player]

    left_col, right_col = st.columns([2,1])

    with left_col:
        st.subheader(f"Current Player: {player['name']} ({player['team_name']})")

        if st.button("Draw Card"):
            st.session_state.current_card = random.choice(cards)

        card = st.session_state.current_card
        if card:
            st.markdown(f"**Card:** {card['title']}")
            option_choice = st.radio(
                "Choose an option",
                [format_option_text(opt) for opt in card["options"]],
                key=f"choice_{player['name']}"
            )
            selected_option = card["options"][[format_option_text(opt) for opt in card["options"]].index(option_choice)]

            if st.button("Submit Option"):
                valid, msg = is_valid_option(player, selected_option)
                if not valid:
                    st.warning(msg)
                else:
                    # Apply changes
                    st.session_state.players[st.session_state.current_player] = apply_effects(player, selected_option)
                    st.session_state.current_card = None  # Reset card
                    # Move to next player safely
                    st.session_state.current_player = (st.session_state.current_player + 1) % len(st.session_state.players)
                    st.experimental_rerun()

    with right_col:
        st.subheader("Player Status")
        st.markdown(f"**Savings Goal:** {player.get('savings_goal_desc','')}")
        st.markdown(f"**Savings:** {player['savings']}")
        st.markdown(f"**Well-being:** {player['emotion']}")
        st.markdown(f"**Energy:** {player['time']}")
        st.markdown(f"**Allocation:** Needs {player['allocation']['needs']}, Wants {player['allocation']['wants']}, Savings {player['allocation']['savings']}")
