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

if "decision_log" not in st.session_state:
    st.session_state.decision_log = []

if "facilitator_settings" not in st.session_state:
    st.session_state.facilitator_settings = {
        "goal": 5000,
        "monthly_income": 2000,
        "rounds": 10
    }

if "pending_rerun" not in st.session_state:
    st.session_state.pending_rerun = False

# --------------------------------
# Load cards
# --------------------------------
try:
    with open("data/life_cards.json", "r") as f:
        cards = json.load(f)
except FileNotFoundError:
    st.error("Cards file not found! Please ensure 'data/life_cards.json' exists.")
    st.stop()

# --------------------------------
# Helper functions
# --------------------------------
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
    return f"{opt['text']} → 💰 {opt['money']:,} SAR, 😊 {opt['wellbeing']}, ⚡ {opt['time']}"

def currency_fmt(val):
    return f"{val:,} SAR"

# --------------------------------
# Facilitator setup
# --------------------------------
st.sidebar.header("Facilitator Setup")
goal = st.sidebar.number_input(
    "Savings goal per player", value=st.session_state.facilitator_settings["goal"], step=50
)
monthly_income = st.sidebar.number_input(
    "Monthly income", value=st.session_state.facilitator_settings["monthly_income"], step=50
)
rounds = st.sidebar.number_input(
    "Number of rounds", value=st.session_state.facilitator_settings.get("rounds", 10), step=1
)

st.session_state.facilitator_settings.update({
    "goal": goal,
    "monthly_income": monthly_income,
    "rounds": rounds
})

# --------------------------------
# Player setup
# --------------------------------
st.header("Players")
team_name = st.text_input("Team Name")
player_name = st.text_input("Player Name")
savings_goal_desc = st.text_input("Savings Goal Description")
needs_init = st.number_input("Needs allocation", min_value=0, step=50, value=monthly_income//2)
wants_init = st.number_input("Wants allocation", min_value=0, step=50, value=monthly_income//4)
savings_init = st.number_input("Monthly savings", min_value=0, step=50, value=monthly_income - needs_init - wants_init)

total_alloc = needs_init + wants_init + savings_init
if total_alloc != monthly_income:
    st.warning(f"Total allocation ({total_alloc:,} SAR) must equal monthly income ({monthly_income:,} SAR)")

if st.button("Create Player") and player_name and team_name and total_alloc == monthly_income:
    st.session_state.players.append({
        "team_name": team_name,
        "name": player_name,
        "savings_goal_desc": savings_goal_desc,
        "savings_goal": goal,
        "savings": 0,
        "monthly_income": monthly_income,
        "allocation": {"needs": needs_init, "wants": wants_init, "savings": savings_init},
        "emotion": 5,
        "time": 5,
        "rounds_played": 0
    })
    st.success(f"Player {player_name} created! You can start the game.")
    st.session_state.pending_rerun = True

# --------------------------------
# Game logic
# --------------------------------
if st.session_state.players:
    player = st.session_state.players[st.session_state.current_player]

    col1, col2 = st.columns([2, 1])
    with col1:
        st.subheader(f"Current Player: {player['name']} (Team: {player['team_name']})")

        # Draw Card
        if st.button("Draw Card"):
            st.session_state.current_card = random.choice(cards)
            st.session_state.pending_rerun = True

        card = st.session_state.current_card
        if card:
            st.markdown(f"### Card: {card['title']}")
            option_choice = st.radio(
                "Choose an option",
                [format_option_text(opt) for opt in card["options"]],
                key=f"choice_{player['name']}"
            )
            selected_option = card["options"][[format_option_text(opt) for opt in card["options"]].index(option_choice)]

            if st.button("Submit Decision"):
                valid, msg = is_valid_option(player, selected_option)
                if not valid:
                    st.warning(msg)
                else:
                    apply_effects(player, selected_option)
                    # Add to decision log
                    st.session_state.decision_log.append({
                        "player": player['name'],
                        "team": player['team_name'],
                        "decision": selected_option['text'],
                        "money": selected_option['money'],
                        "wellbeing": selected_option['wellbeing'],
                        "time": selected_option['time']
                    })
                    st.session_state.current_card = None  # clear card
                    st.session_state.pending_rerun = True

    with col2:
        st.markdown("### 📝 Player Stats & Rounds")
        st.markdown(f"**Rounds left:** {st.session_state.facilitator_settings['rounds'] - player['rounds_played']}/{st.session_state.facilitator_settings['rounds']}")

        # Visual card style with shadow
        st.markdown(
            f"""
            <div style="padding:20px; border-radius:15px; box-shadow: 2px 4px 20px rgba(0,0,0,0.3); background-color:#fdfdfd">
            <h4>💰 Savings</h4>
            <p>{currency_fmt(player['savings'])} / {currency_fmt(player['savings_goal'])} ({player['savings']/player['savings_goal']*100:.1f}%)</p>
            <progress value="{player['savings']}" max="{player['savings_goal']}" style="width:100%"></progress>
            <p>Goal Description: {player.get('savings_goal_desc','')}</p>

            <h4>🏦 Monthly Income</h4>
            <p>{currency_fmt(player['monthly_income'])}</p>

            <h4>📊 Budget Allocation (for next round)</h4>
            </div>
            """, unsafe_allow_html=True
        )

        needs_new = st.number_input("Needs", min_value=0, step=50, value=player['allocation']['needs'], key=f"needs_{player['name']}")
        wants_new = st.number_input("Wants", min_value=0, step=50, value=player['allocation']['wants'], key=f"wants_{player['name']}")
        savings_new = st.number_input("Savings", min_value=0, step=50, value=player['allocation']['savings'], key=f"savings_{player['name']}")

        if st.button("Save Allocation"):
            total = needs_new + wants_new + savings_new
            if total != player['monthly_income']:
                st.warning(f"Allocation must sum to {currency_fmt(player['monthly_income'])}")
            else:
                player['allocation'] = {"needs": needs_new, "wants": wants_new, "savings": savings_new}
                st.success("Allocation saved for next round!")
                st.session_state.pending_rerun = True

        st.markdown(f"😊 Well-being: {player['emotion']}/10")
        st.markdown(f"⚡ Energy/Time: {player['time']}/10")

# --------------------------------
# Decision log
# --------------------------------
if st.session_state.decision_log:
    st.markdown("---")
    st.subheader("Decision Log")
    for idx, d in enumerate(st.session_state.decision_log, 1):
        st.markdown(f"{idx}. {d['player']} ({d['team']}): {d['decision']} → 💰 {d['money']:,} SAR, 😊 {d['wellbeing']}, ⚡ {d['time']}")

# --------------------------------
# Safe rerun at end
# --------------------------------
if st.session_state.pending_rerun:
    st.session_state.pending_rerun = False
    st.experimental_rerun()
