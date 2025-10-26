import streamlit as st
import random
import json

# -------------------------------
# Page config
# -------------------------------
st.set_page_config(
    page_title="Tharwa Savings Game",
    layout="wide",
)

# -------------------------------
# Initialize session state
# -------------------------------
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
        "rounds": 6,
    }

if "pending_rerun" not in st.session_state:
    st.session_state.pending_rerun = False

if "decision_log" not in st.session_state:
    st.session_state.decision_log = []

# -------------------------------
# Load cards
# -------------------------------
with open("data/life_cards.json", "r") as f:
    cards = json.load(f)

# -------------------------------
# Helper functions
# -------------------------------
def apply_effects(player, option):
    player["savings"] += option.get("money", 0)
    player["emotion"] += option.get("wellbeing", 0)
    player["time"] += option.get("time", 0)
    player["rounds_played"] += 1
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

def format_currency(amount):
    return f"SAR {amount:,.0f}"

# -------------------------------
# Facilitator Setup
# -------------------------------
st.sidebar.header("Facilitator Setup")
goal = st.sidebar.number_input(
    "Savings goal (SAR)", 
    value=st.session_state.facilitator_settings["goal"], 
    step=50
)
income = st.sidebar.number_input(
    "Monthly income (SAR)", 
    value=st.session_state.facilitator_settings["income"], 
    step=50
)
rounds = st.sidebar.number_input(
    "Number of rounds", 
    value=st.session_state.facilitator_settings["rounds"], 
    step=1, 
    min_value=1
)

st.session_state.facilitator_settings = {
    "goal": goal,
    "income": income,
    "rounds": rounds,
}

# -------------------------------
# Player Setup
# -------------------------------
st.header("Create Player")
team_name = st.text_input("Team Name")
player_name = st.text_input("Player Name")
savings_goal_desc = st.text_input("Savings Goal Description")
initial_needs = st.number_input("Needs allocation (SAR)", step=50, value=goal//3)
initial_wants = st.number_input("Wants allocation (SAR)", step=50, value=goal//6)
initial_savings = st.number_input("Savings allocation (SAR)", step=50, value=goal//6)

if st.button("Create Player") and player_name:
    st.session_state.players.append({
        "team": team_name,
        "name": player_name,
        "savings_goal_desc": savings_goal_desc,
        "savings_goal_amount": goal,
        "savings": 0,
        "emotion": 5,
        "time": 5,
        "income": income,
        "allocation": {"needs": initial_needs, "wants": initial_wants, "savings": initial_savings},
        "rounds_played": 0,
    })
    # redirect to player page by setting a flag
    st.session_state.pending_rerun = True

# -------------------------------
# Game Logic
# -------------------------------
if st.session_state.players:
    player = st.session_state.players[st.session_state.current_player]

    # Layout: left column for game, right column for stats
    game_col, stats_col = st.columns([2, 1], gap="large")

    with stats_col:
        # Shadow card style for player stats
        st.markdown(
            f"""
            <div style='
                background-color: #fefefe;
                padding: 20px;
                border-radius: 15px;
                box-shadow: 0 10px 25px rgba(0,0,0,0.2);
                min-height: 500px;
            '>
            <h3>Player Stats 🏆</h3>
            <b>Name:</b> {player['name']} <br>
            <b>Team:</b> {player['team']} <br>
            <b>Savings Goal:</b> {player['savings_goal_desc']} ({format_currency(player['savings_goal_amount'])})<br>
            <b>Savings Progress:</b> {format_currency(player['savings'])} 
            ({int(player['savings']/player['savings_goal_amount']*100)}%)
            <progress value="{player['savings']}" max="{player['savings_goal_amount']}" style="width:100%"></progress><br>
            <b>Monthly Income:</b> {format_currency(player['income'])}<br>
            <b>Budget Allocation (SAR):</b><br>
            """, unsafe_allow_html=True
        )

        # Budget allocation inputs in a single row
        needs, wants, savings_alloc = st.columns(3)
        with needs:
            new_needs = st.number_input("Needs", step=50, value=player["allocation"]["needs"], key="needs_input")
        with wants:
            new_wants = st.number_input("Wants", step=50, value=player["allocation"]["wants"], key="wants_input")
        with savings_alloc:
            new_savings = st.number_input("Savings", step=50, value=player["allocation"]["savings"], key="savings_input")

        if st.button("Save", key="save_alloc"):
            total = new_needs + new_wants + new_savings
            if total != player["income"]:
                st.warning(f"Total allocation ({total}) must equal income ({player['income']})")
            else:
                player["allocation"] = {"needs": new_needs, "wants": new_wants, "savings": new_savings}
                st.success("Allocation saved!")
                st.session_state.pending_rerun = True

        st.markdown(
            f"""
            <b>Well-being:</b> {player['emotion']} 💖<br>
            <b>Energy:</b> {player['time']} ⚡<br>
            <b>Rounds Played:</b> {player['rounds_played']} / {st.session_state.facilitator_settings['rounds']}<br>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with game_col:
        st.subheader("Draw a Life Card")
        if st.button("Draw Card", key="draw_card"):
            st.session_state.current_card = random.choice(cards)
            st.session_state.pending_rerun = True

        card = st.session_state.current_card
        if card:
            st.markdown(f"**Card:** {card['title']}")
            option_choice = st.radio(
                "Choose an option",
                [format_option_text(opt) for opt in card["options"]],
                key=f"choice_{player['name']}"
            )
            selected_option = card["options"][[format_option_text(opt) for opt in card["options"]].index(option_choice)]
            if st.button("Submit Decision", key="submit_option"):
                valid, msg = is_valid_option(player, selected_option)
                if not valid:
                    st.warning(msg)
                else:
                    player = apply_effects(player, selected_option)
                    st.success("Decision applied!")
                    st.session_state.decision_log.append({
                        "player": player["name"],
                        "card": card["title"],
                        "choice": option_choice,
                    })
                    st.session_state.current_card = None
                    st.session_state.pending_rerun = True

    # -------------------------------
    # Decision Log
    # -------------------------------
    if st.session_state.decision_log:
        st.subheader("Decision Log 📝")
        for log in st.session_state.decision_log:
            st.write(f"{log['player']} chose '{log['choice']}' on '{log['card']}'")

# -------------------------------
# Safe rerun at end of script
# -------------------------------
if st.session_state.pending_rerun:
    st.session_state.pending_rerun = False
    st.experimental_rerun()
