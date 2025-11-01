# pages/game.py
import streamlit as st
import json
import random
import time

# -------------------------------------------------
# Helper Functions
# -------------------------------------------------
def fmt(value):
    try:
        return f"SAR {int(value):,}"
    except Exception:
        return f"SAR {value}"

def emoji_bar(value, emoji, max_value=10):
    v = int(max(0, min(max_value, value)))
    return emoji * v + "▫️" * (max_value - v) + f" ({v}/{max_value})"

# -------------------------------------------------
# Guards
# -------------------------------------------------
if "player" not in st.session_state or "facilitator_settings" not in st.session_state:
    st.warning("No player data found. Please start from the setup page.")
    st.stop()

p = st.session_state.player
fs = st.session_state.facilitator_settings
st.set_page_config(layout="wide")

# -------------------------------------------------
# Defaults
# -------------------------------------------------
p.setdefault("rounds_played", 0)
p.setdefault("savings", 0)
p.setdefault("emotion", 5)
p.setdefault("time", 5)
p.setdefault("decision_log", [])
p.setdefault("current_card", None)
p.setdefault("choice_made", False)
p.setdefault("income", fs.get("income", 2000))
p.setdefault("fixed_costs", fs.get("fixed_costs", 1000))
p.setdefault("ef_cap", 3000)
p.setdefault("ef_balance", 0)
p.setdefault("wants_balance", 0)
p.setdefault("allocation", {"savings": 334, "ef": 333, "wants": 333})

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

/* KPI boxes */
.kpi-card {
  background: #fff !important;
  border-radius: 16px;
  box-shadow: 0 3px 12px rgba(0,0,0,0.08);
  padding: 18px 22px !important;
  margin-bottom: 0.5rem !important;
}

/* Typography */
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
rp = p["rounds_played"]
tr = fs.get("rounds", 10)
pct_rounds = min(1.0, max(0.0, float(rp) / max(1, float(tr))))

st.markdown(f"""
<div class="header-row">
  <div class="header-title">💰 Savings Monopoly</div>
  <div class="rounds"><b>Rounds:</b> {rp}/{tr}<br><progress value="{pct_rounds}" max="1"></progress></div>
</div>
""", unsafe_allow_html=True)

# -------------------------------------------------
# KPI Row (with boxes)
# -------------------------------------------------
remaining = int(p["income"] - p["fixed_costs"])
k1, k2, k3, k4 = st.columns(4, gap="small")

with k1:
    with st.container():
        st.markdown('<div class="kpi-card">', unsafe_allow_html=True)
        st.markdown("#### 💰 Budget Overview")
        st.markdown(f"**Monthly Income:** {fmt(p['income'])}")
        st.markdown(f"**Fixed Costs:** {fmt(p['fixed_costs'])}")
        st.markdown(f"**Remaining:** {fmt(remaining)}")
        st.markdown('</div>', unsafe_allow_html=True)

with k2:
    with st.container():
        st.markdown('<div class="kpi-card">', unsafe_allow_html=True)
        st.markdown("#### 🎯 Savings Goal")
        goal_value = fs.get("goal", 5000)
        savings_value = p.get("savings", 0)
        pct = (savings_value / goal_value) if goal_value else 0.0
        st.progress(min(1.0, pct))
        st.markdown(f"**{fmt(savings_value)} / {fmt(goal_value)}** ({int(pct * 100)}%)")
        p["allocation"]["savings"] = st.number_input(
            "Monthly allocation:",
            min_value=0,
            max_value=remaining,
            value=int(p["allocation"]["savings"]),
            step=50,
            key="alloc_savings"
        )
        st.markdown('</div>', unsafe_allow_html=True)

with k3:
    with st.container():
        st.markdown('<div class="kpi-card">', unsafe_allow_html=True)
        st.markdown("#### 🛟 Emergency Fund")
        st.markdown(f"**Balance:** {fmt(p['ef_balance'])}")
        st.caption(f"Cap: {fmt(p['ef_cap'])}")
        p["allocation"]["ef"] = st.number_input(
            "Monthly allocation:",
            min_value=0,
            max_value=remaining,
            value=int(p["allocation"]["ef"]),
            step=50,
            key="alloc_ef"
        )
        st.markdown('</div>', unsafe_allow_html=True)

with k4:
    with st.container():
        st.markdown('<div class="kpi-card">', unsafe_allow_html=True)
        st.markdown("#### 🎉 Wants Fund")
        st.markdown(f"**Balance:** {fmt(p['wants_balance'])}")
        st.caption("Cap: None")
        p["allocation"]["wants"] = st.number_input(
            "Monthly allocation:",
            min_value=0,
            max_value=remaining,
            value=int(p["allocation"]["wants"]),
            step=50,
            key="alloc_wants"
        )
        st.markdown('</div>', unsafe_allow_html=True)

