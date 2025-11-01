import streamlit as st
import random
import json

# -------------------------------
# Verify session state
# -------------------------------
if "player" not in st.session_state or "facilitator_settings" not in st.session_state:
    st.warning("Please create a player first.")
    st.stop()

player = st.session_state.player
fs = st.session_state.facilitator_settings

st.set_page_config(page_title="Savings Monopoly Game", layout="wide")

# -------------------------------
# Load life cards
# -------------------------------
try:
    with open("data/life_cards.json") as f:
        cards = json.load(f)
except Exception:
    cards = []

# -------------------------------
# Helper functions
# -------------------------------
def format_currency(n):
    return f"SAR {n:,.0f}"

def apply_option(player, option):
    player["emotion"] = max(0, min(10, player["emotion"] + option.get("wellbeing", 0)))
    player["time"] += option.get("time", 0)
    money = option.get("money", 0)
    if money < 0:
        cost = -money
        # deduct from wants first
        w = min(player["allocation"]["wants"], cost)
        player["allocation"]["wants"] -= w
        cost -= w
        if cost > 0:
            s = min(player["allocation"]["savings"], cost)
            player["allocation"]["savings"] -= s
    else:
        player["savings"] += money
    player["rounds_played"] += 1
    player["decision_log"].append(f"{option.get('card_title', '')} — {option.get('text', '')}")
    return player

# -------------------------------
# Layout
# -------------------------------
game_col, stats_col = st.columns([1.3, 1.7], gap="large")

# -------------------------------
# Left column — gameplay
# -------------------------------
with game_col:
    # top view-results button if finished
    if player["rounds_played"] >= fs["rounds"]:
        st.success("✅ All rounds complete!")
        if st.button("🎉 View Results"):
            st.switch_page("pages/results.py")
        st.stop()

    st.markdown("## 🎴 Draw Life Card")
    rounds_played = player["rounds_played"]
    st.progress(rounds_played / fs["rounds"])
    st.markdown(f"**Rounds Played:** {rounds_played}/{fs['rounds']}")

    if st.button("Draw Life Card"):
        if cards:
            st.session_state.current_card = random.choice(cards)
        else:
            st.warning("No life cards found in data/life_cards.json")

    card = st.session_state.get("current_card")
    if card:
        st.markdown(f"### {card['title']}")
        options = card.get("options", [])
        if options:
            opts = [f"{o['text']} → Money: {o['money']}, Wellbeing: {o['wellbeing']}, Time: {o['time']}" for o in options]
            choice = st.radio("Choose an option:", opts)
            selected = options[opts.index(choice)]
            if st.button("✅ Submit Decision"):
                player = apply_option(player, selected)
                st.session_state.player = player
                st.session_state.current_card = None
                st.success("Decision applied!")
                st.rerun()

# -------------------------------
# Right column — player stats
# -------------------------------
with stats_col:
    remaining = player["income"] - player["fixed_costs"]
    wants_val = player["allocation"]["wants"]
    savings_val = player["allocation"]["savings"]
    total = wants_val + savings_val
    color = "#059669" if total == remaining else "#dc2626"

    st.markdown(
        f"""
        <div style='background-color:#fff;
                    padding:24px;
                    border-radius:18px;
                    border:1px solid #e5e7eb;
                    overflow-wrap:break-word;
                    white-space:normal;
                    box-sizing:border-box;'>
            <h3 style="margin-bottom:0;">{player['name']}</h3>
            <div style="color:#6b7280; font-size:13px;">{player['team']}</div>
            <br>

            <b>Savings Goal:</b> {player['goal_desc']}<br>
            <b>Current Savings:</b> {format_currency(player['savings'])}
            ({int((player['savings']/max(1,fs['goal']))*100)}%)<br>
            <progress value="{player['savings']}" max="{fs['goal']}" style="width:100%;height:8px;border-radius:8px;"></progress>
            <br>

            <b>Energy:</b> {player['time']} ⚡<br>
            <b>Well-being:</b> {player['emotion']} ❤️<br><br>

            <b>Monthly Income:</b> {format_currency(player['income'])}<br>
            <b>Fixed Expenses:</b> {format_currency(player['fixed_costs'])}<br>
            <b style="color:{color};">Remaining Budget:</b> {format_currency(remaining)}<br>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Budget Allocation block
    st.markdown(
        "<h4 style='margin-top:1.5rem;'>💰 Budget Allocation</h4>"
        "<p style='color:#6b7280;font-style:italic;margin-top:-10px;'>Adjust monthly allocation</p>",
        unsafe_allow_html=True,
    )

    with st.container():
        st.markdown(
            """
            <div style='background-color:#f9fafb;
                        border:1px solid #e5e7eb;
                        padding:16px;
                        border-radius:12px;
                        margin-bottom:10px;'>
            """,
            unsafe_allow_html=True,
        )
        col1, col2, col3 = st.columns([1, 1, 0.6])
        with col1:
            new_wants = st.number_input("Wants (SAR)", min_value=0, max_value=remaining, value=wants_val, step=50)
        with col2:
            new_savings = st.number_input("Savings (SAR)", min_value=0, max_value=remaining, value=savings_val, step=50)
        with col3:
            st.markdown("<br>", unsafe_allow_html=True)
            st.button("💾 Save", use_container_width=True)

        st.markdown("</div>", unsafe_allow_html=True)

    # Validate and update
    valid = (new_wants + new_savings) == remaining
    if not valid:
        st.warning(f"⚠️ Allocations must equal remaining budget ({format_currency(remaining)}).")
    else:
        player["allocation"]["wants"] = new_wants
        player["allocation"]["savings"] = new_savings
        st.session_state.player = player


# -------------------------------
# Bottom — decision log (plain)
# -------------------------------
st.markdown("---")
st.subheader("🧾 Decision Log")
if player["decision_log"]:
    for entry in reversed(player["decision_log"]):
        st.markdown(f"- {entry}")
else:
    st.caption("No decisions logged yet.")
