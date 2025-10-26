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

if "current_page" not in st.session_state:
    st.session_state.current_page = "setup"

# Safe rerun
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
    return f"{opt['text']} → SAR {opt['money']:,}, Wellbeing: {opt['wellbeing']}, Time: {opt['time']}"

def format_currency(value):
    return f"SAR {value:,}"

def color_bar(value):
    if value < 3:
        return "🔴"
    elif value < 7:
        return "🟡"
    else:
        return "🟢"

# --------------------------------
# Facilitator setup
# --------------------------------
st.sidebar.header("Facilitator Setup")
income = st.sidebar.number_input(
    "Monthly income for all players (SAR)", 
    value=st.session_state.facilitator_settings["income"],
    step=50,
    format="%d"
)
goal = st.sidebar.number_input(
    "Savings goal for all players (SAR)", 
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
# Page navigation
# --------------------------------
if st.session_state.current_page == "setup":
    st.header("Players Setup")
    with st.expander("Add New Player"):
        team_name = st.text_input("Team Name")
        player_name = st.text_input("Player Name")
        savings_goal_desc = st.text_input("Savings Goal Description", placeholder="E.g., buy a car, emergency fund...")
        needs = st.number_input("Needs allocation", value=int(income*0.5), step=50, format="%d")
        wants = st.number_input("Wants allocation", value=int(income*0.25), step=50, format="%d")
        savings_alloc = st.number_input("Savings allocation", value=int(income*0.25), step=50, format="%d")

        total_alloc = needs + wants + savings_alloc
        if total_alloc != income:
            st.warning(f"Allocation must sum to monthly income ({income:,}). Current total: {total_alloc:,}")

        if st.button("Create Player") and player_name and team_name and total_alloc == income:
            st.session_state.players.append({
                "team": team_name,
                "name": player_name,
                "savings": savings_alloc,
                "emotion": 5,
                "time": 5,
                "income": income,
                "allocation": {"needs": needs, "wants": wants, "savings": savings_alloc},
                "savings_goal_desc": savings_goal_desc,
                "round": 0
            })
            st.success(f"Player {player_name} created! Redirecting to game...")
            st.session_state.current_page = "game"
            st.session_state.rerun_flag = True

# --------------------------------
# Game logic
# --------------------------------
if st.session_state.current_page == "game" and st.session_state.players:
    player = st.session_state.players[st.session_state.current_player]
    st.subheader(f"Current Player: {player['name']} ({player['team']})")

    # Two-column layout
    left_col, right_col = st.columns([2,1])

    # -------- LEFT COLUMN --------
    with left_col:
        if st.button("Draw Card"):
            st.session_state.current_card = random.choice(cards)
            st.session_state.rerun_flag = True

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
                    # Apply effects
                    st.session_state.players[st.session_state.current_player] = apply_effects(player, selected_option)
                    st.session_state.players[st.session_state.current_player]["round"] += 1
                    st.session_state.current_card = None
                    # Move to next player
                    st.session_state.current_player = (st.session_state.current_player + 1) % len(st.session_state.players)
                    st.session_state.rerun_flag = True

    # -------- RIGHT COLUMN (Player Stats) --------
    with right_col:
        st.markdown("### Player Status")
        st.markdown(f"**Savings Goal:** {player['savings_goal_desc']} ({format_currency(goal)})")
        st.markdown(f"**Savings:** {format_currency(player['savings'])}")
        st.progress(min(player['savings']/goal,1.0))
        st.markdown(f"**Monthly Income:** {format_currency(player['income'])}")

        # Allow player to adjust monthly allocation for next round
        st.markdown("**Monthly Budget Allocation (adjust for next round)**")
        col1, col2, col3 = st.columns(3)
        needs_new = col1.number_input("Needs", value=player["allocation"]["needs"], step=50, key=f"needs_{player['name']}")
        wants_new = col2.number_input("Wants", value=player["allocation"]["wants"], step=50, key=f"wants_{player['name']}")
        savings_new = col3.number_input("Savings", value=player["allocation"]["savings"], step=50, key=f"savings_{player['name']}")
        total_new = needs_new + wants_new + savings_new
        if total_new != player["income"]:
            st.warning(f"Allocation must sum to monthly income ({player['income']:,}). Current total: {total_new:,}")
        else:
            player["allocation"] = {"needs": needs_new, "wants": wants_new, "savings": savings_new}

        # Wellbeing and Time
        st.markdown(f"**Well-being:** {player['emotion']}/10 {color_bar(player['emotion'])}")
        st.markdown(f"**Energy:** {player['time']}/10 {color_bar(player['time'])}")
        st.markdown(f"**Round:** {player['round']} / {rounds}")

