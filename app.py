import streamlit as st
import random
import json

# -------------------------------
# Defaults
# -------------------------------
DEFAULT_FACILITATOR_SETTINGS = {
    "goal": 5000,
    "income": 2000,
    "rounds": 10,
    "fixed_costs": 1000,
}

# -------------------------------
# Ensure facilitator settings exist and are normalized
# -------------------------------
if "facilitator_settings" not in st.session_state:
    st.session_state.facilitator_settings = DEFAULT_FACILITATOR_SETTINGS.copy()
else:
    for k, v in DEFAULT_FACILITATOR_SETTINGS.items():
        if k not in st.session_state.facilitator_settings:
            st.session_state.facilitator_settings[k] = v

# -------------------------------
# Initialize session state for players, indexes and card
# -------------------------------
if "players" not in st.session_state:
    st.session_state.players = []

if "current_player" not in st.session_state:
    st.session_state.current_player = 0

if "current_card" not in st.session_state:
    st.session_state.current_card = None

# -------------------------------
# Load life cards
# -------------------------------
with open("data/life_cards.json", "r") as f:
    cards = json.load(f)

# -------------------------------
# Helper functions
# -------------------------------
def format_currency(amount):
    return f"SAR {amount:,.0f}"

def format_option_text(opt):
    return f"{opt.get('text','(no text)')} → Money: {opt.get('money',0)}, Wellbeing: {opt.get('wellbeing',0)}, Time: {opt.get('time',0)}"

def init_round_buckets(player):
    alloc = player.get("allocation", {})
    player["wants_balance"] = alloc.get("wants", 0)
    player["savings_balance"] = alloc.get("savings", 0)
    return player

def validate_allocation_total(income, fixed_costs, wants, savings):
    available = income - fixed_costs
    if available < 0:
        return False, f"Fixed costs exceed income. Available = {format_currency(available)}."
    if wants + savings != available:
        return False, f"Wants + Savings must equal available income ({format_currency(available)})."
    return True, ""

def is_valid_option_during_round(player, option):
    money = option.get("money",0)
    if money < 0:
        cost = -money
        funds_available = player.get("wants_balance",0) + player.get("savings_balance",0)
        if cost > funds_available:
            return False, "Not enough allocated funds (wants + savings) to take this option."
    new_time = player.get("time",0) + option.get("time",0)
    if new_time < 0:
        return False, "Not enough energy/time for this option!"
    new_emotion = player.get("emotion",0) + option.get("wellbeing",0)
    if not (0 <= new_emotion <= 10):
        return False, "Well-being out of range!"
    return True, ""

def apply_option_and_settle(player, option):
    money = option.get("money",0)
    player["emotion"] = max(0,min(10,player.get("emotion",5)+option.get("wellbeing",0)))
    player["time"] = player.get("time",5)+option.get("time",0)
    player.setdefault("decision_log",[]).append(
        {"card": option.get("card_title",""), "choice": option.get("text","")}
    )

    wants_bal = player.get("wants_balance",0)
    savings_bal = player.get("savings_balance",0)

    if money >= 0:
        savings_bal += money
    else:
        cost = -money
        take_from_wants = min(wants_bal, cost)
        wants_bal -= take_from_wants
        remaining = cost - take_from_wants
        if remaining > 0:
            take_from_savings = min(savings_bal, remaining)
            savings_bal -= take_from_savings
            remaining -= take_from_savings
        if remaining > 0:
            savings_bal -= remaining

    leftover = max(0,wants_bal) + max(0,savings_bal)
    player["savings"] = player.get("savings",0) + leftover

    player["wants_balance"] = 0
    player["savings_balance"] = 0
    return player

