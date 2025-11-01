import streamlit as st
import random
import json

# ---------------------------------------
# Helper functions
# ---------------------------------------
def format_currency(value):
    return f"SAR {value:,}"

def render_emoji_stat(value, emoji, max_value=10):
    """Return emoji repeated for each point and show as x/10."""
    full = emoji * int(value)
    empty = "▫️" * int(max_value - value)
    return f"{full}{empty} <span style='color:#6b7280;'>({int(value)}/{max_value})</span>"

# ---------------------------------------
# Load facilitator settings & player
# ---------------------------------------
if "player" not in st.session_state or "facilitator_settings" not in st.session_state:
    st.warning("No player data found. Please start from the setup page.")
    st.stop()

player = st.session_state.player
fs = st.session_state.facilitator_settings

# ---------------------------------------
# Layout
# ---------------------------------------
st.set_page_config(layout="wide")
st.title("🎲 Draw Life Card")

game_col, stats_col = st.columns([1.2, 1])

# -------------------------------
# Left column — Life card logic
# -------------------------------
with game_col:
    st.markdown("### Draw Life Card")
    st.progress(player["rounds_played"] / fs["rounds"])
    st.markdown(f"**Rounds Played:** {player['rounds_played']}/{fs['rounds']}")

    if "life_cards" not in st.session_state:
        with open("data/life_cards.json", "r") as f:
            st.session_state.life_cards = json.load(f)

    if st.button("Draw Life Card"):
        player["current_card"] = random.choice(st.session_state.life_cards)
        st.session_state.player = player

    if player.get("current_card"):
        card = player["current_card"]
        st.markdown(f"### {card['title']}")
        st.write(card["description"])

        options = [f"{opt['label']} → Money: {opt['money']}, Wellbeing: {opt['wellbeing']}, Time: {opt['time']}" for opt in card["options"]]
        choice = st.radio("Choose an option:", options, key="decision_choice")

        if st.button("✅ Submit Decision"):
            selected = card["options"][options.index(choice)]
            player["savings"] += selected["money"]
            player["emotion"] = min(10, max(0, player["emotion"] + selected["wellbeing"]))
            player["time"] = min(10, max(0, player["time"] - selected["time"]))
            player["rounds_played"] += 1
            player["decision_log"].append(choice)
            st.session_state.player = player
            st.success("Decision logged!")

# -------------------------------
# Right column — Player stats
# -------------------------------
with stats_col:
    remaining = player["income"] - player["fixed_costs"]
    wants_val = player["allocation"]["wants"]
    savings_val = player["allocation"]["savings"]
    total = wants_val + savings_val
    color = "#059669" if total == remaining else "#dc2626"

    # --- Player stats card ---
    st.markdown(
        f"""
        <div style='background-color:#ffffff;
                    padding:24px;
                    border-radius:20px;
                    box-shadow:0 4px 10px rgba(0,0,0,0.08);
                    margin-bottom:1.5rem;'>
            <h3 style="margin-bottom:0;">{player['name']}</h3>
            <div style="color:#6b7280; font-size:13px;">{player['team']}</div>
            <hr style="margin:8px 0 12px 0; border:none; border-top:1px solid #e5e7eb;">

            <b>Savings Goal:</b> {player['goal_desc']}<br>
            <b>Current Savings:</b> {format_currency(player['savings'])}
            ({int((player['savings']/max(1,fs['goal']))*100)}%)<br>
            <progress value="{player['savings']}" max="{fs['goal']}" 
                      style="width:100%;height:8px;border-radius:6px;background:#f3f4f6;"></progress>

            <div style="margin-top:12px;">
                <b>Energy:</b> {render_emoji_stat(player['time'], '⚡')}<br>
                <b>Well-being:</b> {render_emoji_stat(player['emotion'], '❤️')}
            </div>

            <hr style="margin:14px 0; border:none; border-top:1px solid #e5e7eb;">
            <b>Monthly Income:</b> {format_currency(player['income'])}<br>
            <b>Fixed Expenses:</b> {format_currency(player['fixed_costs'])}<br>
            <b style="color:{color};">Remaining Budget:</b> {format_currency(remaining)}
        </div>
        """,
        unsafe_allow_html=True,
    )

    # --- Budget Allocation section ---
    st.markdown(
        "<h4 style='margin-top:0.5rem;'>💰 Budget Allocation</h4>"
        "<p style='color:#6b7280;font-style:italic;margin-top:-8px;'>Adjust your monthly distribution</p>",
        unsafe_allow_html=True,
    )

    st.markdown(
        "<div style='background-color:#f9fafb;border:1px solid #e5e7eb;"
        "padding:16px;border-radius:12px;margin-top:-10px;'>",
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

    valid = (new_wants + new_savings) == remaining
    if not valid:
        st.warning(f"⚠️ Allocations must equal remaining budget ({format_currency(remaining)}).")
    else:
        player["allocation"]["wants"] = new_wants
        player["allocation"]["savings"] = new_savings
        st.session_state.player = player

# -------------------------------
# Decision log at the bottom
# -------------------------------
st.markdown("---")
st.markdown("### 🧾 Decision Log")
if player["decision_log"]:
    for i, d in enumerate(player["decision_log"], 1):
        st.write(f"**Round {i}:** {d}")
else:
    st.caption("No decisions logged yet.")
