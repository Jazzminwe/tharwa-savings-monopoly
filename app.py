# app.py
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

# facilitator_settings now include goal (global), income, rounds, fixed_costs
if "facilitator_settings" not in st.session_state:
    st.session_state.facilitator_settings = {
        "goal": 5000,        # global savings goal per player
        "income": 2000,      # monthly income
        "rounds": 10,
        "fixed_costs": 1000, # monthly fixed costs (needs)
    }

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
    # show sign for positive/negative money for clarity
    return f"{opt['text']} → Money: {opt['money']}, Wellbeing: {opt['wellbeing']}, Time: {opt['time']}"

def init_round_buckets(player):
    """
    At the start of each round, set up per-round buckets based on allocation.
    These are temporary balances which will be consumed by life card decisions.
    """
    player["wants_balance"] = player["allocation"]["wants"]
    player["savings_balance"] = player["allocation"]["savings"]
    return player

def validate_allocation_total(income, fixed_costs, wants, savings):
    """
    Ensure wants + savings equals available (income - fixed costs).
    """
    available = income - fixed_costs
    if wants + savings != available:
        return False, f"Wants + Savings must equal available income ({format_currency(available)})."
    return True, ""

def is_valid_option_during_round(player, option):
    """
    Check whether the option is financially possible given current per-round buckets.
    Option money: negative = expense, positive = income.
    We assume expenses are paid immediately from wants_balance then savings_balance.
    """
    money = option.get("money", 0)
    if money < 0:
        cost = -money
        funds_available = player.get("wants_balance", 0) + player.get("savings_balance", 0)
        if cost > funds_available:
            return False, "Not enough allocated funds (wants + savings) to take this option."
    # also check time and wellbeing bounds after effect
    new_time = player.get("time", 0) + option.get("time", 0)
    if new_time < 0:
        return False, "Not enough energy/time for this option!"
    new_emotion = player.get("emotion", 0) + option.get("wellbeing", 0)
    if not (0 <= new_emotion <= 10):
        return False, "Well-being out of range!"
    return True, ""

def apply_option_and_settle(player, option):
    """
    Apply wellbeing/time. Handle money:
    - If option gives money (>=0) we add it to savings_balance (treated as income).
    - If option costs money (<0), consume wants_balance first, then savings_balance.
    After settling, transfer any remaining wants_balance + savings_balance into player's total savings.
    Reset per-round balances.
    """
    money = option.get("money", 0)
    # wellbeing/time effects
    player["emotion"] += option.get("wellbeing", 0)
    player["time"] += option.get("time", 0)
    # record decision log
    player.setdefault("decision_log", []).append(
        {"card": option.get("card_title", ""), "choice": option.get("text", "")}
    )

    if money >= 0:
        # treat as added income into savings_balance
        player["savings_balance"] = player.get("savings_balance", 0) + money
    else:
        cost = -money
        # consume wants_balance first
        wants = player.get("wants_balance", 0)
        take_from_wants = min(wants, cost)
        player["wants_balance"] = wants - take_from_wants
        remaining_cost = cost - take_from_wants
        if remaining_cost > 0:
            # consume savings_balance
            savings_bal = player.get("savings_balance", 0)
            take_from_savings = min(savings_bal, remaining_cost)
            player["savings_balance"] = savings_bal - take_from_savings
            remaining_cost -= take_from_savings
        # if remaining_cost > 0 here, it should not happen due to prior validation
    # After decision, everything left in wants_balance and savings_balance becomes actual saved money:
    leftover = player.get("wants_balance", 0) + player.get("savings_balance", 0)
    player["savings"] += leftover
    # reset per-round balances
    player["wants_balance"] = 0
    player["savings_balance"] = 0
    return player

