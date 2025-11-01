# ============================
# app.py (Setup)
# ============================
import streamlit as st

# ----------------------------------------
# Page config
# ----------------------------------------
st.set_page_config(page_title="Savings Monopoly — Setup", layout="centered")
st.title("💰 Savings Monopoly — Setup")

# ----------------------------------------
# Initialize facilitator settings (defaults)
# ----------------------------------------
if "facilitator_settings" not in st.session_state:
    st.session_state.facilitator_settings = {
        "goal": 5000,
        "income": 2000,
        "rounds": 10,
        "fixed_costs": 1000,
        "ef_cap": 3000,
    }

fs = st.session_state.facilitator_settings

# ----------------------------------------
# Facilitator Setup (sidebar)
# ----------------------------------------
st.sidebar.header("Facilitator Settings")
goal = st.sidebar.number_input("Savings goal (SAR)", min_value=0, value=fs["goal"], step=100)
income = st.sidebar.number_input("Monthly income (SAR)", min_value=0, value=fs["income"], step=100)
fixed_costs = st.sidebar.number_input("Fixed monthly costs / NEEDS (SAR)", min_value=0, value=fs["fixed_costs"], step=50)
rounds = st.sidebar.number_input("Number of rounds (months)", min_value=1, value=fs["rounds"], step=1)
default_cap = max(0, fixed_costs * 3)
ef_cap = st.sidebar.number_input("Emergency fund cap (SAR)", min_value=0, value=fs.get("ef_cap", default_cap) or default_cap, step=100)

st.session_state.facilitator_settings = {"goal": goal, "income": income, "rounds": rounds, "fixed_costs": fixed_costs, "ef_cap": ef_cap}

# ----------------------------------------
# Player Creation Form
# ----------------------------------------
st.header("Create Player")

with st.form("create_player_form"):
    team = st.text_input("Team Name")
    name = st.text_input("Player Name")
    desc = st.text_input("Savings Goal Description")

    income_val = income
    fixed_val = fixed_costs
    available = max(0, income_val - fixed_val)
    st.markdown(f"**Available monthly budget:** SAR {available:,}")

    c1, c2, c3 = st.columns(3)
    with c1:
        wants = st.number_input("Wants (SAR)", min_value=0, max_value=available, step=50, value=max(0, available // 3))
    with c2:
        ef = st.number_input("Emergency Fund (SAR)", min_value=0, max_value=available, step=50, value=max(0, available // 3))
    with c3:
        savings = st.number_input("Savings Goal (SAR)", min_value=0, max_value=available, step=50, value=max(0, available - (wants + ef)))

    submitted = st.form_submit_button("Create Player")

    if submitted:
        has_error = False
        if not team:
            st.error("Please enter a team name.")
            has_error = True
        if not name:
            st.error("Please enter a player name.")
            has_error = True
        if not desc:
            st.error("Please enter a savings goal description.")
            has_error = True
        if wants + ef + savings != available:
            st.error(f"Wants + Emergency Fund + Savings must equal remaining budget ({available}).")
            has_error = True

        if not has_error:
            st.session_state.player = {
                "team": team,
                "name": name,
                "goal_desc": desc,
                "income": income_val,
                "fixed_costs": fixed_val,
                "allocation": {"wants": wants, "ef": ef, "savings": savings},
                "rounds_played": 0,
                "savings": 0,
                "ef_balance": 0,
                "ef_cap": ef_cap,
                "emotion": 5,
                "time": 5,
                "decision_log": [],
                "current_card": None,
                "choice_made": False,
                "awaiting_round_start": True,
                "ef_full_alert": False,
            }
            st.success(f"✅ Player {name} created! Redirecting to game…")
            st.switch_page("pages/game.py")

st.markdown("---")
st.caption("The Emergency Fund is visible from the start. Each round adds your EF and Savings Goal amounts before drawing a card.")

