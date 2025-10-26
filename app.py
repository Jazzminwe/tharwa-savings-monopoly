import streamlit as st
import random
import json
from pathlib import Path

# ------------------------------
# Safe rerun helper
# ------------------------------
if "rerun_flag" not in st.session_state:
    st.session_state.rerun_flag = False

if st.session_state.rerun_flag:
    st.session_state.rerun_flag = False
    st.experimental_rerun()

# ------------------------------
# Initialize session state
# ------------------------------
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
        "rounds": 12
    }

if "current_page" not in st.session_state:
    st.session_state.current_page = "setup"

# ------------------------------
# Load life cards
# ------------------------------
data_path = Path("data/life_cards.json")
if data_path.exists():
    with open(data_path, "r") as f:
        cards = json.load(f)
else:
    st.error("Data file life_cards.json not found in /data folder")
    st.stop()

# ------------------------------
# Helper functions
# ------------------------------
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
    return f"{opt['text']} → Money: SAR {opt['money']:,}, Wellbeing: {opt['wellbeing']}, Time: {opt['time']}"

def format_sar(value):
    return f"SAR {value:,}"

# ------------------------------
# Facilitator setup
# ------------------------------
st.sidebar.header("Facilitator Setup")
goal = st.sidebar.number_input(
    "Savings Goal (SAR)", 
    min_value=0, step=50, value=st.session_state.facilitator_settings["goal"]
)
income = st.sidebar.number_input(
    "Monthly Income (SAR)", 
    min_value=0, step=50, value=st.session_state.facilitator_settings["income"]
)
rounds = st.sidebar.number_input(
    "Number of Rounds", 
    min_value=1, step=1, value=st.session_state.facilitator_settings.get("rounds",12)
)

# Save facilitator settings
st.session_state.facilitator_settings = {
    "goal": goal,
    "income": income,
    "rounds": rounds
}

# ------------------------------
# Page routing
# ------------------------------
if st.session_state.current_page == "setup":
    st.title("Player Setup")
    team_name = st.text_input("Team Name")
    player_name = st.text_input("Player Name")
    savings_desc = st.text_input("Savings Goal Description")
    
    needs = st.number_input("Needs Allocation (SAR)", min_value=0, step=50, value=st.session_state.facilitator_settings["income"]//2)
    wants = st.number_input("Wants Allocation (SAR)", min_value=0, step=50, value=st.session_state.facilitator_settings["income"]//4)
    savings_alloc = st.number_input("Savings Allocation (SAR)", min_value=0, step=50, value=st.session_state.facilitator_settings["income"]//4)
    
    total_alloc = needs + wants + savings_alloc
    if total_alloc != st.session_state.facilitator_settings["income"]:
        st.warning(f"Total allocation must equal monthly income SAR {st.session_state.facilitator_settings['income']:,}")
    else:
        if st.button("Create Player"):
            st.session_state.players.append({
                "team": team_name,
                "name": player_name,
                "savings_desc": savings_desc,
                "savings": savings_alloc,
                "monthly_income": st.session_state.facilitator_settings["income"],
                "allocation": {"needs": needs, "wants": wants, "savings": savings_alloc},
                "emotion": 5,
                "time": 5,
                "rounds_played": 0
            })
            st.session_state.current_page = "game"
            st.session_state.rerun_flag = True

# ------------------------------
# Game page
# ------------------------------
if st.session_state.current_page == "game":
    if not st.session_state.players:
        st.error("No players available. Go back to setup.")
        st.stop()
    
    player = st.session_state.players[st.session_state.current_player]
    st.header(f"Player: {player['name']} (Team: {player['team']})")
    
    left_col, right_col = st.columns([2,1])
    
    # ------------------------------
    # Left column: Game actions
    # ------------------------------
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
                    player = apply_effects(player, selected_option)
                    player["rounds_played"] += 1
                    st.success("Option applied!")
                    st.session_state.current_card = None
                    # Advance player to next round (loop back if multiple players)
                    st.session_state.current_player = (st.session_state.current_player + 1) % len(st.session_state.players)
                    st.session_state.rerun_flag = True
    
    # ------------------------------
    # Right column: Player stats panel
    # ------------------------------
    with right_col:
        st.subheader("Player Stats")
        
        # Savings with goal
        st.markdown(f"**Savings Goal:** {player['savings_desc']} ({format_sar(st.session_state.facilitator_settings['goal'])})")
        st.progress(min(player['savings']/st.session_state.facilitator_settings['goal'], 1.0))
        st.markdown(f"**Current Savings:** {format_sar(player['savings'])}")
        
        # Monthly income
        st.markdown(f"**Monthly Income:** {format_sar(player['monthly_income'])}")
        
        # Budget allocation editable
        st.markdown("**Monthly Budget Allocation (SAR):**")
        needs_new = st.number_input("Needs", min_value=0, step=50, value=player['allocation']['needs'], key=f"needs_{player['name']}")
        wants_new = st.number_input("Wants", min_value=0, step=50, value=player['allocation']['wants'], key=f"wants_{player['name']}")
        savings_new = st.number_input("Savings", min_value=0, step=50, value=player['allocation']['savings'], key=f"savings_{player['name']}")
        total_alloc = needs_new + wants_new + savings_new
        if total_alloc != player['monthly_income']:
            st.warning(f"Total allocation must equal monthly income SAR {player['monthly_income']:,}")
        else:
            if st.button("Save Allocation"):
                player['allocation'] = {"needs": needs_new, "wants": wants_new, "savings": savings_new}
                st.success("Allocation saved for next round!")
        
        # Wellbeing & Energy
        st.markdown(f"**Well-being:** {player['emotion']} / 10 ⭐")
        st.markdown(f"**Energy:** {player['time']} / 10 ⚡")
        
        # Rounds
        st.markdown(f"**Rounds Played:** {player['rounds_played']} / {st.session_state.facilitator_settings['rounds']} ⏳")
