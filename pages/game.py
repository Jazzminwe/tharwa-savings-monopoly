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
st.title("💰 Savings Monopoly")

# -------------------------------
# Load life cards
# -------------------------------
if "life_cards" not in st.session_state:
    with open("data/life_cards.json", "r") as f:
        st.session_state.life_cards = json.load(f)

# Initialize wants fund if missing
if "wants_balance" not in player:
    player["wants_balance"] = 0

# -------------------------------
# Emergency Fund full popup
# -------------------------------
if player.get("ef_full_alert", False):
    st.markdown("## 🚨 Emergency Fund Full")
    st.info(
        f"Your Emergency Fund cap is {format_currency(player['ef_cap'])}. "
        f"Current: {format_currency(player['ef_balance'])}.\n\n"
        "Future EF contributions won't fit. Redirect EF to Savings Goal?"
    )
    c1, c2 = st.columns(2)
    with c1:
        if st.button("✅ Redirect EF contribution to Savings Goal"):
            moved = player["allocation"]["ef"]
            player["allocation"]["savings"] += moved
            player["allocation"]["ef"] = 0
            player["ef_full_alert"] = False
            st.session_state.player = player
            st.rerun()
    with c2:
        if st.button("✖️ Keep EF as is"):
            player["ef_full_alert"] = False
            st.session_state.player = player
            st.rerun()
    st.stop()

# -------------------------------
# Automatic contributions (post-round)
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
# Layout
# -------------------------------
left_col, right_col = st.columns([1.2, 1], gap="large")

# -------------------------------
# LEFT: Game Area
# -------------------------------
with left_col:
    progress_fraction = player["rounds_played"] / max(1, fs["rounds"])
    st.progress(progress_fraction)
    st.caption(f"Rounds Played: {player['rounds_played']} / {fs['rounds']}")

    # Determine allowed card types
    def allowed_types(round_idx, player):
        base = ["positive", "neutral", "negative_type_1"]
        if round_idx >= 4:
            base.append("negative_type_2")
        if player["savings"] >= fs["goal"] * 0.6:
            base.append("temptation")
        return base

    game_over = player["rounds_played"] >= fs["rounds"]
    draw_disabled = player.get("current_card") is not None or game_over

    if game_over:
        st.success("🏁 Game finished! Great job.")

    draw = st.button("🎴 Draw Life Card", type="primary", disabled=draw_disabled)

    if draw and not draw_disabled:
        permitted = allowed_types(player["rounds_played"] + 1, player)
        pool = [c for c in st.session_state.life_cards if c.get("type") in permitted]
        if not pool:
            st.error(f"No life cards available for round type(s): {permitted}. Please check life_cards.json.")
            st.stop()
        player["current_card"] = random.choice(pool)
        player["choice_made"] = False
        st.session_state.player = player

    # Display current card
    if not player.get("current_card"):
        st.markdown("## 🎴 Draw a life card to start the month.")
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

                    # Time exhaustion check
                    if player["time"] <= 0 and delta_time > 0:
                        st.warning("⏳ You don’t have enough energy for this choice — it won’t be applied.")
                        st.stop()

                    # Update wellbeing and time
                    old_emotion = player["emotion"]
                    player["emotion"] = max(0, min(10, old_emotion + delta_wellbeing))
                    player["time"] = max(0, min(10, player["time"] - delta_time))

                    # Burnout check
                    if player["emotion"] <= 0:
                        st.error("💥 Burnout! Your wellbeing reached 0 — you’ve burned out and can’t continue.")
                        st.markdown("Return to the group screen to discuss your results.")
                        st.stop()

                    # -----------------------
                    # MONEY HANDLING LOGIC
                    # -----------------------
                    if delta_money < 0 and delta_wellbeing > 0:
                        # Spending for wellbeing (Wants → Savings hierarchy)
                        cost = abs(delta_money)
                        wants = player["wants_balance"]
                        savings = player["savings"]

                        if wants >= cost:
                            # Fully covered by wants
                            player["wants_balance"] -= cost

                        else:
                            # Wants insufficient → check savings
                            shortfall = cost - wants
                            if savings >= shortfall:
                                st.warning(
                                    f"You only have {format_currency(wants)} in your Wants fund. "
                                    f"The remaining {format_currency(shortfall)} will be deducted from your Savings Goal."
                                )
                                if st.button("Acknowledge and Continue"):
                                    player["wants_balance"] = 0
                                    player["savings"] -= shortfall
                                else:
                                    st.stop()
                            else:
                                st.error(
                                    f"🚫 Insufficient funds! You need {format_currency(cost)}, "
                                    f"but only have {format_currency(wants)} in Wants and {format_currency(savings)} in Savings. "
                                    f"Please pick another option."
                                )
                                st.stop()

                    elif card.get("ef_eligible", False) and delta_money < 0:
                        # Emergency fund applies
                        need = abs(delta_money)
                        cover = min(player["ef_balance"], need)
                        player["ef_balance"] -= cover
                        player["savings"] -= (need - cover)
                    else:
                        # Regular income/expense
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
        else:
            st.warning("⚠️ This card has no available options.")

# -------------------------------
# RIGHT: Player Stats
# -------------------------------
with right_col:
    st.markdown("### 🧍 Player Stats")
    st.markdown(f"**{player['name']} ({player['team']})**")

    pct = player["savings"] / fs["goal"] if fs["goal"] > 0 else 0
    st.progress(pct)
    st.markdown(f"**Savings:** {format_currency(player['savings'])} ({int(pct * 100)}%)")
    st.markdown(f"**Time:** {render_emoji_stat(player['time'], '⚡')}")
    st.markdown(f"**Wellbeing:** {render_emoji_stat(player['emotion'], '❤️')}")
    st.divider()

    remaining = player["income"] - player["fixed_costs"]
    st.markdown(f"**Monthly Income:** {format_currency(player['income'])}")
    st.markdown(f"**Fixed Costs:** {format_currency(player['fixed_costs'])}")
    st.markdown(f"**Remaining:** {format_currency(remaining)}")

    st.markdown("---")
    st.markdown("### 💰 Budget Allocation")

    wants = st.number_input("Wants", min_value=0, max_value=remaining, value=int(player["allocation"]["wants"]), step=50)
    ef = st.number_input("Emergency Fund", min_value=0, max_value=remaining, value=int(player["allocation"]["ef"]), step=50)
    savings = st.number_input("Savings Goal", min_value=0, max_value=remaining, value=int(player["allocation"]["savings"]), step=50)

    if st.button("💾 Save Budget"):
        if wants + ef + savings != remaining:
            st.warning(f"Allocations must equal remaining budget ({format_currency(remaining)}).")
        else:
            player["allocation"] = {"wants": wants, "ef": ef, "savings": savings}
            st.session_state.player = player
            st.success("✅ Budget updated!")

    st.markdown("---")
    st.markdown("### 🛟 Emergency Fund")
    st.markdown(f"**Balance:** {format_currency(player['ef_balance'])}")
    st.markdown(f"**Cap:** {format_currency(player['ef_cap'])}")
    st.markdown("---")
    st.markdown("### 🎉 Wants Fund")
    st.markdown(f"**Balance:** {format_currency(player['wants_balance'])}")

# -------------------------------
# Decision Log
# -------------------------------
st.markdown("---")
st.subheader("🧾 Decision Log")

if player["decision_log"]:
    for i, d in enumerate(player["decision_log"], 1):
        st.write(f"**Round {i}:** {d}")
else:
    st.caption("No decisions logged yet.")
