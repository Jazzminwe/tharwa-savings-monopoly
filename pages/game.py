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

# ---- Backfill / normalize player state (for older saves)
player.setdefault("rounds_played", 0)
player.setdefault("savings", 0)
player.setdefault("emotion", 5)
player.setdefault("time", 5)
player.setdefault("decision_log", [])
player.setdefault("current_card", None)
player.setdefault("choice_made", False)
player.setdefault("awaiting_round_start", False)

# budgets & funds
player.setdefault("income", fs.get("income", 0))
player.setdefault("fixed_costs", fs.get("fixed_costs", 0))
player.setdefault("ef_cap", player.get("ef_cap", 2000))
player.setdefault("ef_balance", player.get("ef_balance", 0))
player.setdefault("wants_balance", player.get("wants_balance", 0))

# allocations
player.setdefault("allocation", {})
alloc = player["allocation"]
remaining = max(0, player["income"] - player["fixed_costs"])
alloc.setdefault("wants", alloc.get("wants", 0))
alloc.setdefault("ef", alloc.get("ef", 0))
alloc.setdefault("savings", max(0, remaining - alloc["wants"] - alloc["ef"]))

# write back in case anything changed
st.session_state.player = player

st.set_page_config(layout="wide")

# -------------------------------
# Styling
# -------------------------------
st.markdown("""
<style>
div.block-container { padding-top: 2.2rem !important; }
.kpi-box {
    background-color: #ffffff;
    border-radius: 14px;
    box-shadow: 0 6px 16px rgba(0,0,0,0.12);
    padding: 16px 18px;
    height: 100%;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
}
.kpi-row > div[data-testid="stVerticalBlock"] {
    display: flex;
    flex-direction: column;
    justify-content: stretch;
}
.kpi-row { align-items: stretch; }
.stProgress > div > div {
    height: 6px !important;
    border-radius: 4px !important;
}
.title-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
}
.title-row h3 { margin: 0; }
.rounds-info {
    font-size: 0.9rem;
    color: #444;
    text-align: right;
}
.round-progress {
    width: 160px;
    height: 8px;
    border-radius: 4px;
}
</style>
""", unsafe_allow_html=True)

# -------------------------------
# Header
# -------------------------------
rounds_played = player["rounds_played"]
total_rounds = fs["rounds"]
progress = rounds_played / max(1, total_rounds)

st.markdown(f"""
<div class="title-row">
    <h3>💰 <b>Savings Monopoly</b></h3>
    <div class="rounds-info">
        Rounds: {rounds_played}/{total_rounds}<br>
        <progress class="round-progress" value="{progress}" max="1"></progress>
    </div>
</div>
""", unsafe_allow_html=True)

# -------------------------------
# Load life cards
# -------------------------------
if "life_cards" not in st.session_state:
    with open("data/life_cards.json", "r") as f:
        st.session_state.life_cards = json.load(f)

# -------------------------------
# KPI Row
# -------------------------------
remaining = player["income"] - player["fixed_costs"]

def update_allocations(new_wants=None, new_ef=None):
    if new_wants is not None:
        player["allocation"]["wants"] = new_wants
    if new_ef is not None:
        player["allocation"]["ef"] = new_ef
    total_alloc = player["allocation"]["wants"] + player["allocation"]["ef"]
    if total_alloc > remaining:
        st.warning("⚠️ Allocations exceed your remaining monthly budget.")
        return
    player["allocation"]["savings"] = remaining - total_alloc
    st.session_state.player = player
    st.toast("✅ Budget updated!")

st.markdown('<div class="kpi-row">', unsafe_allow_html=True)
col1, col2, col3, col4 = st.columns(4)

# --- Savings Goal
with col1:
    with st.container():
        st.markdown('<div class="kpi-box">', unsafe_allow_html=True)
        pct = player["savings"] / fs["goal"] if fs["goal"] > 0 else 0
        st.markdown("##### 💸 Savings Goal")
        st.caption(player["goal_desc"])
        st.progress(min(pct, 1.0))
        st.markdown(f"**{format_currency(player['savings'])} / {format_currency(fs['goal'])}** ({int(pct*100)}%)")
        st.markdown('</div>', unsafe_allow_html=True)

