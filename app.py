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
    st.session_state.facilitator_settings = {"goal": 5000, "income": 2000, "rounds": 10}

if "rerun_flag" not in st.session_state:
    st.session_state.rerun_flag = False

# Handle safe rerun
if st.session_state.rerun_flag:
    st.session_state.rerun_flag = False
    st.experimental_rerun()

# --------------------------------
# Load life cards
# --------------------------------
try:
    with open("data/life_cards.json", "r") as f:
        cards = json.load(f)
except FileNotFoundError:
    st.error("Life cards file not found! Make sure 'data/life_cards.json' exists.")
    st.stop()

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
    return f"{opt['text']} → Money: {opt['money']:,}, Wellbeing: {opt['wellbeing']}, Time: {opt['time']}"

def format_currency(value):
    return f"{value:,}"

# --------------------------------
# Facilitator setup
# --------------------------------
st.sidebar.header("Facilitator Setup")
income = st.sidebar.number_input(
    "Monthly income for all players", 
    value=st.session_state.facilitator_settings["income"],
    step=50,
    format="%d"
)
goal = st.sidebar.number_input(
    "Savings goal for all players", 
    value=st.session_state.facilitator_settings["goal"],
    step=50,
    format="%d"
)
rounds = st.sidebar.number_input(
    "Number of rounds", 
    value=st.session_state.facilitator_settings.get("rounds", 10),
    min_value=1,
    step=1
)

st.session_state.facilitator_settings = {"goal": goal, "income": income, "rounds": rounds}

# --------------------------------
# Player setup
# --------------------------------
st.header("Players Setup")
with st.expander("Add New Player"):
    team_name = st.text_input("Team Name")
    player_name = st.text_input("Player Name")
    player_income = st.number_input(
        "Monthly Income", 
        value=income, 
        step=50, 
        format="%d"
    )
    needs = st.number_input("Needs allocation", value=int(player_income*0.5), step=50, format="%d")
    wants = st.number_input("Wants allocation", value=int(player_income*0.25), step=50, format="%d")
    savings_alloc = st.number_input("Savings allocation", value=int(player_income*0.25), step=50, format="%d")
    savings_goal_desc = st.text_input("Savings Goal Description", placeholder="E.g., buy a car, emergency fund...")

    total_alloc = needs + wants + savings_alloc
    if total_alloc != player_income:
        st.warning(f"Allocation must sum to monthly income ({player_income:,}). Current total: {total_alloc:,}")

    if st.button("Add Player") and player_name and team_name and total_alloc == player_income:
        st.session_state.players.append({
            "team": team_name,
            "name": player_name,
            "savings": savings_alloc,
            "emotion": 5,
            "time": 5,
            "income": player_income,
            "allocation": {"needs": needs, "wants": wants, "savings": savings_alloc},
            "savings_goal_desc": savings_goal_desc,
            "round": 0
        })
        st.success(f"Player {player_name} added!")

# --------------------------------
# Game logic
# --------------------------------
if st.session_state.players:
    player = st.session_state.players[st.session_state.current_player]
    st.subheader(f"Current Player: {player['name']} ({player['team']})")

    # Two-column layout
    left_col, right_col = st.columns([2,1])

    with left_col:
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
            selected_option = card["options"][[format_option_text(opt) for opt in card["options"]].index(option_choice)]

            if st.button("Submit Option"):
                valid, msg = is_valid_option(player, selected_option)
                if not valid:
                    st.warning(msg)
                else:
                    st.session_state.players[st.session_state.current_player] = apply_effects(player, selected_option)
                    st.session_state.current_card = None  # Reset card
                    st.session_state.players[st.session_state.current_player]["round"] += 1
                    # Move to next player
                    st.session_state.current_player = (st.session_state.current_player + 1) % len(st.session_state.players)
                    st.session_state.rerun_flag = True

    with right_col:
        st.markdown("### Player Status")
        st.markdown(f"**Savings Goal:** {player['savings_goal_desc']}")
        st.markdown(f"**Savings:** ${format_currency(player['savings'])}")
        st.progress(min(player['savings']/goal,1.0))
        st.markdown(f"**Well-being:** {player['emotion']}/10")
        st.markdown(f"**Energy:** {player['time']}/10")
        st.markdown(f"**Monthly Income:** ${format_currency(player['income'])}")
        st.markdown(f"**Round:** {player['round']} / {rounds}")

