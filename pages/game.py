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
    return f"{full}{empty} ({int(value)}/{max_value})"

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
    st.header("Draw Life Card")
    st.progress(player["rounds_played"] / fs["rounds"])
    st.write(f"**Rounds Played:** {player['rounds_played']}/{fs['rounds']}")

    if "life_cards" not in st.session_state:
        with open("data/life_cards.json", "r") as f:
            st.session_state.life_cards = json.load(f)

    if st.button("Draw Life Card"):
        player["current_card"] = random.choice(st.session_state.life_cards)
        st.session_state.player = player

    if player.get("current_card"):
        card = player["current_card"]
        st.subheader(card["title"])
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
    st.subheader(player["name"])
    st.caption(player["team"])

    st.markdown(f"**Savings Goal:** {player['goal_desc']}")
    st.markdown(f"**Current Savings:** {format_currency(player['savings'])} "
                f"({int((player['savings'] / max(1, fs['goal'])) * 100)}%)")
    st.progress(player["savings"] / fs["goal"])

    st.write(f"**Energy:** {render_emoji_stat(player['time'], '⚡')}")
    st.write(f"**Well-being:** {render_emoji_stat(player['emotion'], '❤️')}")

    st.divider()
    st.write(f"**Monthly Income:** {format_currency(player['income'])}")
    st.write(f"**Fixed Expenses:** {format_currency(player['fixed_costs'])}")

    remaining = player["income"] - player["fixed_costs"]
    wants_val = player["allocation"]["wants"]
    savings_val = player["allocation"]["savings"]
    total = wants_val + savings_val

    st.markdown(f"**Remaining Budget:** {format_currency(remaining)}")

    # Budget allocation section
    st.markdown("### 💰 Budget Allocation")
    st.caption("Adjust your monthly distribution")

    col1, col2, col3 = st.columns([1, 1, 0.5])
    with col1:
        new_wants = st.number_input("Wants (SAR)", min_value=0, max_value=remaining, value=wants_val, step=50)
    with col2:
        new_savings = st.number_input("Savings (SAR)", min_value=0, max_value=remaining, value=savings_val, step=50)
    with col3:
        st.markdown("<br>", unsafe_allow_html=True)
        save = st.button("💾 Save", use_container_width=True)

    if save:
        if (new_wants + new_savings) != remaining:
            st.warning(f"⚠️ Allocations must equal remaining budget ({format_currency(remaining)}).")
        else:
            player["allocation"]["wants"] = new_wants
            player["allocation"]["savings"] = new_savings
            st.session_state.player = player
            st.success("Budget updated!")

# -------------------------------
# Decision log at the bottom
# -------------------------------
st.divider()
st.subheader("🧾 Decision Log")
if player["decision_log"]:
    for i, d in enumerate(player["decision_log"], 1):
        st.write(f"**Round {i}:** {d}")
else:
    st.caption("No decisions logged yet.")
