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
    st.session_state.facilitator_settings = {
        "goal": 5000,
        "income": 2000,
        "allocation": {"needs": 1000, "wants": 500, "savings": 500}
    }

# --------------------------------
# Load cards safely
# --------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
cards_file = os.path.join(BASE_DIR, "cards.json")

try:
    with open(cards_file, "r") as f:
        cards = json.load(f)
except FileNotFoundError:
    st.warning("cards.json not found. Using default sample card.")
    cards = [
        {
            "title": "Sample Card",
            "options": [
                {"text": "Do nothing", "money": 0, "wellbeing": 0, "time": 0},
                {"text": "Save 100", "money": 100, "wellbeing": 1, "time": -1},
            ],
        }
    ]

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
goal = st.sidebar.number_input(
    "Savings goal", value=st.session_state.facilitator_settings["goal"]
)
income = st.sidebar.number_input(
    "Monthly income", value=st.session_state.facilitator_settings["income"]
)
needs = st.sidebar.number_input(
    "Needs allocation", value=st.session_state.facilitator_settings["allocation"]["needs"]
)
wants = st.sidebar.number_input(
    "Wants allocation", value=st.session_state.facilitator_settings["allocation"]["wants"]
)
savings_alloc = st.sidebar.number_input(
    "Savings allocation", value=st.session_state.facilitator_settings["allocation"]["savings"]
)

total_alloc = needs + wants + savings_alloc
if total_alloc != income:
    st.sidebar.error(f"Total allocation (needs+wants+savings={total_alloc}) must equal income ({income})")
    st.stop()

# Save facilitator settings
st.session_state.facilitator_settings = {
    "goal": goal,
    "income": income,
    "allocation": {"needs": needs, "wants": wants, "savings": savings_alloc},
}

# --------------------------------
# Player setup
# --------------------------------
st.header("Players")
player_name = st.text_input("Enter your name")

if st.button("Add Player") and player_name:
    st.session_state.players.append({
        "name": player_name,
        "savings": savings_alloc,
        "emotion": 5,
        "time": 5,
        "income": income,
        "allocation": {"needs": needs, "wants": wants, "savings": savings_alloc},
    })
    st.success(f"Player {player_name} added!")

# --------------------------------
# Game logic
# --------------------------------
if st.session_state.players:
    player = st.session_state.players[st.session_state.current_player]
    st.subheader(f"Current Player: {player['name']}")

    # Draw card
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
        # Map back to the option dict
        selected_option = card["options"][[format_option_text(opt) for opt in card["options"]].index(option_choice)]

        if st.button("Submit Option"):
            valid, msg = is_valid_option(player, selected_option)
            if not valid:
                st.warning(msg)
            else:
                player = apply_effects(player, selected_option)
                st.success("Option applied!")
                st.session_state.current_card = None  # Reset card
                st.experimental_rerun()  # Refresh to next player

    st.markdown(
        f"**Savings:** {player['savings']}, **Well-being:** {player['emotion']}, **Energy:** {player['time']}"
    )
