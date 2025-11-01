import streamlit as st

# ----------------------------------------
# Initialize session state
# ----------------------------------------
if "facilitator_settings" not in st.session_state:
    st.session_state.facilitator_settings = {
        "goal": 5000,
        "income": 2000,
        "rounds": 10,
        "fixed_costs": 1000,
    }

st.set_page_config(page_title="Savings Monopoly Setup", layout="centered")
st.title("💰 Savings Monopoly — Setup")

# ----------------------------------------
# Facilitator Setup (sidebar)
# ----------------------------------------
st.sidebar.header("Facilitator Settings")
goal = st.sidebar.number_input("Savings goal (SAR)", min_value=0, value=st.session_state.facilitator_settings["goal"], step=100)
income = st.sidebar.number_input("Monthly income (SAR)", min_value=0, value=st.session_state.facilitator_settings["income"], step=100)
fixed_costs = st.sidebar.number_input("Fixed monthly costs / needs (SAR)", min_value=0, value=st.session_state.facilitator_settings["fixed_costs"], step=100)
rounds = st.sidebar.number_input("Number of rounds", min_value=1, value=st.session_state.facilitator_settings["rounds"], step=1)

st.session_state.facilitator_settings = {
    "goal": goal,
    "income": income,
    "rounds": rounds,
    "fixed_costs": fixed_costs,
}

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
    available = income_val - fixed_val
    st.markdown(f"**Available monthly budget:** SAR {available:,}")

    col1, col2 = st.columns(2)
    with col1:
        wants = st.number_input("Wants (SAR)", min_value=0, max_value=available, step=50, value=max(0, available // 2))
    with col2:
        savings = st.number_input("Savings (SAR)", min_value=0, max_value=available, step=50, value=max(0, available - (available // 2)))

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
        if wants + savings != available:
            st.error(f"Wants + Savings must equal remaining budget ({available}).")
            has_error = True

        if not has_error:
            st.session_state.player = {
                "team": team,
                "name": name,
                "goal_desc": desc,
                "income": income_val,
                "fixed_costs": fixed_val,
                "allocation": {"wants": wants, "savings": savings},
                "rounds_played": 0,
                "savings": 0,
                "emotion": 5,
                "time": 5,
                "decision_log": [],
            }
            st.success(f"✅ Player {name} created! Redirecting to game...")
            st.switch_page("game")
