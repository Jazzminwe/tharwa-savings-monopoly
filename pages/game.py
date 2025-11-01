# ============================
# pages/game.py (Main Game)
# ============================
import streamlit as st
import json
import random
import time

def format_currency(value):
    return f"SAR {value:,}"

def render_emoji_stat(value, emoji, max_value=10):
    full = emoji * int(value)
    empty = "▫️" * int(max_value - value)
    return f"{full}{empty} ({int(value)}/{max_value})"

if "player" not in st.session_state or "facilitator_settings" not in st.session_state:
    st.warning("No player data found. Please start from the setup page.")
    st.stop()

player = st.session_state.player
fs = st.session_state.facilitator_settings

st.set_page_config(layout="wide")
st.title("💰 Savings Monopoly")

if "life_cards" not in st.session_state:
    with open("data/life_cards.json", "r") as f:
        st.session_state.life_cards = json.load(f)

# ----- Emergency Fund Full Modal -----
if player.get("ef_full_alert", False):
    st.markdown("## 🚨 Emergency Fund Full")
    st.info(f"Your EF cap is {format_currency(player['ef_cap'])}. Current: {format_currency(player['ef_balance'])}.")
    st.write("Future EF contributions won't fit. Redirect EF to Savings?")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("✅ Redirect EF contribution to Savings Goal"):
            moved = player["allocation"]["ef"]
            player["allocation"]["savings"] += moved
            player["allocation"]["ef"] = 0
            player["ef_full_alert"] = False
            st.session_state.player = player
            st.experimental_rerun()
    with c2:
        if st.button("✖️ Keep EF as is"):
            player["ef_full_alert"] = False
            st.session_state.player = player
            st.experimental_rerun()
    st.stop()

# ----- Per-round auto-contributions -----
if player.get("awaiting_round_start", False):
    ef_add = player["allocation"]["ef"]
    projected = player["ef_balance"] + ef_add
    if ef_add > 0 and projected >= player["ef_cap"] and not player.get("ef_full_alert", False):
        player["ef_full_alert"] = True
        st.session_state.player = player
        st.experimental_rerun()
    room = max(0, player["ef_cap"] - player["ef_balance"])
    to_add = min(room, ef_add)
    player["ef_balance"] += to_add
    player["savings"] += player["allocation"]["savings"]
    player["awaiting_round_start"] = False
    st.session_state.player = player

# ----- Layout -----
left_col, right_col = st.columns([1.2, 1], gap="large")

with left_col:
    progress_fraction = player["rounds_played"] / max(1, fs["rounds"])
    st.progress(progress_fraction)
    st.caption(f"Rounds Played: {player['rounds_played']} / {fs['rounds']}")

    def allowed_types(round_idx):
        base = ["positive", "neutral", "negative_type_1"]
        if round_idx >= 4:
            base.append("negative_type_2")
        return base

    draw_disabled = player.get("current_card") is not None or player["rounds_played"] >= fs["rounds"]
    draw = st.button("🎴 Draw Life Card", type="primary", disabled=draw_disabled)

    if draw and not draw_disabled:
        permitted = allowed_types(player["rounds_played"] + 1)
        pool = [c for c in st.session_state.life_cards if c.get("type") in permitted]
        player["current_card"] = random.choice(pool)
        player["choice_made"] = False
        st.session_state.player = player

    if not player.get("current_card"):
        st.markdown("## 🎴 Draw a life card to start the month")
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
                selected = card["options"][options.index(choice)]
                player["emotion"] = max(0, min(10, player["emotion"] + selected.get("wellbeing", 0)))
                player["time"] = max(0, min(10, player["time"] - selected.get("time", 0)))
                delta_money = selected.get("money", 0)
                if card.get("ef_eligible", False) and delta_money < 0:
                    need = abs(delta_money)
                    cover = min(player["ef_balance"], need)
                    player["ef_balance"] -= cover
                    player["savings"] -= need - cover
                else:
                    player["savings"] += delta_money
                player["rounds_played"] += 1
                player["decision_log"].append(f"{card['title']} — {choice}")
                player["choice_made"] = True
                player["current_card"] = None
                player["awaiting_round_start"] = True
                st.session_state.player = player
                st.success("✅ Decision saved!")
                time.sleep(0.5)
                st.experimental_rerun()

with right_col:
    st.markdown("### 🧍 Player Stats")
    st.markdown(f"**{player['name']} ({player['team']})**")
    pct = player["savings"] / fs["goal"] if fs["goal"] > 0 else 0
    st.progress(pct)
    st.markdown(f"**Savings:** {format_currency(player['savings'])} ({int(pct*100)}%)")
    st.markdown(f"**Time:** {render_emoji_stat(player['time'], '⚡')}")
    st.markdown(f"**Wellbeing:** {render_emoji_stat(player['emotion'], '❤️')}")
    st.divider()
    remaining = player["income"] - player["fixed_costs"]
    st.markdown(f"**Monthly Income:** {format_currency(player['income'])}")
    st.markdown(f"**Fixed Costs:** {format_currency(player['fixed_costs'])}")
    st.markdown(f"**Remaining:** {format_currency(remaining)}")
    st.markdown("---")
    st.markdown("### 💰 Budget Allocation")
    wants = st.number_input("Wants", min_value=0, max_value=remaining, value=int(player['allocation']['wants']), step=50)
    ef = st.number_input("Emergency Fund", min_value=0, max_value=remaining, value=int(player['allocation']['ef']), step=50)
    savings = st.number_input("Savings Goal", min_value=0, max_value=remaining, value=int(player['allocation']['savings']), step=50)
    if st.button("💾 Save Budget"):
        if wants + ef + savings != remaining:
            st.warning(f"Allocations must equal remaining budget ({format_currency(remaining)}).")
        else:
            player['allocation'] = {'wants': wants, 'ef': ef, 'savings': savings}
            st.session_state.player = player
            st.success("Budget updated!")
    st.markdown("---")
    st.markdown("### 🛟 Emergency Fund")
    st.markdown(f"**Balance:** {format_currency(player['ef_balance'])}")
    st.markdown(f"**Cap:** {format_currency(player['ef_cap'])}")

st.markdown("---")
st.subheader("🧾 Decision Log")
for i, d in enumerate(player["decision_log"], 1):
    st.write(f"**Round {i}:** {d}")
