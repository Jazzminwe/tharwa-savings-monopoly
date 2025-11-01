# app.py (full)
import streamlit as st
import random
import json
from pathlib import Path

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
# Initialize session variables
# -------------------------------
if "players" not in st.session_state:
    st.session_state.players = []

if "current_player" not in st.session_state:
    st.session_state.current_player = 0

if "current_card" not in st.session_state:
    st.session_state.current_card = None

if "decision_log" not in st.session_state:
    st.session_state.decision_log = []

# -------------------------------
# Load life cards (defensive)
# -------------------------------
cards_path = Path("data/life_cards.json")
if cards_path.exists():
    with open(cards_path, "r") as f:
        try:
            cards = json.load(f)
        except Exception:
            cards = []
else:
    cards = []

# -------------------------------
# Helper functions
# -------------------------------
def format_currency(amount):
    try:
        return f"SAR {amount:,.0f}"
    except Exception:
        return f"SAR {amount}"

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
    """
    Apply wellbeing/time. Money handling:
      - positive money -> add to savings_balance
      - negative money -> consume wants_balance then savings_balance
    Then leftover in wants_balance & savings_balance -> player['savings'].
    """
    money = option.get("money",0)
    # wellbeing/time
    player["emotion"] = max(0, min(10, player.get("emotion",5) + option.get("wellbeing",0)))
    player["time"] = player.get("time",5) + option.get("time",0)

    # log
    player.setdefault("decision_log", []).append(
        {"card": option.get("card_title",""), "choice": option.get("text","")}
    )

    # ensure balances exist
    wants_bal = player.get("wants_balance", 0)
    savings_bal = player.get("savings_balance", 0)

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
            # Defensive fallback (should not happen if validated earlier)
            savings_bal -= remaining

    # leftover moves to player's savings
    leftover = max(0, wants_bal) + max(0, savings_bal)
    player["savings"] = player.get("savings", 0) + leftover

    # reset per-round balances
    player["wants_balance"] = 0
    player["savings_balance"] = 0

    return player

# -------------------------------
# Facilitator setup (shown only when no players yet)
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
# Player creation area (left/top)
# -------------------------------
st.title("Savings Monopoly — Setup & Game")