# -------------------------------
# Facilitator setup (only before game)
# -------------------------------
if not st.session_state.players:
    st.sidebar.header("Facilitator Setup")
    goal = st.sidebar.number_input(
        "Savings goal per player (global)",
        value=st.session_state.facilitator_settings["goal"],
        step=50,
    )
    income = st.sidebar.number_input(
        "Monthly income (SAR)",
        value=st.session_state.facilitator_settings["income"],
        step=50,
    )
    fixed_costs = st.sidebar.number_input(
        "Fixed monthly costs / needs (SAR)",
        value=st.session_state.facilitator_settings.get("fixed_costs", 1000),
        step=50,
        min_value=0,
    )
    rounds = st.sidebar.number_input(
        "Number of rounds",
        value=st.session_state.facilitator_settings.get("rounds", 10),
        step=1,
        min_value=1,
    )

    # update global facilitator settings
    st.session_state.facilitator_settings = {
        "goal": goal,
        "income": income,
        "rounds": rounds,
        "fixed_costs": fixed_costs,
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

    # Important: savings goal amount is global, so we display it but do not ask per player
    st.markdown(f"### 💵 Monthly Income: {format_currency(st.session_state.facilitator_settings['income'])}")
    st.markdown(f"- **Fixed monthly costs / needs:** {format_currency(st.session_state.facilitator_settings['fixed_costs'])} (set by facilitator)")
    st.markdown(f"- **Available for allocation (income - fixed costs):** {format_currency(st.session_state.facilitator_settings['income'] - st.session_state.facilitator_settings['fixed_costs'])}")

    st.subheader("💰 Initial Budget Allocation")
    # Player only defines wants and savings; needs are fixed (facilitator)
    available = st.session_state.facilitator_settings["income"] - st.session_state.facilitator_settings["fixed_costs"]
    wants = st.number_input("Wants (SAR)", min_value=0, step=50, value=available//2, key="init_wants")
    savings = st.number_input("Savings (SAR)", min_value=0, step=50, value=available - (available//2), key="init_savings")

    if st.button("Create Player") and player_name and team_name:
        ok, msg = validate_allocation_total(st.session_state.facilitator_settings["income"],
                                            st.session_state.facilitator_settings["fixed_costs"],
                                            wants, savings)
        if not ok:
            st.warning(msg)
        else:
            st.session_state.players.append(
                {
                    "team": team_name,
                    "name": player_name,
                    "savings_goal_desc": savings_goal_desc,   # saved per-player, displayed as 'description'
                    # savings_goal_amount is global in facilitator_settings
                    "savings": 0,
                    "emotion": 5,
                    "time": 5,
                    "income": st.session_state.facilitator_settings["income"],
                    "allocation": {"needs": st.session_state.facilitator_settings["fixed_costs"], "wants": wants, "savings": savings},
                    "rounds_played": 0,
                    "decision_log": [],
                    # per-round balances start at zero until round begins
                    "wants_balance": 0,
                    "savings_balance": 0,
                }
            )
            st.session_state.player_created = True
            st.rerun()

# -------------------------------
# Game Interface
# -------------------------------
if st.session_state.player_created:
    player = st.session_state.players[st.session_state.current_player]

    # Two-column layout
    game_col, stats_col = st.columns([1.6, 1], gap="large")

    with game_col:
        # Removed the word "Player" from the title per request
        st.subheader(f"{player['name']} (Team: {player['team']})")

        # Progress bar for rounds
        rounds_played = player['rounds_played']
        total_rounds = st.session_state.facilitator_settings['rounds']
        progress = rounds_played / total_rounds if total_rounds else 0
        st.progress(progress)
        st.markdown(f"**Rounds Played:** {rounds_played}/{total_rounds}")

        available = player["income"] - st.session_state.facilitator_settings["fixed_costs"]

        # If it's the start of a new round (no wants_balance set), initialize per-round buckets:
        if player.get("wants_balance", 0) == 0 and player.get("savings_balance", 0) == 0 and rounds_played < total_rounds:
            # initialize per-round buckets for the player from allocation
            player = init_round_buckets(player)
            st.session_state.players[st.session_state.current_player] = player

        st.markdown("### 🎴 Draw Life Card")
        if st.button("Draw Life Card"):
            # draw a card every round (random)
            st.session_state.current_card = random.choice(cards)

        card = st.session_state.current_card
        if card:
            st.markdown(f"### {card['title']}")
            option_texts = [format_option_text(opt) for opt in card["options"]]
            option_choice = st.radio(
                "Choose an option",
                option_texts,
                key=f"choice_{player['name']}",
            )
            selected_index = option_texts.index(option_choice)
            selected_option = card["options"][selected_index]
            selected_option["card_title"] = card["title"]

            st.markdown(f"**Per-round buckets — Wants:** {format_currency(player.get('wants_balance',0))} • **Savings bucket:** {format_currency(player.get('savings_balance',0))}")

            if st.button("✅ Submit Decision"):
                valid, msg = is_valid_option_during_round(player, selected_option)
                if not valid:
                    st.warning(msg)
                else:
                    player = apply_option_and_settle(player, selected_option)
                    player["rounds_played"] += 1
                    # clear current card for next round
                    st.session_state.current_card = None
                    st.session_state.players[st.session_state.current_player] = player
                    st.success("Decision applied and round settled.")
                    st.rerun()

        st.markdown("<br><br>", unsafe_allow_html=True)

        # Decision log at bottom
        if player["decision_log"]:
            st.subheader("Decision Log 📝")
            for log in player["decision_log"]:
                st.markdown(f"- **{log['card']}** → {log['choice']}")

        # Next / Prev player controls (if multiple players)
        col_prev, col_next = st.columns([1,1])
        with col_prev:
            if st.button("← Prev Player"):
                st.session_state.current_player = max(0, st.session_state.current_player - 1)
                st.session_state.current_card = None
                st.rerun()
        with col_next:
            if st.button("Next Player →"):
                st.session_state.current_player = min(len(st.session_state.players)-1, st.session_state.current_player + 1)
                st.session_state.current_card = None
                st.rerun()

    # -------------------------------
    # Player stats panel (shadow card)
    # -------------------------------
    with stats_col:
        # Show the savings goal amount (global) and the player-specific description (now called 'description')
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
            <b>Savings Goal:</b> {format_currency(st.session_state.facilitator_settings['goal'])}<br>
            <b>description:</b> {player.get('savings_goal_desc','')}<br><br>
            <b>Current Savings:</b> {format_currency(player['savings'])} 
            ({int((player['savings'] / max(1, st.session_state.facilitator_settings['goal']))*100)}%)<br>
            <progress value="{player['savings']}" max="{st.session_state.facilitator_settings['goal']}" style="width:100%"></progress><br>
            <b>Monthly Income:</b> {format_currency(player['income'])}<br>
            <b>Fixed monthly costs / needs:</b> {format_currency(player['allocation']['needs'])}<br>
            <b>Per-round Wants balance:</b> {format_currency(player.get('wants_balance',0))}<br>
            <b>Per-round Savings bucket (not yet moved to total savings until round ends):</b> {format_currency(player.get('savings_balance',0))}<br>
            <b>Well-being:</b> {player['emotion']} ❤️<br>
            <b>Energy:</b> {player['time']} ⚡<br>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # -------------------------------
        # #adjust budget (player may change wants/savings but must equal available)
        # -------------------------------
        st.markdown("## #adjust budget")
        col_a, col_b, col_c = st.columns([1,1,0.5])
        with col_a:
            new_wants = st.number_input("Wants", min_value=0, step=50, value=player["allocation"]["wants"], key="wants_adj")
        with col_b:
            new_savings = st.number_input("Savings", min_value=0, step=50, value=player["allocation"]["savings"], key="save_adj")
        with col_c:
            if st.button("💾 Save"):
                ok, msg = validate_allocation_total(player["income"],
                                                   player["allocation"]["needs"],
                                                   new_wants, new_savings)
                if not ok:
                    st.warning(msg)
                else:
                    player["allocation"]["wants"] = new_wants
                    player["allocation"]["savings"] = new_savings
                    # if the player is between rounds, reset per-round balances so next round uses the new allocation:
                    if player["wants_balance"] == 0 and player["savings_balance"] == 0:
                        player = init_round_buckets(player)
                    st.session_state.players[st.session_state.current_player] = player
                    st.success("Budget allocation updated!")

