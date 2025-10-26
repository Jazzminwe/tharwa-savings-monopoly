import streamlit as st
import random
import json

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
# Load cards
# --------------------------------
with open("cards.json", "r") as f:
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
goal = st.sidebar.number_input("Savings goal", value=st.session_state.facilitator_settings["goal"])
income = st.sidebar.number_input("Monthly income", value=st.session_state.facilitator_settings["income"])
needs = st.sidebar.number_input("Needs allocation", value=st.session_state.facilitator_settings["allocation"]["needs"])
wants = st.sidebar.number_input("Wants allocation", value=st.session_state.facilitator_settings["allocation"]["wants"])
savings_alloc = st.sidebar.number_input("Savings allocation", value=st.session_state.facilitator_settings["allocation"]["savings"])

total_alloc = needs + wants + savings_alloc
if total_alloc != income:
    st.sidebar.error(f"Total allocation (needs+wants+savings={total_alloc}) must equal income ({income})")
    st.stop()

st.session_state.facilitator_settings = {
    "goal": goal,
    "income": income,
    "allocation": {"needs": needs, "wants": wants, "savings": savings_alloc}
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
    idx = st.session_state.current_player
    player = st.session_state.players[idx]
    st.subheader(f"Current Player: {player['name']}")

    # Draw card
    if st.button("Draw Card"):
        st.session_state.current_card = random.choice(cards)

    card = st.session_state.current_card
    if card:
        st.markdown(f"**Card:** {card['title']}")

        # Store choice in session state to avoid losing it on rerun
        choice_key = f"choice_{player['name']}"
        if choice_key not in st.session_state:
            st.session_state[choice_key] = None

        option_texts = [format_option_text(opt) for opt in card["options"]]
        st.session_state[choice_key] = st.radio(
            "Choose an option",
            option_texts,
            index=0,
            key=choice_key
        )

        selected_option = card["options"][option_texts.index(st.session_state[choice_key])]

        if st.button("Submit Option"):
            valid, msg = is_valid_option(player, selected_option)
            if not valid:
                st.warning(msg)
            else:
                # Update player in session state
                st.session_state.players[idx] = apply_effects(player, selected_option)
                st.success("Option applied!")
                st.session_state.current_card = None
                st.session_state.current_player = (st.session_state.current_player + 1) % len(st.session_state.players)
                st.experimental_rerun()  # Move to next player

    st.markdown(f"**Savings:** {player['savings']}, **Well-being:** {player['emotion']}, **Energy:** {player['time']}")
