import streamlit as st
import json
import random
import time

# -------------------------------
# Helper functions
# -------------------------------
def format_currency(value):
    try:
        return f"SAR {int(value):,}"
    except Exception:
        return f"SAR {value}"

def render_emoji_stat(value, emoji, max_value=10):
    v = int(max(0, min(max_value, value)))
    full = emoji * v
    empty = "▫️" * (max_value - v)
    return f"{full}{empty} ({v}/{max_value})"


# -------------------------------
# Check for required session data
# -------------------------------
if "player" not in st.session_state or "facilitator_settings" not in st.session_state:
    st.warning("No player data found. Please start from the setup page.")
    st.stop()

player = st.session_state.player
fs = st.session_state.facilitator_settings

# ---- Safe backfill for all player keys ----
player.setdefault("rounds_played", 0)
player.setdefault("savings", 0)
player.setdefault("emotion", 5)
player.setdefault("time", 5)
player.setdefault("decision_log", [])
player.setdefault("current_card", None)
player.setdefault("choice_made", False)
player.setdefault("awaiting_round_start", False)
player.setdefault("income", fs.get("income", 0))
player.setdefault("fixed_costs", fs.get("fixed_costs", 0))
player.setdefault("ef_cap", player.get("ef_cap", 2000))
player.setdefault("ef_balance", player.get("ef_balance", 0))
player.setdefault("wants_balance", player.get("wants_balance", 0))
player.setdefault("name", player.get("name", ""))
player.setdefault("team", player.get("team", ""))

player.setdefault("allocation", {})
alloc = player["allocation"]
remaining = max(0, player["income"] - player["fixed_costs"])
alloc.setdefault("wants", alloc.get("wants", 0))
alloc.setdefault("ef", alloc.get("ef", 0))
alloc.setdefault("savings", max(0, remaining - alloc["wants"] - alloc["ef"]))
st.session_state.player = player

st.set_page_config(layout="wide")

# -------------------------------
# Custom Styling
# -------------------------------
st.markdown("""
<style>
div.block-container { padding-top: 1rem !important; }

/* KPI cards: clean white, equal height */
div[data-testid="stVerticalBlock"]:has(.kpi-marker) {
    background: #ffffff;
    border-radius: 14px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.10);
    padding: 12px 16px;
    height: 100%;
}

/* Smaller heading size inside cards */
div[data-testid="stVerticalBlock"]:has(.kpi-marker) h4,
div[data-testid="stVerticalBlock"]:has(.kpi-marker) h5 {
    font-size: 1rem !important;
    margin-bottom: 4px !important;
    font-weight: 600;
}

/* Tight number inputs */
div[data-testid="stNumberInputContainer"] > div { margin-top: 0 !important; }

/* Reduce gaps between columns */
div[data-testid="column"] { padding-left: 0.4rem !important; padding-right: 0.4rem !important; }

.stProgress > div > div { height: 6px !important; border-radius: 4px !important; }
</style>
""", unsafe_allow_html=True)

# -------------------------------
# Header
# -------------------------------
left_h, right_h = st.columns([4, 1])
with left_h:
    st.markdown("## 💰 Savings Monopoly")
with right_h:
    rp = player["rounds_played"]
    tr = fs["rounds"]
    st.write(f"**Rounds:** {rp}/{tr}")
    st.progress(rp / max(1, tr))

# -------------------------------
# KPI Row
# -------------------------------
remaining = player["income"] - player["fixed_costs"]

def update_allocations(new_wants=None, new_ef=None):
    if new_wants is not None:
        player["allocation"]["wants"] = int(new_wants)
    if new_ef is not None:
        player["allocation"]["ef"] = int(new_ef)
    total_alloc = player["allocation"]["wants"] + player["allocation"]["ef"]
    if total_alloc > remaining:
        st.warning("⚠️ Allocations exceed remaining budget.")
        return
    player["allocation"]["savings"] = max(0, remaining - total_alloc)
    st.session_state.player = player
    st.toast("✅ Budget updated!")

k1, k2, k3, k4 = st.columns(4, gap="small")

