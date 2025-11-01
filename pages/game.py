# pages/game.py
import streamlit as st
import json
import random
import time

# -------------------------------------------------
# Helper Functions
# -------------------------------------------------
def format_currency(value):
    try:
        return f"SAR {int(value):,}"
    except Exception:
        return f"SAR {value}"

def emoji_bar(value, emoji, max_value=10):
    v = int(max(0, min(max_value, value)))
    return emoji * v + "▫️" * (max_value - v) + f" ({v}/{max_value})"

# -------------------------------------------------
# Guard
# -------------------------------------------------
if "player" not in st.session_state or "facilitator_settings" not in st.session_state:
    st.warning("No player data found. Please start from the setup page.")
    st.stop()

player = st.session_state.player
fs = st.session_state.facilitator_settings
st.set_page_config(layout="wide")

# -------------------------------------------------
# Defaults
# -------------------------------------------------
player.setdefault("rounds_played", 0)
player.setdefault("savings", 0)
player.setdefault("emotion", 5)
player.setdefault("time", 5)
player.setdefault("decision_log", [])
player.setdefault("current_card", None)
player.setdefault("choice_made", False)
player.setdefault("income", fs.get("income", 2000))
player.setdefault("fixed_costs", fs.get("fixed_costs", 1000))
player.setdefault("ef_cap", 3000)
player.setdefault("ef_balance", 0)
player.setdefault("wants_balance", 0)
player.setdefault("allocation", {
    "savings": 500,
    "ef": 250,
    "wants": 250,
})

# -------------------------------------------------
# CSS
# -------------------------------------------------
st.markdown("""
<style>
div.block-container {
  max-width: 1280px;
  padding-top: 4rem !important;
  padding-bottom: 1rem !important;
  margin: 0 auto;
  overflow: visible !important;
  background: transparent !important;
}

/* Header */
.header-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  margin-bottom: 0.8rem;
}
.header-title {
  font-size: 1.8rem !important;
  font-weight: 800;
  line-height: 1.1;
}
.rounds {
  text-align: right;
  font-size: 0.9rem;
}
.rounds progress {
  width: 140px;
  height: 5px;
  border-radius: 3px;
  accent-color: #1f6feb;
  margin-top: 4px;
}

/* 3D box styling */
div[data-testid="stVerticalBlock"]:has(> .marker) {
  background: #fff !important;
  border-radius: 16px;
  box-shadow: 0 3px 12px rgba(0,0,0,0.08);
  padding: 18px 22px !important;
  margin-bottom: 0.5rem !important;
}

/* Headings */
h3, h4, h5, h6 {
  font-size: 1rem !important;
  font-weight: 700 !important;
  margin-bottom: 0.4rem !important;
}

/* Inputs */
div[data-testid="stNumberInput"] > div {
  width: 100% !important;
}
div[data-testid="stNumberInput"] input {
  width: 100% !important;
  font-size: 0.95rem;
}

/* Progress bars */
.stProgress > div > div {
  height: 6px !important;
  border-radius: 3px !important;
}

/* Columns */
div[data-testid="column"] {
  padding-left: 0.6rem !important;
  padding-right: 0.6rem !important;
}

/* Divider cleanup */
hr, .stDivider { display: none !important; }
</style>
""", unsafe_allow_html=True)

# -------------------------------------------------
# Header
# -------------------------------------------------
rp = player["rounds_played"]
tr = fs.get("rounds", 10)
pct_rounds = min(1.0, max(0.0, float(rp) / max(1, float(tr))))

st.markdown(f"""
<div class="header-row">
  <div class="header-title">💰 Savings Monopoly</div>
  <div class="rounds"><b>Rounds:</b> {rp}/{tr}<br><progress value="{pct_rounds}" max="1"></progress></div>
</div>
""", unsafe_allow_html=True)

# -------------------------------------------------
# KPI ROW (in proper 3D boxes)
# -------------------------------------------------
remaining = player["income"] - player["fixed_costs"]
k1, k2, k3, k4 = st.columns(4, gap="small")

with k1:
    st.markdown('<span class="marker"></span>', unsafe_allow_html=True)
    st.markdown("#### 💰 Budget Overview")
    st.markdown(f"**Monthly Income:** {format_currency(player['income'])}")
    st.markdown(f"**Fixed Costs:** {format_currency(player['fixed_costs'])}")
    st.markdown(f"**Remaining:** {format_currency(remaining)}")

with k2:
    st.markdown('<span class="marker"></span>', unsafe_allow_html=True)
    st.markdown("#### 🎯 Savings Goal")
    goal_value = fs.get("goal", 5000)
    savings_value = player.get("savings", 0)
    pct = (savings_value / goal_value) if goal_value else 0.0
    st.progress(min(1.0, pct))
    st.markdown(f"**{format_currency(savings_value)} / {format_currency(goal_value)}** ({int(pct * 100)}%)")
    player["allocation"]["savings"] = st.number_input("Monthly allocation:", 0, remaining, player["allocation"]["savings"], 50)

with k3:
    st.markdown('<span class="marker"></span>', unsafe_allow_html=True)
    st.markdown("#### 🛟 Emergency Fund")
    st.markdown(f"**Balance:** {format_currency(player['ef_balance'])}")
    st.caption(f"Cap: {format_currency(player['ef_cap'])}")
    player["allocation"]["ef"] = st.number_input("Monthly allocation:", 0, remaining, player["allocation"]["ef"], 50)