st.markdown("### Add player")
# We'll show inline errors below fields when the form is submitted and validation fails.
with st.form("create_player_form"):
    col_a, col_b = st.columns([1,1])
    with col_a:
        team_name = st.text_input("Team Name", key="form_team")
    with col_b:
        player_name = st.text_input("Player Name", key="form_player")

    savings_goal_desc = st.text_input("Savings Goal Description", key="form_desc")

    # read facilitator global values (defensive)
    fs = st.session_state.get("facilitator_settings", DEFAULT_FACILITATOR_SETTINGS)
    income_val = fs.get("income", DEFAULT_FACILITATOR_SETTINGS["income"])
    fixed_val = fs.get("fixed_costs", DEFAULT_FACILITATOR_SETTINGS["fixed_costs"])
    available = income_val - fixed_val

    st.markdown(f"**Monthly Income:** {format_currency(income_val)}")
    st.markdown(f"- **Fixed monthly costs / needs:** {format_currency(fixed_val)} (set by facilitator)")
    st.markdown(f"- **Available for allocation (income - fixed costs):** {format_currency(available)}")

    st.subheader("Initial Budget Allocation")
    if available < 0:
        st.error("Fixed costs exceed income. Adjust facilitator settings first.")
        init_wants = 0
        init_savings = 0
    else:
        col_w, col_s = st.columns(2)
        with col_w:
            init_wants = st.number_input("Wants (SAR)", min_value=0, step=50, value=max(0, available // 2), key="form_wants")
        with col_s:
            init_savings = st.number_input("Savings (SAR)", min_value=0, step=50, value=max(0, available - (available // 2)), key="form_savings")

    create_clicked = st.form_submit_button("Create Player")

    # Inline validation & visual feedback under fields
    if create_clicked:
        has_error = False
        if not team_name:
            st.error("Please enter a team name.")
            has_error = True
        if not player_name:
            st.error("Please enter a player name.")
            has_error = True
        if not savings_goal_desc:
            st.error("Please enter a short description for the savings goal.")
            has_error = True

        ok, msg = validate_allocation_total(income_val, fixed_val, init_wants, init_savings)
        if not ok:
            st.error(msg)
            has_error = True

        if not has_error:
            allocation = {"needs": fixed_val, "wants": init_wants, "savings": init_savings}
            new_player = {
                "team": team_name,
                "name": player_name,
                "savings_goal_desc": savings_goal_desc,
                # global goal lives in facilitator_settings
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
            st.session_state.current_player = len(st.session_state.players) - 1
            st.success(f"Player '{player_name}' added.")
            st.rerun()

# -------------------------------
# If no players, show info and stop here
# -------------------------------
if not st.session_state.players:
    st.info("Add a player using the form above to start playing.")
    st.stop()

# -------------------------------
# Main game UI (two columns) - right column is the shadow card
# -------------------------------
player = st.session_state.players[st.session_state.current_player]
# widen right panel by adjusting column ratios
game_col, stats_col = st.columns([1.3, 1.7], gap="large")

with game_col:
    # Header: show player name and team subtitle
    st.subheader(f"{player.get('name','Player Dashboard')}")
    st.markdown(f"<span style='color:gray; font-size:14px;'>{player.get('team','')}</span>", unsafe_allow_html=True)

    # Life card area
    rounds_played = int(player.get("rounds_played", 0))
    total_rounds = st.session_state.facilitator_settings.get("rounds", DEFAULT_FACILITATOR_SETTINGS["rounds"])
    progress = rounds_played / total_rounds if total_rounds else 0
    st.progress(progress)
    st.markdown(f"**Rounds Played:** {rounds_played}/{total_rounds}")

    st.markdown("### 🎴 Draw Life Card")
    if st.button("Draw Life Card"):
        if cards:
            st.session_state.current_card = random.choice(cards)
        else:
            st.warning("No life cards found in data/life_cards.json")

    card = st.session_state.current_card
    if card:
        st.markdown(f"#### {card.get('title','(untitled)')}")
        option_texts = [format_option_text(opt) for opt in card.get("options", [])]
        if option_texts:
            option_choice = st.radio("Choose an option", option_texts, key=f"choice_{player.get('name','')}")
            selected_index = option_texts.index(option_choice)
            selected_option = card["options"][selected_index]
            selected_option["card_title"] = card.get("title", "")

            # ensure per-round buckets are initialized
            if player.get("wants_balance", 0) == 0 and player.get("savings_balance", 0) == 0 and rounds_played < total_rounds:
                player = init_round_buckets(player)
                st.session_state.players[st.session_state.current_player] = player

            st.markdown(f"**Per-round buckets — Wants:** {format_currency(player.get('wants_balance',0))} • **Savings bucket:** {format_currency(player.get('savings_balance',0))}")

            if st.button("✅ Submit Decision"):
                valid, msg = is_valid_option_during_round(player, selected_option)
                if not valid:
                    st.warning(msg)
                else:
                    player = apply_option_and_settle(player, selected_option)
                    player["rounds_played"] = player.get("rounds_played", 0) + 1
                    # append to global decision log for display
                    st.session_state.decision_log.append(f"{player['name']} • {selected_option.get('text','')}")
                    # update player in session
                    st.session_state.players[st.session_state.current_player] = player
                    st.session_state.current_card = None
                    st.success("Decision applied and round settled.")
                    st.rerun()
        else:
            st.info("This card has no options.")

# -------------------------------
# Shadow stats panel (right)
# -------------------------------
with stats_col:
    fs_goal = st.session_state.facilitator_settings.get("goal", DEFAULT_FACILITATOR_SETTINGS["goal"])
    allocation = player.get("allocation", {"needs": player.get("income",0), "wants":0, "savings":0})
    wants_val = allocation.get("wants", 0)
    savings_val = allocation.get("savings", 0)
    income_val = player.get("income", 0)
    fixed_val = allocation.get("needs", st.session_state.facilitator_settings.get("fixed_costs", 0))
    remaining = income_val - fixed_val

    # Styled white panel with faint grey border
    st.markdown(
        f"""
        <div style='
            background-color: #ffffff;
            padding: 18px;
            border-radius: 16px;
            border: 1px solid #e6e6e6;
            width: 100%;
            min-width: 320px;
            margin-bottom: 12px;
        '>
        <h3 style="margin:0px;">{player.get('name','Player Dashboard')}</h3>
        <div style="color: #6b7280; margin-top:4px; font-size:13px;">{player.get('team','')}</div>
        <div style="margin-top:12px;">
        <b>Savings goal — description:</b> {player.get('savings_goal_desc','')}<br><br>
        <b>Current Savings:</b> {format_currency(player.get('savings',0))} ({int((player.get('savings',0)/max(1,fs_goal))*100)}%)<br>
        <progress value="{player.get('savings',0)}" max="{fs_goal}" style="width:100%; height:12px; margin-top:8px;"></progress><br><br>

        <b>Monthly Income:</b> {format_currency(income_val)}<br>
        <b>Fixed Expenses:</b> {format_currency(fixed_val)}<br>
        """
        + "</div></div>",
        unsafe_allow_html=True,
    )

    # Remaining budget display (color-coded)
    # This is displayed above the inline Wants/Savings inputs
    # Compute remaining AFTER allocations (but during editing, we show available before allocations)
    # For in-panel editing, we'll show Remaining Available (income - fixed) and Remaining after current inputs
    st.markdown("**Remaining Budget (available = income − fixed):**")
    st.markdown(f"**{format_currency(remaining)}**")

    # Inline side-by-side wants & savings and Save button
    st.markdown("")  # spacer
    cols = st.columns([1,1,0.6])
    # Use keys that won't clash across reruns
    with cols[0]:
        new_wants = st.number_input(
            "Wants (SAR)",
            min_value=0,
            max_value=remaining,
            value=wants_val,
            step=50,
            key="shadow_wants",
            label_visibility="visible",
        )
    with cols[1]:
        new_savings = st.number_input(
            "Savings (SAR)",
            min_value=0,
            max_value=remaining,
            value=savings_val,
            step=50,
            key="shadow_savings",
            label_visibility="visible",
        )

    total_alloc = new_wants + new_savings
    remaining_after = remaining - total_alloc

    # Color-coded remaining indicator (green if zero, red otherwise)
    if remaining_after == 0:
        rem_html = f"<div style='color: #059669; font-weight:600; margin-top:8px;'>Remaining after allocations: {format_currency(remaining_after)} ✅</div>"
    else:
        rem_html = f"<div style='color: #dc2626; font-weight:600; margin-top:8px;'>Remaining after allocations: {format_currency(remaining_after)}</div>"
    st.markdown(rem_html, unsafe_allow_html=True)

    # Save button: disabled until allocation matches exactly
    save_disabled = (total_alloc != remaining)
    if cols[2].button("💾 Save", disabled=save_disabled):
        # commit the allocation
        player["allocation"]["wants"] = int(new_wants)
        player["allocation"]["savings"] = int(new_savings)
        # init next round buckets if not mid-round
        if player.get("wants_balance", 0) == 0 and player.get("savings_balance", 0) == 0:
            player = init_round_buckets(player)
        st.session_state.players[st.session_state.current_player] = player
        st.session_state.decision_log.append(f"{player['name']} saved budget: Wants={new_wants}, Savings={new_savings}")
        st.success("Budget allocation updated!")

    # Stats lines (energy, wellbeing) below the budget area
    st.markdown("---")
    st.markdown(f"**Energy:** {player.get('time',5)} ⚡")
    st.markdown(f"**Well-being:** {player.get('emotion',5)} ❤️")

# -------------------------------
# Decision Log anchored at the very bottom (plain section)
# -------------------------------
st.markdown("---")
st.subheader("Decision Log")
if st.session_state.decision_log:
    for entry in reversed(st.session_state.decision_log):
        st.markdown(f"- {entry}")
else:
    st.caption("No decisions logged yet.")