# --- Savings Goal
with k1:
    st.markdown('<span class="kpi-marker"></span>', unsafe_allow_html=True)
    st.markdown("#### 💸 Savings Goal")
    st.caption(player.get("goal_desc", ""))
    pct = player["savings"] / fs["goal"] if fs["goal"] else 0
    st.progress(min(1.0, pct))
    st.markdown(f"**{format_currency(player['savings'])} / {format_currency(fs['goal'])}** ({int(pct*100)}%)")

# --- Emergency Fund
with k2:
    st.markdown('<span class="kpi-marker"></span>', unsafe_allow_html=True)
    st.markdown("#### 🛟 Emergency Fund")
    st.markdown(f"**Balance:** {format_currency(player['ef_balance'])}")
    new_ef = st.number_input(
        "EF Allocation",
        min_value=0, max_value=remaining, value=int(player['allocation']['ef']),
        step=50, label_visibility="collapsed", key="ef_allocation"
    )
    if new_ef != player["allocation"]["ef"]:
        update_allocations(new_ef=new_ef)
    st.caption(f"Cap: {format_currency(player['ef_cap'])}")

# --- Wants Fund
with k3:
    st.markdown('<span class="kpi-marker"></span>', unsafe_allow_html=True)
    st.markdown("#### 🎉 Wants Fund")
    st.markdown(f"**Balance:** {format_currency(player['wants_balance'])}")
    new_wants = st.number_input(
        "Wants Allocation",
        min_value=0, max_value=remaining, value=int(player['allocation']['wants']),
        step=50, label_visibility="collapsed", key="wants_allocation"
    )
    if new_wants != player["allocation"]["wants"]:
        update_allocations(new_wants=new_wants)
    st.caption(f"Monthly add: {format_currency(player['allocation']['wants'])}")

# --- Wellbeing / Time
with k4:
    st.markdown('<span class="kpi-marker"></span>', unsafe_allow_html=True)
    st.markdown("#### ❤️⚡ Wellbeing / Time")
    st.markdown(f"**Wellbeing:** {render_emoji_stat(player['emotion'], '❤️')}")
    st.markdown(f"**Time:** {render_emoji_stat(player['time'], '⚡')}")

# -------------------------------
# Reflection logic — when goal reached
# -------------------------------
if player["savings"] >= fs["goal"]:
    st.markdown("---")
    st.markdown("""
    ### 🎉 Congratulations — You’ve Reached Your Savings Goal!
    You’ve balanced income, needs, and wellbeing over the year.  
    Before moving to investing later in the workshop, reflect briefly:
    - What helped you reach your goal?
    - What tradeoffs were hardest?
    - What would you keep doing next month?
    """)
    st.stop()

# -------------------------------
# Game + Simplified Budget Overview
# -------------------------------
left_col, right_col = st.columns([2, 1], gap="large")

# --- Game section
with left_col:
    st.markdown("### 🎴 Game Round")
    draw_disabled = player.get("current_card") is not None or player["rounds_played"] >= fs["rounds"]
    draw = st.button("🎴 Draw Life Card", type="primary", disabled=draw_disabled)

    if "life_cards" not in st.session_state:
        with open("data/life_cards.json", "r") as f:
            st.session_state.life_cards = json.load(f)

    def allowed_types(round_idx, p):
        base = ["positive", "neutral", "negative_type_1"]
        if round_idx >= 4:
            base.append("negative_type_2")
        if p["savings"] >= fs["goal"] * 0.6:
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
            options.append(
                f"{label} → Money: {money}, Wellbeing: {wellbeing}, Time: {time_cost}"
            )

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
                        st.error("💥 Burnout! Your wellbeing reached 0 — game over.")
                        st.stop()

                    player["savings"] += delta_money
                    player["rounds_played"] += 1
                    player["decision_log"].append(f"{card['title']} — {choice}")
                    player["choice_made"] = True
                    player["current_card"] = None

                    st.session_state.player = player
                    st.success("✅ Decision saved!")
                    time.sleep(0.5)
                    st.rerun()

# --- Simplified Budget Overview
with right_col:
    st.markdown("### 💰 Budget Overview")
    st.markdown(f"**{player.get('name','')}** <span style='color:#888;'>({player.get('team','')})</span>", unsafe_allow_html=True)
    st.markdown(f"**Monthly Income:** {format_currency(player['income'])}")
    st.markdown(f"**Fixed Costs:** {format_currency(player['fixed_costs'])}")
    st.markdown(f"**Remaining:** {format_currency(remaining)}")

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