# -------------------------------
# Facilitator setup
# -------------------------------
if not st.session_state.players:
    st.sidebar.header("Facilitator Setup")
    fs = st.session_state.facilitator_settings
    goal = st.sidebar.number_input("Savings goal per player (global)", value=fs.get("goal", DEFAULT_FACILITATOR_SETTINGS["goal"]), step=50)
    income = st.sidebar.number_input("Monthly income (SAR)", value=fs.get("income", DEFAULT_FACILITATOR_SETTINGS["income"]), step=50)
    fixed_costs = st.sidebar.number_input("Fixed monthly costs / needs (SAR)", value=fs.get("fixed_costs", DEFAULT_FACILITATOR_SETTINGS["fixed_costs"]), step=50, min_value=0)
    rounds = st.sidebar.number_input("Number of rounds", value=fs.get("rounds", DEFAULT_FACILITATOR_SETTINGS["rounds"]), step=1, min_value=1)

    st.session_state.facilitator_settings = {
        "goal": goal,
        "income": income,
        "rounds": rounds,
        "fixed_costs": fixed_costs,
    }

# -------------------------------
# Player setup
# -------------------------------
if "player_created" not in st.session_state:
    st.session_state.player_created = False

if not st.session_state.player_created:
    team_name = st.text_input("Team Name")
    player_name = st.text_input("Player Name")
    savings_goal_desc = st.text_input("Savings Goal Description")

    fs = st.session_state.get("facilitator_settings", DEFAULT_FACILITATOR_SETTINGS)
    income_val = fs.get("income", DEFAULT_FACILITATOR_SETTINGS["income"])
    fixed_val = fs.get("fixed_costs", DEFAULT_FACILITATOR_SETTINGS["fixed_costs"])
    available = income_val - fixed_val

    st.markdown(f"### 💵 Monthly Income: {format_currency(income_val)}")
    st.markdown(f"- **Fixed monthly costs / needs:** {format_currency(fixed_val)} (set by facilitator)")
    st.markdown(f"- **Available for allocation (income - fixed costs):** {format_currency(available)}")

    st.subheader("💰 Initial Budget Allocation")
    if available < 0:
        st.error("Warning: fixed costs exceed income. Adjust facilitator settings.")
        wants = 0
        savings = 0
    else:
        wants = st.number_input("Wants (SAR)", min_value=0, step=50, value=max(0, available // 2), key="init_wants")
        savings = st.number_input("Savings (SAR)", min_value=0, step=50, value=max(0, available - (available // 2)), key="init_savings")

    if st.button("Create Player") and player_name and team_name:
        ok, msg = validate_allocation_total(income_val, fixed_val, wants, savings)
        if not ok:
            st.warning(msg)
        else:
            allocation = {"needs": fixed_val, "wants": wants, "savings": savings}
            new_player = {
                "team": team_name,
                "name": player_name,
                "savings_goal_desc": savings_goal_desc,
                "savings": 0,
                "emotion": 5,
                "time": 5,
                "income": income_val,
                "allocation": allocation,
                "rounds_played": 0,
                "decision_log": [],
                "wants_balance": 0,
                "savings_balance": 0,
            }
            st.session_state.players.append(new_player)
            st.session_state.player_created = True
            st.rerun()

# -------------------------------
# Game Interface
# -------------------------------
if st.session_state.player_created:
    player = st.session_state.players[st.session_state.current_player]
    game_col, stats_col = st.columns([1.6, 1], gap="large")

    with game_col:
        st.subheader(f"{player.get('name','Unnamed')} (Team: {player.get('team','-')})")

        rounds_played = int(player.get("rounds_played", 0))
        total_rounds = st.session_state.facilitator_settings.get("rounds", DEFAULT_FACILITATOR_SETTINGS["rounds"])
        progress = rounds_played / total_rounds if total_rounds else 0
        st.progress(progress)
        st.markdown(f"**Rounds Played:** {rounds_played}/{total_rounds}")

        income_val = player.get("income", st.session_state.facilitator_settings.get("income", DEFAULT_FACILITATOR_SETTINGS["income"]))
        fixed_val = st.session_state.facilitator_settings.get("fixed_costs", DEFAULT_FACILITATOR_SETTINGS["fixed_costs"])
        available = income_val - fixed_val

        if player.get("wants_balance", 0) == 0 and player.get("savings_balance", 0) == 0 and rounds_played < total_rounds:
            player = init_round_buckets(player)
            st.session_state.players[st.session_state.current_player] = player

        st.markdown("### 🎴 Draw Life Card")
        if st.button("Draw Life Card"):
            st.session_state.current_card = random.choice(cards)

        card = st.session_state.current_card
        if card:
            st.markdown(f"### {card.get('title','(untitled)')}")
            option_texts = [format_option_text(opt) for opt in card.get("options", [])]
            if option_texts:
                option_choice = st.radio("Choose an option", option_texts, key=f"choice_{player.get('name','')}")
                selected_index = option_texts.index(option_choice)
                selected_option = card["options"][selected_index]
                selected_option["card_title"] = card.get("title", "")

                st.markdown(f"**Per-round buckets — Wants:** {format_currency(player.get('wants_balance',0))} • **Savings bucket:** {format_currency(player.get('savings_balance',0))}")

                if st.button("✅ Submit Decision"):
                    valid, msg = is_valid_option_during_round(player, selected_option)
                    if not valid:
                        st.warning(msg)
                    else:
                        player = apply_option_and_settle(player, selected_option)
                        player["rounds_played"] = player.get("rounds_played",0)+1
                        st.session_state.current_card = None
                        st.session_state.players[st.session_state.current_player] = player
                        st.success("Decision applied and round settled.")
                        st.rerun()

        if player.get("decision_log"):
            st.subheader("Decision Log 📝")
            for log in player.get("decision_log", []):
                st.markdown(f"- **{log.get('card','')}** → {log.get('choice','')}")

    with stats_col:
        fs_goal = st.session_state.facilitator_settings.get("goal", DEFAULT_FACILITATOR_SETTINGS["goal"])
        allocation = player.get("allocation", {"needs": fixed_val, "wants": 0, "savings": 0})
        wants_bal = player.get("wants_balance", 0)
        savings_bal = player.get("savings_balance", 0)
        st.markdown(
            f"""
            <div style='
                background-color: #fefefe;
                padding: 20px;
                border-radius: 20px;
                box-shadow: 0 10px 25px rgba(0,0,0,0.25);
                width: 100%;
                overflow-y: auto;
                margin-bottom: 25px;
            '>
            <h3>🏆 Player Stats</h3>
            <b>Savings Goal:</b> {format_currency(fs_goal)}<br>
            <b>Description:</b> {player.get('savings_goal_desc','')}<br><br>
            <b>Current Savings:</b> {format_currency(player.get('savings',0))} ({int((player.get('savings',0)/max(1,fs_goal))*100)}%)<br>
            <progress value="{player.get('savings',0)}" max="{fs_goal}" style="width:100%"></progress><br>
            <b>Monthly Income:</b> {format_currency(player.get('income', income_val))}<br>
            <b>Fixed monthly costs / needs:</b> {format_currency(allocation.get('needs', fixed_val))}<br>
            <b>Per-round Wants balance:</b> {format_currency(wants_bal)}<br>
            <b>Per-round Savings bucket:</b> {format_currency(savings_bal)}<br>
            <b>Well-being:</b> {player.get('emotion',5)} ❤️<br>
            <b>Energy:</b> {player.get('time',5)} ⚡<br>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Adjust budget
        st.markdown("## Adjust budget")
        col_a, col_b, col_c = st.columns([1,1,0.5])
        with col_a:
            new_wants = st.number_input("Wants", min_value=0, step=50, value=allocation.get("wants",0), key="wants_adj")
        with col_b:
            new_savings = st.number_input("Savings", min_value=0, step=50, value=allocation.get("savings",0), key="save_adj")
        with col_c:
            if st.button("💾 Save"):
                ok, msg = validate_allocation_total(player.get("income", income_val), allocation.get("needs", fixed_val), new_wants, new_savings)
                if not ok:
                    st.warning(msg)
                else:
                    player["allocation"]["wants"] = new_wants
                    player["allocation"]["savings"] = new_savings
                    if player.get("wants_balance",0)==0 and player.get("savings_balance",0)==0:
                        player = init_round_buckets(player)
                    st.session_state.players[st.session_state.current_player] = player
                    st.success("Budget allocation updated!")
