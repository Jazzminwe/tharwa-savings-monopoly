import streamlit as st
import random
import json

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
        "rounds": 10,
    }

# -------------------------------
# Load life cards
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
    # log decision
    player.setdefault("decision_log", []).append(
        {"card": option.get("card_title", ""), "choice": option.get("text", "")}
    )
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
# Facilitator setup (only BEFORE game)
# -------------------------------
if not st.session_state.players:
    st.sidebar.header("Facilitator Setup")
    goal = st.sidebar.number_input(
        "Savings goal per player",
        value=st.session_state.facilitator_settings["goal"],
        step=50,
    )
    income = st.sidebar.number_input(
        "Monthly income (SAR)",
        value=st.session_state.facilitator_settings["income"],
        step=50,
    )
    rounds = st.sidebar.number_input(
        "Number of rounds",
        value=st.session_state.facilitator_settings.get("rounds", 10),
        step=1,
        min_value=1,
    )

    st.session_state.facilitator_settings = {
        "goal": goal,
        "income": income,
        "rounds": rounds,
    }

# -------------------------------
# Player setup
# -------------------------------
st.header("Players")

if "player_created" not in st.session_state:
    st.session_state.player_created = False

if not st.session_state.player_created:
    team_name = st.text_input("Team Name")
    player_name = st.text_input("Player Name")
    savings_goal_desc = st.text_input("Savings Goal Description")

    savings_goal_amount = st.number_input(
        "Savings Goal Amount (SAR)",
        min_value=0,
        step=50,
        value=st.session_state.facilitator_settings["goal"],
    )

    st.markdown(
        f"### 💵 Monthly Income: {format_currency(st.session_state.facilitator_settings['income'])}"
    )

    st.subheader("💰 Initial Budget Allocation")
    needs = st.number_input("Needs (SAR)", min_value=0, step=50, value=1000)
    wants = st.number_input("Wants (SAR)", min_value=0, step=50, value=500)
    saving = st.number_input("Savings (SAR)", min_value=0, step=50, value=500)

    if st.button("Create Player") and player_name and team_name:
        st.session_state.players.append(
            {
                "team": team_name,
                "name": player_name,
                "savings_goal_desc": savings_goal_desc,
                "savings_goal_amount": savings_goal_amount,
                "savings": 0,
                "emotion": 5,
                "time": 5,
                "income": st.session_state.facilitator_settings["income"],
                "allocation": {"needs": needs, "wants": wants, "savings": saving},
                "rounds_played": 0,
                "decision_log": [],
            }
        )
        st.session_state.player_created = True
        st.rerun()

# -------------------------------
# Game interface
# -------------------------------
if st.session_state.player_created:
    player = st.session_state.players[st.session_state.current_player]

    # Two-column layout: game left, stats right
    game_col, stats_col = st.columns([1.6, 1], gap="large")

    # ---------- LEFT: GAME ----------
    with game_col:
        st.subheader(f"Current Player: {player['name']} (Team: {player['team']})")

        # Rounds progress bar (no % label, just bar + X/Y)
        rounds_played = player["rounds_played"]
        total_rounds = st.session_state.facilitator_settings["rounds"]
        progress = rounds_played / total_rounds if total_rounds else 0
        st.progress(progress)
        st.markdown(f"**Rounds Played:** {rounds_played}/{total_rounds}")

        # Draw card
        if st.button("🎴 Draw Life Card"):
            st.session_state.current_card = random.choice(cards)

        card = st.session_state.current_card
        if card:
            st.markdown(f"### {card['title']}")
            option_choice = st.radio(
                "Choose an option",
                [format_option_text(opt) for opt in card["options"]],
                key=f"choice_{player['name']}",
            )
            selected_option = card["options"][
                [format_option_text(opt) for opt in card["options"]].index(option_choice)
            ]
            selected_option["card_title"] = card["title"]

            if st.button("✅ Submit Decision"):
                valid, msg = is_valid_option(player, selected_option)
                if not valid:
                    st.warning(msg)
                else:
                    player = apply_effects(player, selected_option)
                    player["rounds_played"] += 1
                    st.session_state.current_card = None
                    st.session_state.players[st.session_state.current_player] = player
                    st.rerun()

        # Decision log at bottom
        if player["decision_log"]:
            st.markdown("<br>", unsafe_allow_html=True)
            st.subheader("Decision Log 📝")
            for log in player["decision_log"]:
                st.markdown(f"- **{log['card']}** → {log['choice']}")

    # ---------- RIGHT: STATS + BUDGET ----------
    with stats_col:
        # 3D card for player stats
        savings_goal = max(1, player["savings_goal_amount"])
        pct = int(player["savings"] / savings_goal * 100)

        st.markdown(
            f"""
            <div style='
                background-color: #fefefe;
                padding: 20px;
                border-radius: 20px;
                box-shadow: 0 10px 25px rgba(0,0,0,0.25);
                width: 100%;
                margin-bottom: 25px;
            '>
              <h3>🏆 Player Stats</h3>
              <b>Savings Goal:</b> {format_currency(player['savings_goal_amount'])} ({player['savings_goal_desc']})<br>
              <b>Current Savings:</b> {format_currency(player['savings'])} ({pct}%)<br>
              <progress value="{player['savings']}" max="{savings_goal}" style="width:100%"></progress><br><br>
              <b>Monthly Income:</b> {format_currency(player['income'])}<br>
              <b>Well-being:</b> {player['emotion']} ❤️<br>
              <b>Energy:</b> {player['time']} ⚡<br>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # 3D card for budget allocation (Needs / Wants / Savings)
        st.markdown(
            """
            <div style='
                background-color: #fefefe;
                padding: 20px;
                border-radius: 20px;
                box-shadow: 0 10px 25px rgba(0,0,0,0.18);
                width: 100%;
                margin-bottom: 10px;
            '>
            <h3>💰 Adjust Budget Allocation</h3>
            </div>
            """,
            unsafe_allow_html=True,
        )

        col_a, col_b, col_c, col_d = st.columns([1, 1, 1, 0.7])
        with col_a:
            new_needs = st.number_input(
                "Needs",
                min_value=0,
                step=50,
                value=player["allocation"]["needs"],
                key="needs_adj",
            )
        with col_b:
            new_wants = st.number_input(
                "Wants",
                min_value=0,
                step=50,
                value=player["allocation"]["wants"],
                key="wants_adj",
            )
        with col_c:
            new_savings = st.number_input(
                "Savings",
                min_value=0,
                step=50,
                value=player["allocation"]["savings"],
                key="save_adj",
            )
        with col_d:
            if st.button("💾 Save"):
                player["allocation"] = {
                    "needs": new_needs,
                    "wants": new_wants,
                    "savings": new_savings,
                }
                st.session_state.players[st.session_state.current_player] = player
                st.success("Budget allocation updated!")
