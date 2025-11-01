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

# -------------------------------
# Page Styling
# -------------------------------
st.markdown(
    """
    <style>
    div.block-container {
        padding-top: 2.4rem !important;
    }
    h3, h4, h5 {
        margin-bottom: 0.3rem !important;
    }
    .small-label {
        color:#777;
        font-size:0.85rem;
    }

    /* KPI container styling */
    .kpi-anchor + div[data-testid="stContainer"]{
      background:#f9f9f9 !important;
      border:0 !important;
      border-radius:14px !important;
      box-shadow:0 4px 12px rgba(0,0,0,0.12) !important;
      padding:16px 18px !important;
      min-height:220px !important;
      display:flex;
      flex-direction:column;
      justify-content:space-between;
    }

    /* Progress bar */
    .kpi-anchor + div[data-testid="stContainer"] .stProgress > div > div{
      height:6px !important;
      border-radius:4px !important;
    }

    /* Title and round counter layout */
    .title-row {
      display:flex;
      align-items:center;
      justify-content:space-between;
      width:100%;
    }
    .title-row h3 {
      margin:0;
      display:flex;
      align-items:center;
      gap:8px;
    }
    .rounds-info {
      font-size:0.9rem;
      color:#444;
      text-align:right;
    }
    .round-progress {
      width:160px;
      height:8px;
      border-radius:4px;
      display:block;
    }

    input[type=number]{
        border:1px solid #ddd;
        border-radius:6px;
        padding:4px 8px;
        font-size:0.9rem;
        width:100%;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# -------------------------------
# Load life cards
# -------------------------------
if "life_cards" not in st.session_state:
    with open("data/life_cards.json", "r") as f:
        st.session_state.life_cards = json.load(f)

# -------------------------------
# HEADER (Row 1)
# -------------------------------
rounds_played = player["rounds_played"]
total_rounds = fs["rounds"]
progress = rounds_played / max(1, total_rounds)

st.markdown(
    f"""
    <div class="title-row">
        <h3>💰 <b>Savings Monopoly</b></h3>
        <div class="rounds-info">
            <div>Rounds: {rounds_played}/{total_rounds}</div>
            <progress class="round-progress" value="{progress}" max="1"></progress>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# -------------------------------
# Auto Contributions per round
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
# Row 2 – KPI Dashboard
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

kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)

# --- Savings Goal
with kpi_col1:
    st.markdown('<div class="kpi-anchor"></div>', unsafe_allow_html=True)
    with st.container(border=True):
        pct = player["savings"] / fs["goal"] if fs["goal"] > 0 else 0
        st.markdown("#### 💸 Savings Goal")
        st.caption(player["goal_desc"])
        st.progress(pct)
        st.markdown(f"**{format_currency(player['savings'])} / {format_currency(fs['goal'])}** ({int(pct*100)}%)")

# --- Emergency Fund
with kpi_col2:
    st.markdown('<div class="kpi-anchor"></div>', unsafe_allow_html=True)
    with st.container(border=True):
        st.markdown("#### 🛟 Emergency Fund")
        st.markdown(f"**Balance:** {format_currency(player['ef_balance'])}")
        new_ef = st.number_input(
            "EF Allocation", min_value=0, max_value=remaining, value=int(player["allocation"]["ef"]),
            step=50, key="ef_input", label_visibility="collapsed",
            on_change=update_allocations, args=(None, int(player["allocation"]["ef"]))
        )
        st.caption(f"Cap: {format_currency(player['ef_cap'])}")

# --- Wants Fund
with kpi_col3:
    st.markdown('<div class="kpi-anchor"></div>', unsafe_allow_html=True)
    with st.container(border=True):
        st.markdown("#### 🎉 Wants Fund")
        st.markdown(f"**Balance:** {format_currency(player['wants_balance'])}")
        new_wants = st.number_input(
            "Wants Allocation", min_value=0, max_value=remaining, value=int(player["allocation"]["wants"]),
            step=50, key="wants_input", label_visibility="collapsed",
            on_change=update_allocations, args=(int(player["allocation"]["wants"]), None)
        )
        st.caption(f"Monthly add: {format_currency(player['allocation']['wants'])}")

# --- Wellbeing / Time
with kpi_col4:
    st.markdown('<div class="kpi-anchor"></div>', unsafe_allow_html=True)
    with st.container(border=True):
        st.markdown("#### ❤️⚡ Wellbeing / Time")
        st.markdown(f"**Wellbeing:** {render_emoji_stat(player['emotion'], '❤️')}")
        st.markdown(f"**Time:** {render_emoji_stat(player['time'], '⚡')}")

# -------------------------------
# Row 3 – Game Area
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
    st.markdown(f"👤 **{player['name']}** — *{player['team']}*")
    st.markdown("### 💰 Budget Summary")
    st.markdown(f"**Monthly Income:** {format_currency(player['income'])}")
    st.markdown(f"**Fixed Costs:** {format_currency(player['fixed_costs'])}")
    st.markdown(f"**Remaining:** {format_currency(remaining)}")
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
