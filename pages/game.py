import streamlit as st
import random
import json

# ---------------------------------------
# Helper functions
# ---------------------------------------
def format_currency(value):
    return f"SAR {value:,}"

def render_emoji_stat(value, emoji, max_value=10):
    full = emoji * int(value)
    empty = "▫️" * int(max_value - value)
    return f"{full}{empty} ({int(value)}/{max_value})"

def team_color(team):
    palette = {
        "Thuraya": "#1E88E5",
        "Horizon": "#43A047",
        "Nova": "#FDD835",
        "Orion": "#FB8C00",
    }
    return palette.get(team, "#6366F1")  # default indigo

# ---------------------------------------
# Setup
# ---------------------------------------
if "player" not in st.session_state or "facilitator_settings" not in st.session_state:
    st.warning("No player data found. Please start from the setup page.")
    st.stop()

player = st.session_state.player
fs = st.session_state.facilitator_settings

st.set_page_config(layout="wide")
st.title("🎲 Draw Life Card")
st.markdown("---")

# ---------------------------------------
# Layout
# ---------------------------------------
left_col, right_col = st.columns([1.2, 1], gap="large")

# -------------------------------
# 🎴 Left: Game Area
# -------------------------------
with left_col:
    st.markdown("## 🎴 Draw Life Card")

    st.progress(player["rounds_played"] / fs["rounds"])
    st.caption(f"Rounds Played: {player['rounds_played']} / {fs['rounds']}")
    st.write(" ")

    if "life_cards" not in st.session_state:
        with open("data/life_cards.json", "r") as f:
            st.session_state.life_cards = json.load(f)

    if st.button("Draw Life Card", type="primary"):
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
# 🧍 Right: Single Unified Player Card
# -------------------------------
with right_col:
    color = team_color(player["team"])

    st.markdown(
        f"""
        <style>
        .player-card {{
            background-color: #ffffff;
            border-radius: 18px;
            box-shadow: 0 6px 18px rgba(0,0,0,0.07);
            padding: 25px 30px;
            margin-bottom: 1.5rem;
            position: relative;
        }}
        .player-card::before {{
            content: "";
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 8px;
            border-top-left-radius: 18px;
            border-top-right-radius: 18px;
            background-color: {color};
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )

    with st.container():
        st.markdown('<div class="player-card">', unsafe_allow_html=True)

        # --- Player Header ---
        st.markdown(f"### 🧍 {player['name']}")
        st.caption(f"Team: {player['team']}")
        st.write(" ")

        # --- Goal & Savings ---
        st.markdown(f"**Savings Goal:** {player['goal_desc']}")
        st.markdown(f"**Current Savings:** {format_currency(player['savings'])} "
                    f"({int((player['savings'] / max(1, fs['goal'])) * 100)}%)")
        st.progress(player["savings"] / fs["goal"])

        # --- Emoji Stats ---
        st.write("")
        st.markdown(f"**Energy:** {render_emoji_stat(player['time'], '⚡')}")
        st.markdown(f"**Well-being:** {render_emoji_stat(player['emotion'], '❤️')}")
        st.divider()

        # --- Financial Overview ---
        remaining = player["income"] - player["fixed_costs"]
        wants_val = player["allocation"]["wants"]
        savings_val = player["allocation"]["savings"]

        st.markdown(f"**Monthly Income:** {format_currency(player['income'])}")
        st.markdown(f"**Fixed Expenses:** {format_currency(player['fixed_costs'])}")
        st.markdown(f"**Remaining Budget:** {format_currency(remaining)}")

        # --- Budget Allocation ---
        st.markdown("---")
        st.markdown("### 💰 Budget Allocation")
        st.caption("Adjust your monthly distribution below:")

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
                st.success("✅ Budget updated!")

        st.markdown("</div>", unsafe_allow_html=True)

# -------------------------------
# 🧾 Decision log
# -------------------------------
st.markdown("---")
st.subheader("🧾 Decision Log")
if player["decision_log"]:
    for i, d in enumerate(player["decision_log"], 1):
        st.write(f"**Round {i}:** {d}")
else:
    st.caption("No decisions logged yet.")