st.session_state.player = p

# -------------------------------------------------
# Logic Helpers
# -------------------------------------------------
def apply_monthly(p):
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

    # Early-ending conditions
    if p["emotion"] <= 0:
        end_game("💥 You’ve burned out! Take care of your wellbeing — balance is key.")
    if p["savings"] >= fs.get("goal", 5000):
        end_game("🎉 Congratulations! You reached your savings goal! Great planning and patience.")
    if p["time"] <= 0:
        p["emotion"] = max(0, p["emotion"] - 2)
        p["time"] = 3
        st.warning("⏳ You ran out of time! You feel drained (-2 wellbeing, time reset to 3).")

    draw_disabled = bool(p.get("current_card") or p["rounds_played"] >= tr)
    draw = st.button("🎴 Draw Life Card", type="primary", disabled=draw_disabled)

    if "life_cards" not in st.session_state:
        with open("data/life_cards.json", "r") as f:
            st.session_state.life_cards = json.load(f)

    if draw:
        apply_monthly(p)
        p["current_card"] = random.choice(st.session_state.life_cards)
        p["choice_made"] = False
        st.session_state.player = p

    if not p.get("current_card"):
        st.caption("Draw a life card to start the month.")
    else:
        card = p["current_card"]
        st.subheader(card.get("title", "Life Event"))
        if card.get("description"):
            st.write(card["description"])

        options = [
            f"{opt['label']} → Money: {opt.get('money',0)}, Wellbeing: {opt.get('wellbeing',0)}, Time: {opt.get('time',0)}"
            for opt in card.get("options", [])
        ]
        choice = st.radio("Choose an option:", options, key="decision_choice")

        sum_alloc = sum(p["allocation"].values())
        if sum_alloc != remaining:
            st.warning(f"Your monthly allocations ({fmt(sum_alloc)}) must equal remaining ({fmt(remaining)}).")

        if st.button("💾 Save Decision", key="save_decision"):
            if sum_alloc != remaining:
                st.error("Allocations do not match remaining budget.")
                st.stop()

            selected = card["options"][options.index(choice)]
            money = selected.get("money", 0)
            wellbeing = selected.get("wellbeing", 0)
            time_cost = selected.get("time", 0)

            # Apply financial effects
            if money < 0:
                need = abs(money)
                from_wants = min(need, p["wants_balance"])
                p["wants_balance"] -= from_wants
                need -= from_wants
                if need > p["savings"]:
                    st.error("💸 Not enough funds.")
                    st.stop()
                p["savings"] -= need
            else:
                p["savings"] += money

            # Wellbeing/time effects
            p["emotion"] = max(0, min(10, p["emotion"] + wellbeing))
            if p["time"] - time_cost < 0:
                st.error("⏳ Not enough time.")
                st.stop()
            p["time"] -= time_cost

            # Record progress
            p["rounds_played"] += 1
            p["decision_log"].append(f"{card['title']} — {choice}")
            p["choice_made"] = True
            p["current_card"] = None
            st.session_state.player = p

            st.success("✅ Decision saved!")
            time.sleep(0.4)
            st.rerun()

with right:
    with st.container():
        st.markdown('<div class="kpi-card">', unsafe_allow_html=True)
        st.markdown("#### 📈 Game Progress")
        st.markdown(f"**Rounds:** {rp}/{tr}")
        st.progress(pct_rounds)
        st.markdown('</div>', unsafe_allow_html=True)

    with st.container():
        st.markdown('<div class="kpi-card">', unsafe_allow_html=True)
        st.markdown("#### ❤️⚡ Wellbeing / Time Overview")
        st.markdown(f"**Wellbeing:** {emoji_bar(p['emotion'], '❤️')}")
        st.markdown(f"**Time:** {emoji_bar(p['time'], '⚡')}")
        st.markdown('</div>', unsafe_allow_html=True)

# -------------------------------------------------
# Decision Log
# -------------------------------------------------
st.markdown("""<hr style="border:none;border-top:1px solid #eee;margin:.8rem 0 .4rem">""", unsafe_allow_html=True)
st.subheader("🧾 Decision Log")
if p["decision_log"]:
    for i, d in enumerate(p["decision_log"], 1):
        st.write(f"**Round {i}:** {d}")
else:
    st.caption("No decisions yet.")
