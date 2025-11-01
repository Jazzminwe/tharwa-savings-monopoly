# pages/game.py
import streamlit as st
import json
import random
import time

# -------------------------------------------------
# Helper functions
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
p.setdefault("allocation", {"savings": 0, "ef": 0, "wants": 0})

# -------------------------------------------------
# CSS (respect hierarchy)
# -------------------------------------------------
st.markdown("""
<style>
div.block-container {
  max-width: 1280px;
  padding-top: 2rem;
}
.header-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  margin-bottom: 1rem;
}
.header-title {
  font-size: 1.2rem; /* small and understated header */
  font-weight: 800;
  line-height: 1.1;
}
.rounds {
  text-align: right;
  font-size: 0.85rem;
}
.rounds progress {
  width: 140px;
  height: 6px;
  border-radius: 3px;
  accent-color: #1f6feb;
  margin-top: 4px;
}
h3, h4 {
  font-size: 1rem !important;
  font-weight: 700 !important;
  margin-bottom: 0.4rem !important;
}
</style>
""", unsafe_allow_html=True)

# -------------------------------------------------
# Header
# -------------------------------------------------
rp = p["rounds_played"]
tr = fs.get("rounds", 10)
pct_rounds = min(1.0, float(rp) / max(1, float(tr)))

st.markdown(f"""
<div class="header-row">
  <div class="header-title">💰 Savings Monopoly</div>
  <div class="rounds">
    <b>Rounds:</b> {rp}/{tr}<br>
    <progress value="{pct_rounds}" max="1"></progress>
  </div>
</div>
""", unsafe_allow_html=True)

# -------------------------------------------------
# Budget Overview + Allocations
# -------------------------------------------------
remaining = int(p["income"] - p["fixed_costs"])
k1, k2, k3, k4 = st.columns(4, gap="small")

with k1:
    st.markdown("#### 💰 Budget Overview")
    st.markdown(f"**Monthly Income:** {fmt(p['income'])}")
    st.markdown(f"**Fixed Costs:** {fmt(p['fixed_costs'])}")
    st.markdown(f"**Remaining:** {fmt(remaining)}")

with k2:
    st.markdown("#### 🎯 Savings Goal")
    goal = fs.get("goal", 5000)
    pct = p["savings"] / goal if goal else 0
    st.progress(min(1.0, pct))
    st.markdown(f"**{fmt(p['savings'])} / {fmt(goal)}** ({int(pct*100)}%)")
    p["allocation"]["savings"] = st.number_input(
        "Monthly allocation (Savings):", 0, remaining, int(p["allocation"]["savings"]), 50, key="alloc_sav"
    )

with k3:
    st.markdown("#### 🛟 Emergency Fund")
    st.markdown(f"**Balance:** {fmt(p['ef_balance'])}")
    st.caption(f"Cap: {fmt(p['ef_cap'])}")
    p["allocation"]["ef"] = st.number_input(
        "Monthly allocation (EF):", 0, remaining, int(p["allocation"]["ef"]), 50, key="alloc_ef"
    )

with k4:
    st.markdown("#### 🎉 Wants Fund")
    st.markdown(f"**Balance:** {fmt(p['wants_balance'])}")
    st.caption("Cap: None")
    p["allocation"]["wants"] = st.number_input(
        "Monthly allocation (Wants):", 0, remaining, int(p["allocation"]["wants"]), 50, key="alloc_w"
    )

# -------------------------------------------------
# Logic Helpers
# -------------------------------------------------
def apply_monthly_income(p):
    """Distribute income across funds at start of round."""
    p["ef_balance"] = min(p["ef_cap"], p["ef_balance"] + p["allocation"]["ef"])
    p["wants_balance"] += p["allocation"]["wants"]
    p["savings"] += p["allocation"]["savings"]

def apply_card_effects(p, selected):
    """Apply life card effects to funds, time, and wellbeing."""
    money = selected.get("money", 0)
    wellbeing = selected.get("wellbeing", 0)
    time_cost = selected.get("time", 0)

    if money < 0:
        need = abs(money)
        for fund in ["wants_balance", "savings", "ef_balance"]:
            take = min(need, p[fund])
            p[fund] -= take
            need -= take
            if need <= 0:
                break
        if need > 0:
            st.warning("💸 Some expenses couldn’t be covered!")
    else:
        p["savings"] += money

    p["emotion"] = max(0, min(10, p["emotion"] + wellbeing))
    if p["time"] - time_cost < 0:
        st.error("⏳ Not enough time to take this action.")
        st.stop()
    p["time"] -= time_cost

def end_popup(msg, success=False):
    """Popup shown at the end of game."""
    if success:
        st.success(msg)
    else:
        st.error(msg)
    if st.button("🔄 Restart Game"):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()
    st.stop()

# -------------------------------------------------
# Game Section
# -------------------------------------------------
left, right = st.columns([2, 1])

with left:
    st.markdown("### 🎴 Game Round")

    # Early termination checks
    if p["emotion"] <= 0:
        end_popup("💥 You burned out! Game over.", success=False)
    if p["savings"] >= fs.get("goal", 5000):
        end_popup("🎉 You reached your savings goal early! Excellent financial planning.", success=True)
    if p["time"] <= 0:
        p["emotion"] = max(0, p["emotion"] - 2)
        p["time"] = 3
        st.warning("⏳ You ran out of time energy. -2 wellbeing, time reset to 3.")

    # End of game popup (all rounds played)
    if p["rounds_played"] >= tr:
        if p["savings"] >= fs.get("goal", 5000):
            end_popup("🏆 The game has ended — you reached your savings goal. Well done!", success=True)
        else:
            end_popup(f"⏰ The game has ended after {tr} rounds — you didn’t reach your goal yet. Reflect and try again!", success=False)

    draw_disabled = bool(p.get("current_card") or p["rounds_played"] >= tr)
    draw = st.button("🎴 Draw Life Card", type="primary", disabled=draw_disabled)

    if "life_cards" not in st.session_state:
        with open("data/life_cards.json", "r") as f:
            st.session_state.life_cards = json.load(f)

    if draw and not draw_disabled:
        apply_monthly_income(p)
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

        options = card.get("options", [])
        display_opts = [
            f"{opt['label']} → Money: {opt.get('money',0)}, Wellbeing: {opt.get('wellbeing',0)}, Time: {opt.get('time',0)}"
            for opt in options
        ]
        choice = st.radio("Choose an option:", display_opts, key="decision_choice")

        if st.button("💾 Save Decision", key="save_decision"):
            selected = options[display_opts.index(choice)]
            apply_card_effects(p, selected)

            p["rounds_played"] += 1
            p["decision_log"].append(f"{card['title']} — {choice}")
            p["choice_made"] = True
            p["current_card"] = None
            st.session_state.player = p

            st.success("✅ Decision saved! Next round starting...")
            time.sleep(0.4)
            st.rerun()

with right:
    st.markdown("#### 📈 Game Progress")
    st.markdown(f"**Rounds:** {rp}/{tr}")
    st.progress(pct_rounds)
    st.markdown("#### ❤️⚡ Wellbeing / Time")
    st.markdown(f"**Wellbeing:** {emoji_bar(p['emotion'], '❤️')}")
    st.markdown(f"**Time:** {emoji_bar(p['time'], '⚡')}")

# -------------------------------------------------
# Decision Log
# -------------------------------------------------
st.markdown("---")
st.subheader("🧾 Decision Log")
if p["decision_log"]:
    for i, d in enumerate(p["decision_log"], 1):
        st.write(f"**Round {i}:** {d}")
else:
    st.caption("No decisions yet.")
