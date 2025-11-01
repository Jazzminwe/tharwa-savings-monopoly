import streamlit as st
import random
import json
import time

# -------------------------------
# Helper functions
# -------------------------------
def format_currency(value):
    return f"SAR {value:,}"

def render_emoji_stat(value, emoji, max_value=10):
    full = emoji * int(value)
    empty = "▫️" * int(max_value - value)
    return f"{full}{empty} ({int(value)}/{max_value})"


# -------------------------------
# Setup
# -------------------------------
if "player" not in st.session_state or "facilitator_settings" not in st.session_state:
    st.warning("No player data found. Please start from the setup page.")
    st.stop()

player = st.session_state.player
fs = st.session_state.facilitator_settings

st.set_page_config(layout="wide")
st.title("💰 Savings Monopoly")
st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)

# -------------------------------
# Layout columns
# -------------------------------
left_col, right_col = st.columns([1.2, 1], gap="large")

# -------------------------------
# 🎴 LEFT: Game Area
# -------------------------------
with left_col:
    draw_disabled = player.get("current_card") is not None
    draw = st.button("🎴 Draw Life Card", type="primary", disabled=draw_disabled)

    # --- Compact progress bar styling
    progress_fraction = player["rounds_played"] / fs["rounds"]
    st.markdown(
        f"""
        <div style="width:70%; margin-top:0.5rem;">
            <progress value="{progress_fraction}" max="1" style="width:100%; height:8px; border-radius:4px;"></progress>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.caption(f"Rounds Played: {player['rounds_played']} / {fs['rounds']}")
    st.write(" ")

    # Load life cards if not already
    if "life_cards" not in st.session_state:
        with open("data/life_cards.json", "r") as f:
            st.session_state.life_cards = json.load(f)

    # Draw new card (only if allowed)
    if draw and not draw_disabled:
        player["current_card"] = random.choice(st.session_state.life_cards)
        player["choice_made"] = False
        st.session_state.player = player

    # --- Display current card or blank prompt
    if not player.get("current_card"):
        st.markdown("## 🎴 Draw a life card to start the game!")
    else:
        card = player["current_card"]
        title = card.get("title", "Life Event")
        desc = card.get("description", "")
        st.subheader(title)
        if desc:
            st.write(desc)

        # Prepare card options
        options = []
        for opt in card.get("options", []):
            label = opt.get("label", "Option")
            money = opt.get("money", 0)
            wellbeing = opt.get("wellbeing", 0)
            time_cost = opt.get("time", 0)
            options.append(f"{label} → Money: {money}, Wellbeing: {wellbeing}, Time: {time_cost}")

        if options:
            choice = st.radio("Choose an option:", options, key="decision_choice")

            if st.button("💾 Save Decision", key="save_decision"):
                if not player.get("choice_made"):
                    selected = card["options"][options.index(choice)]
                    player["savings"] += selected.get("money", 0)
                    player["emotion"] = min(10, max(0, player["emotion"] + selected.get("wellbeing", 0)))
                    player["time"] = min(10, max(0, player["time"] - selected.get("time", 0)))
                    player["rounds_played"] += 1
                    player["decision_log"].append(choice)
                    player["choice_made"] = True
                    player["current_card"] = None
                    st.session_state.player = player
                    st.success("✅ Decision saved! Stats updated.")
                    time.sleep(0.8)
                    st.rerun()
        else:
            st.warning("⚠️ This card has no available options.")


# -------------------------------
# 🧍 RIGHT: Player Stats
# -------------------------------
with right_col:
    # Style for shadow box
    st.markdown("""
        <style>
        .stats-box {
            background-color: #ffffff;
            border-radius: 18px;
            box-shadow: 0 6px 18px rgba(0,0,0,0.08);
            padding: 24px 28px;
        }
        </style>
        <div class="stats-box">
    """, unsafe_allow_html=True)

    st.markdown(f"### 🧍 {player['name']}")
    st.caption(f"Team: {player['team']}")
    st.write(" ")

    st.markdown(f"**Savings Goal:** {player['goal_desc']}")
    st.markdown(
        f"**Current Savings:** {format_currency(player['savings'])} "
        f"({int((player['savings'] / max(1, fs['goal'])) * 100)}%)"
    )
    st.progress(player["savings"] / fs["goal"])

    st.write("")
    st.markdown(f"**Energy:** {render_emoji_stat(player['time'], '⚡')}")
    st.markdown(f"**Well-being:** {render_emoji_stat(player['emotion'], '❤️')}")
    st.divider()

    remaining = player["income"] - player["fixed_costs"]
    wants_val = player["allocation"]["wants"]
    savings_val = player["allocation"]["savings"]

    st.markdown(f"**Monthly Income:** {format_currency(player['income'])}")
    st.markdown(f"**Fixed Expenses:** {format_currency(player['fixed_costs'])}")
    st.markdown(f"**Remaining Budget:** {format_currency(remaining)}")

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
        save = st.button("💾 Save Budget", use_container_width=True)

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