# --- Emergency Fund
with col2:
    with st.container():
        st.markdown('<div class="kpi-box">', unsafe_allow_html=True)
        st.markdown("##### 🛟 Emergency Fund")
        st.markdown(f"**Balance:** {format_currency(player['ef_balance'])}")
        st.number_input("EF Allocation", min_value=0, max_value=remaining,
                        value=int(player["allocation"]["ef"]), step=50,
                        key="ef_input", label_visibility="collapsed",
                        on_change=update_allocations, args=(None, int(player["allocation"]["ef"])))
        st.caption(f"Cap: {format_currency(player['ef_cap'])}")
        st.markdown('</div>', unsafe_allow_html=True)

# --- Wants Fund
with col3:
    with st.container():
        st.markdown('<div class="kpi-box">', unsafe_allow_html=True)
        st.markdown("##### 🎉 Wants Fund")
        st.markdown(f"**Balance:** {format_currency(player['wants_balance'])}")
        st.number_input("Wants Allocation", min_value=0, max_value=remaining,
                        value=int(player["allocation"]["wants"]), step=50,
                        key="wants_input", label_visibility="collapsed",
                        on_change=update_allocations, args=(int(player["allocation"]["wants"]), None))
        st.caption(f"Monthly add: {format_currency(player['allocation']['wants'])}")
        st.markdown('</div>', unsafe_allow_html=True)

# --- Wellbeing / Time
with col4:
    with st.container():
        st.markdown('<div class="kpi-box">', unsafe_allow_html=True)
        st.markdown("##### ❤️⚡ Wellbeing / Time")
        st.markdown(f"**Wellbeing:** {render_emoji_stat(player['emotion'], '❤️')}")
        st.markdown(f"**Time:** {render_emoji_stat(player['time'], '⚡')}")
        st.markdown('</div>', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

# -------------------------------
# Reflection Logic
# -------------------------------
if player["savings"] >= fs["goal"]:
    st.markdown("---")
    st.markdown("""
    ### 🎉 Congratulations — You’ve Reached Your Savings Goal!
    You’ve successfully balanced income, needs, and wellbeing for 12 months.  
    Before moving on to investing, take a moment to reflect:
    - What helped you reach your goal?
    - What tradeoffs were hardest?
    - How would you sustain this habit in real life?
    """)
    st.stop()

# -------------------------------
# Game Area
# -------------------------------
left_col, right_col = st.columns([2, 1], gap="large")

with left_col:
    st.markdown("### 🎴 Game Round")
    draw_disabled = player.get("current_card") is not None or player["rounds_played"] >= fs["rounds"]
    draw = st.button("🎴 Draw Life Card", type="primary", disabled=draw_disabled)

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
            st.error("No available life cards for this round.")
            st.stop()
        player["current_card"] = random.choice(pool)
        player["choice_made"] = False
        st.session_state.player = player

    if not player.get("current_card"):
        st.markdown("🃏 Draw a life card to start the month.")
    else:
        card = player["current_card"]
        st.subheader(card["title"])
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

                    if player["time"] <= 0 and delta_time > 0:
                        st.warning("⏳ Not enough energy for this choice.")
                        st.stop()

                    player["emotion"] = max(0, min(10, player["emotion"] + delta_wellbeing))
                    player["time"] = max(0, min(10, player["time"] - delta_time))
                    if player["emotion"] <= 0:
                        st.error("💥 Burnout! Your wellbeing reached 0 — game over for you.")
                        st.stop()

                    player["savings"] += delta_money
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

with right_col:
    st.markdown("### 💰 Budget Summary")
    st.markdown(f"**{player['name']}** <span style='color:#888;'>({player['team']})</span>", unsafe_allow_html=True)
    st.markdown(f"**Monthly Income:** {format_currency(player['income'])}")
    st.markdown(f"**Fixed Costs:** {format_currency(player['fixed_costs'])}")
    st.markdown(f"**Remaining:** {format_currency(player['income'] - player['fixed_costs'])}")
    st.markdown(f"**Savings Allocation (auto):** {format_currency(player['allocation']['savings'])}")

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
