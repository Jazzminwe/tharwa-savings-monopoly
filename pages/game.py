import streamlit as st
import json
import random
import time

# -------------------------------
# Helper functions
# -------------------------------
def format_currency(value):
    return f"SAR {int(value):,}"

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
st.markdown("<style>div.block-container{padding-top:1rem;}</style>", unsafe_allow_html=True)

# -------------------------------
# Load life cards
# -------------------------------
if "life_cards" not in st.session_state:
    with open("data/life_cards.json", "r") as f:
        st.session_state.life_cards = json.load(f)

# -------------------------------
# Layout: Row 1 – Header
# -------------------------------
col1, col2 = st.columns([3, 1])

with col1:
    st.markdown("## 💰 **Savings Monopoly**")
    st.caption(f"👤 {player['name']} — *{player['team']}*")

with col2:
    rounds_played = player["rounds_played"]
    total_rounds = fs["rounds"]
    progress = rounds_played / max(1, total_rounds)
    st.markdown(
        f"""
        <div style="text-align:right;">
            <b>Rounds:</b> {rounds_played} / {total_rounds}<br>
            <progress value="{progress}" max="1" style="width:100%; height:10px; border-radius:6px;"></progress>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown("---")

# -------------------------------
# Automatic round contributions
# -------------------------------
if player.get("awaiting_round_start", False) and player["rounds_played"] > 0:
    ef_add = player["allocation"]["ef"]
    wants_add = player["allocation"]["wants"]

    projected = player["ef_balance"] + ef_add
    if ef_add > 0 and projected >= player["ef_cap"] and not player.get("ef_full_alert", False):
        player["ef_full_alert"] = True
        st.session_state.player = player
        st.rerun()

    player["ef_balance"] += min(ef_add, max(0, player["ef_cap"] - player["ef_balance"]))
    player["savings"] += player["allocation"]["savings"]
    player["wants_balance"] += wants_add

    player["awaiting_round_start"] = False
    st.session_state.player = player

# -------------------------------
# Row 2 – KPI Overview
# -------------------------------
kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns([2, 1, 1, 1])

with kpi_col1:
    pct = player["savings"] / fs["goal"] if fs["goal"] > 0 else 0
    st.markdown("### 💸 Savings Goal")
    st.caption(player["goal_desc"])
    st.progress(pct)
    st.markdown(f"**{format_currency(player['savings'])} / {format_currency(fs['goal'])}** ({int(pct*100)}%)")

with kpi_col2:
    st.markdown("### 🛟 Emergency Fund")
    st.markdown(f"**Balance:** {format_currency(player['ef_balance'])}")
    st.caption(f"Cap: {format_currency(player['ef_cap'])}")

with kpi_col3:
    st.markdown("### 🎉 Wants Fund")
    st.markdown(f"**Balance:** {format_currency(player['wants_balance'])}")
    st.caption(f"Monthly add: {format_currency(player['allocation']['wants'])}")

with kpi_col4:
    st.markdown("### ❤️⚡ Wellbeing / Time")
    st.markdown(f"**Wellbeing:** {render_emoji_stat(player['emotion'], '❤️')}")
    st.markdown(f"**Time:** {render_emoji_stat(player['time'], '⚡')}")

st.markdown("---")

# -------------------------------
# Row 3 – Game + Budget Area
# -------------------------------
left_col, right_col = st.columns([2, 1], gap="large")

# -------------------------------
# LEFT: Game area
# -------------------------------
with left_col:
    st.subheader("🎴 Game Round")

    game_over = player["rounds_played"] >= fs["rounds"]
    draw_disabled = player.get("current_card") is not None or game_over

    draw = st.button("🎴 Draw Life Card", type="primary", disabled=draw_disabled)

    # Card draw logic
    def allowed_types(round_idx, player):
        base = ["positive", "neutral", "negative_type_1"]
        if round_idx >= 4:
            base.append("negative_type_2")
        if player["savings"] >= fs["goal"] * 0.6:
            base.append("temptation")
        return base

    if draw and not draw_disabled:
        permitted = allowed_types(player["rounds_played"] + 1, player)
        pool = [c for c in st.session_state.life_cards if c.get("type") in permitted]
        if not pool:
            st.error("No life cards available for this stage. Please update life_cards.json.")
            st.stop()
        player["current_card"] = random.choice(pool)
        player["choice_made"] = False
        st.session_state.player = player

    # Display card
    if not player.get("current_card"):
        st.markdown("🃏 Draw a life card to start the month.")
    else:
        card = player["current_card"]
        st.subheader(card.get("title", "Life Event"))
        st.write(card.get("description", ""))

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
                    delta_money = selected.get("money", 0)
                    delta_wellbeing = selected.get("wellbeing", 0)
                    delta_time = selected.get("time", 0)

                    # Time exhaustion
                    if player["time"] <= 0 and delta_time > 0:
                        st.warning("⏳ Not enough energy for this choice.")
                        st.stop()

                    # Update wellbeing & time
                    player["emotion"] = max(0, min(10, player["emotion"] + delta_wellbeing))
                    player["time"] = max(0, min(10, player["time"] - delta_time))

                    if player["emotion"] <= 0:
                        st.error("💥 Burnout! Your wellbeing reached 0 — game over for you.")
                        st.stop()

                    # Spending / income logic
                    if delta_money < 0 and delta_wellbeing > 0:
                        cost = abs(delta_money)
                        wants = player["wants_balance"]
                        savings = player["savings"]

                        if wants >= cost:
                            player["wants_balance"] -= cost
                        else:
                            shortfall = cost - wants
                            if savings >= shortfall:
                                st.warning(
                                    f"You only have {format_currency(wants)} in your Wants fund. "
                                    f"The remaining {format_currency(shortfall)} will be deducted from Savings."
                                )
                                if st.button("Acknowledge and Continue"):
                                    player["wants_balance"] = 0
                                    player["savings"] -= shortfall
                                else:
                                    st.stop()
                            else:
                                st.error(
                                    f"🚫 Insufficient funds! You need {format_currency(cost)}, "
                                    f"but have only {format_currency(wants)} (Wants) and "
                                    f"{format_currency(savings)} (Savings). Choose another option."
                                )
                                st.stop()
                    elif card.get("ef_eligible", False) and delta_money < 0:
                        need = abs(delta_money)
                        cover = min(player["ef_balance"], need)
                        player["ef_balance"] -= cover
                        player["savings"] -= (need - cover)
                    else:
                        player["savings"] += delta_money

                    # End round
                    player["rounds_played"] += 1
                    player["decision_log"].append(f"{card['title']} — {choice}")
                    player["choice_made"] = True
                    player["current_card"] = None
                    if player["rounds_played"] < fs["rounds"]:
                        player["awaiting_round_start"] = True

                    st.session_state.player = player
                    st.success("✅ Decision saved! Stats updated.")
                    time.sleep(0.6)
                    st.rerun()

# -------------------------------
# RIGHT: Budget overview
# -------------------------------
with right_col:
    st.subheader("💰 Budget Overview")
    remaining = player["income"] - player["fixed_costs"]
    st.markdown(f"**Monthly Income:** {format_currency(player['income'])}")
    st.markdown(f"**Fixed Costs:** {format_currency(player['fixed_costs'])}")
    st.markdown(f"**Remaining:** {format_currency(remaining)}")

    st.markdown("---")
    wants = st.number_input("Wants", min_value=0, max_value=remaining, value=int(player["allocation"]["wants"]), step=50)
    ef = st.number_input("Emergency Fund", min_value=0, max_value=remaining, value=int(player["allocation"]["ef"]), step=50)
    savings = st.number_input("Savings Goal", min_value=0, max_value=remaining, value=int(player["allocation"]["savings"]), step=50)

    if st.button("💾 Save Budget"):
        if wants + ef + savings != remaining:
            st.warning(f"Allocations must equal remaining ({format_currency(remaining)}).")
        else:
            player["allocation"] = {"wants": wants, "ef": ef, "savings": savings}
            st.session_state.player = player
            st.success("✅ Budget updated!")

# -------------------------------
# Decision log
# -------------------------------
st.markdown("---")
st.subheader("🧾 Decision Log")
if player["decision_log"]:
    for i, d in enumerate(player["decision_log"], 1):
        st.write(f"**Round {i}:** {d}")
else:
    st.caption("No decisions logged yet.")