with k4:
    st.markdown('<span class="marker"></span>', unsafe_allow_html=True)
    st.markdown("#### 🎉 Wants Fund")
    st.markdown(f"**Balance:** {format_currency(player['wants_balance'])}")
    st.caption("Cap: None")
    player["allocation"]["wants"] = st.number_input("Monthly allocation:", 0, remaining, player["allocation"]["wants"], 50)

st.session_state.player = player

# -------------------------------------------------
# Logic helpers
# -------------------------------------------------
def apply_monthly_allocations(p):
    p["ef_balance"] = min(p["ef_cap"], p["ef_balance"] + p["allocation"]["ef"])
    p["wants_balance"] += p["allocation"]["wants"]
    p["savings"] += p["allocation"]["savings"]

def end_game(msg):
    st.error(msg)
    if st.button("🔄 Restart Game"):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()
    st.stop()

# -------------------------------------------------
# Game + Wellbeing Row
# -------------------------------------------------
left, right = st.columns([2, 1], gap="large")

with left:
    st.markdown("### 🎴 Game Round")

    # Early endings
    if player["emotion"] <= 0:
        end_game("💥 You’ve burned out! Take care of your wellbeing first — balance is key.")
    if player["savings"] >= fs.get("goal", 5000):
        end_game("🎉 Congratulations! You reached your savings goal! Great discipline and planning.")
    if player["time"] <= 0:
        player["emotion"] = max(0, player["emotion"] - 2)
        player["time"] = 3
        st.warning("⏳ You ran out of time! You feel drained (-2 wellbeing, time reset to 3).")

    draw_disabled = player.get("current_card") or player["rounds_played"] >= tr
    draw = st.button("🎴 Draw Life Card", type="primary", disabled=draw_disabled)

    if "life_cards" not in st.session_state:
        with open("data/life_cards.json", "r") as f:
            st.session_state.life_cards = json.load(f)

    if draw:
        apply_monthly_allocations(player)
        player["current_card"] = random.choice(st.session_state.life_cards)
        player["choice_made"] = False
        st.session_state.player = player

    if not player.get("current_card"):
        st.caption("Draw a life card to start the month.")
    else:
        card = player["current_card"]
        st.subheader(card.get("title", "Life Event"))
        if card.get("description"):
            st.write(card["description"])

        options = [
            f"{opt['label']} → Money: {opt.get('money',0)}, Wellbeing: {opt.get('wellbeing',0)}, Time: {opt.get('time',0)}"
            for opt in card.get("options", [])
        ]
        choice = st.radio("Choose an option:", options, key="decision_choice")

        sum_alloc = sum(player["allocation"].values())
        if sum_alloc != remaining:
            st.warning(f"Your monthly allocations ({format_currency(sum_alloc)}) must equal remaining ({format_currency(remaining)}).")

        if st.button("💾 Save Decision", key="save_decision"):
            if sum_alloc != remaining:
                st.error("Allocations do not match remaining budget.")
                st.stop()

            selected = card["options"][options.index(choice)]
            money = selected.get("money", 0)
            wellbeing = selected.get("wellbeing", 0)
            time_cost = selected.get("time", 0)

            # Money handling
            if money < 0:
                need = abs(money)
                from_wants = min(need, player["wants_balance"])
                player["wants_balance"] -= from_wants
                need -= from_wants
                if need > player["savings"]:
                    st.error("💸 Not enough funds.")
                    st.stop()
                player["savings"] -= need
            else:
                player["savings"] += money

            # Wellbeing/time handling
            player["emotion"] = max(0, min(10, player["emotion"] + wellbeing))
            if player["time"] - time_cost < 0:
                st.error("⏳ Not enough time to do this.")
                st.stop()
            player["time"] -= time_cost

            # Record round
            player["rounds_played"] += 1
            player["decision_log"].append(f"{card['title']} — {choice}")
            player["choice_made"] = True
            player["current_card"] = None
            st.session_state.player = player

            st.success("✅ Decision saved!")
            time.sleep(0.4)
            st.rerun()

with right:
    st.markdown('<span class="marker"></span>', unsafe_allow_html=True)
    st.markdown("#### 📈 Game Progress")
    st.markdown(f"**Rounds:** {rp}/{tr}")
    st.progress(pct_rounds)

    st.markdown('<span class="marker"></span>', unsafe_allow_html=True)
    st.markdown("#### ❤️⚡ Wellbeing / Time Overview")
    st.markdown(f"**Wellbeing:** {emoji_bar(player['emotion'], '❤️')}")
    st.markdown(f"**Time:** {emoji_bar(player['time'], '⚡')}")

# -------------------------------------------------
# Decision Log
# -------------------------------------------------
st.markdown("""<hr style="border:none;border-top:1px solid #eee;margin:.8rem 0 .4rem">""", unsafe_allow_html=True)
st.subheader("🧾 Decision Log")
if player["decision_log"]:
    for i, d in enumerate(player["decision_log"], 1):
        st.write(f"**Round {i}:** {d}")
else:
    st.caption("No decisions yet.")
