# pages/game.py

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
# Session guard
# -------------------------------
if "player" not in st.session_state or "facilitator_settings" not in st.session_state:
    st.warning("No player data found. Please start from the setup page.")
    st.stop()

player = st.session_state.player
fs = st.session_state.facilitator_settings

player.setdefault("rounds_played", 0)
player.setdefault("savings", 0)
player.setdefault("emotion", 5)
player.setdefault("time", 5)
player.setdefault("decision_log", [])
player.setdefault("current_card", None)
player.setdefault("choice_made", False)
player.setdefault("income", fs.get("income", 2000))
player.setdefault("fixed_costs", fs.get("fixed_costs", 1000))
player.setdefault("ef_balance", 0)
player.setdefault("wants_balance", 0)
player.setdefault("ef_cap", 3000)
player.setdefault("allocation", {"savings": 334, "ef": 333, "wants": 333})

st.set_page_config(layout="wide")

# -------------------------------
# CSS for layout
# -------------------------------
st.markdown("""
<style>
div.block-container {
  max-width: 1250px;
  padding-top: 0.4rem;
  padding-bottom: 0.4rem;
  margin: 0 auto;
}

/* KPI boxes */
.kpi-card {
  background: white;
  border-radius: 16px;
  box-shadow: 0 3px 10px rgba(0,0,0,0.07);
  padding: 18px 20px !important;
  height: 100%;
}
.kpi-card h5 {
  font-size: 1rem !important;
  font-weight: 700 !important;
  margin-bottom: 8px !important;
}

/* General adjustments */
hr, .stDivider { display: none; }
.stProgress > div > div { height: 6px !important; border-radius: 3px !important; }

/* Column padding */
div[data-testid="column"] { padding-left: 0.4rem !important; padding-right: 0.4rem !important; }

/* Section spacing */
.section-space { margin-top: 1.2rem; }

/* Progress bar beside Game Round */
.round-progress {
  text-align: right;
  font-size: 0.9rem;
}
.round-progress progress {
  width: 180px;
  height: 6px;
  accent-color: #1f6feb;
  border-radius: 3px;
}
</style>
""", unsafe_allow_html=True)

# -------------------------------
# KPI ROW
# -------------------------------
remaining = player["income"] - player["fixed_costs"]

c1, c2, c3, c4 = st.columns(4, gap="small")

with c1:
    st.markdown('<div class="kpi-card">', unsafe_allow_html=True)
    st.markdown("##### 💰 Budget Overview")
    st.markdown(f"**Monthly Income:** {format_currency(player['income'])}")
    st.markdown(f"**Fixed Costs:** {format_currency(player['fixed_costs'])}")
    st.markdown(f"**Remaining:** {format_currency(remaining)}")
    st.markdown("</div>", unsafe_allow_html=True)

with c2:
    st.markdown('<div class="kpi-card">', unsafe_allow_html=True)
    st.markdown("##### 🎯 Savings Goal")
    goal_value = fs.get("goal", 5000)
    savings_value = player.get("savings", 0)
    pct = max(0.0, min(1.0, savings_value / goal_value if goal_value else 0))
    st.progress(pct)
    st.markdown(f"**{format_currency(savings_value)} / {format_currency(goal_value)}** ({int(pct*100)}%)")
    alloc_sav = st.number_input("Monthly allocation:", min_value=0, value=int(player["allocation"]["savings"]),
                                step=50, key="alloc_sav")
    player["allocation"]["savings"] = alloc_sav
    st.markdown("</div>", unsafe_allow_html=True)

with c3:
    st.markdown('<div class="kpi-card">', unsafe_allow_html=True)
    st.markdown("##### 🛟 Emergency Fund")
    st.markdown(f"**Balance:** {format_currency(player['ef_balance'])}")
    st.caption(f"Cap: {format_currency(player['ef_cap'])}")
    alloc_ef = st.number_input("Monthly allocation:", min_value=0, value=int(player["allocation"]["ef"]),
                               step=50, key="alloc_ef")
    player["allocation"]["ef"] = alloc_ef
    st.markdown("</div>", unsafe_allow_html=True)

with c4:
    st.markdown('<div class="kpi-card">', unsafe_allow_html=True)
    st.markdown("##### 🎉 Wants Fund")
    st.markdown(f"**Balance:** {format_currency(player['wants_balance'])}")
    st.caption("Cap: None")
    alloc_wants = st.number_input("Monthly allocation:", min_value=0, value=int(player["allocation"]["wants"]),
                                  step=50, key="alloc_wants")
    player["allocation"]["wants"] = alloc_wants
    st.markdown("</div>", unsafe_allow_html=True)

st.session_state.player = player

# -------------------------------
# GAME + PROGRESS + WELLBEING
# -------------------------------
st.markdown('<div class="section-space"></div>', unsafe_allow_html=True)
left, right = st.columns([2, 1], gap="large")

rp = player["rounds_played"]
tr = fs.get("rounds", 12)
pct_rounds = min(1.0, max(0.0, float(rp) / max(1, float(tr))))

with left:
    st.markdown("### 🎴 Game Round")
    draw_disabled = player.get("current_card") is not None or player["rounds_played"] >= tr
    draw = st.button("🎴 Draw Life Card", type="primary", disabled=draw_disabled)

    if "life_cards" not in st.session_state:
        with open("data/life_cards.json", "r") as f:
            st.session_state.life_cards = json.load(f)

    def allowed_types(round_idx, p):
        base = ["positive", "neutral", "negative_type_1"]
        if round_idx >= 4:
            base.append("negative_type_2")
        if p["savings"] >= fs.get("goal", 0) * 0.6:
            base.append("temptation")
        return base

    def apply_monthly_allocations(p):
        p["ef_balance"] = min(p["ef_cap"], p["ef_balance"] + p["allocation"]["ef"])
        p["wants_balance"] += p["allocation"]["wants"]
        p["savings"] += p["allocation"]["savings"]

    if draw and not draw_disabled:
        apply_monthly_allocations(player)
        permitted = allowed_types(player["rounds_played"] + 1, player)
        pool = [c for c in st.session_state.life_cards if c.get("type") in permitted]
        player["current_card"] = random.choice(pool)
        player["choice_made"] = False
        st.session_state.player = player

    if not player.get("current_card"):
        st.caption("Draw a life card to start the month.")
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
            sum_alloc = sum(player["allocation"].values())
            remaining = player["income"] - player["fixed_costs"]

            if sum_alloc != remaining:
                st.warning(f"Allocations ({format_currency(sum_alloc)}) must equal remaining ({format_currency(remaining)}).")

            if st.button("💾 Save Decision", key="save_decision"):
                if sum_alloc != remaining:
                    st.error("Fix your allocations before saving.")
                    st.stop()

                if not player.get("choice_made"):
                    selected = card["options"][options.index(choice)]
                    delta_money = selected.get("money", 0)
                    delta_wellbeing = selected.get("wellbeing", 0)
                    delta_time = selected.get("time", 0)

                    if delta_money < 0:
                        need = abs(delta_money)
                        from_wants = min(need, player["wants_balance"])
                        player["wants_balance"] -= from_wants
                        need -= from_wants
                        if need > 0:
                            if need > player["savings"]:
                                st.error("💸 Not enough funds.")
                                st.stop()
                            player["savings"] -= need
                    else:
                        player["savings"] += delta_money

                    player["emotion"] = max(0, min(10, player["emotion"] + delta_wellbeing))
                    if player["time"] - delta_time < 0:
                        st.error("⏳ Not enough time energy.")
                        st.stop()
                    player["time"] -= delta_time

                    player["rounds_played"] += 1
                    player["decision_log"].append(f"{card['title']} — {choice}")
                    player["choice_made"] = True
                    player["current_card"] = None
                    st.session_state.player = player
                    st.success("✅ Decision saved.")
                    time.sleep(0.4)
                    st.rerun()

with right:
    st.markdown(f"""
    <div class="round-progress">
      <b>Rounds:</b> {rp}/{tr}<br>
      <progress value="{pct_rounds}" max="1"></progress>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="kpi-card" style="margin-top:10px;">', unsafe_allow_html=True)
    st.markdown("##### ❤️⚡ Wellbeing / Time")
    st.markdown(f"**Wellbeing:** {render_emoji_stat(player['emotion'], '❤️')}")
    st.markdown(f"**Time:** {render_emoji_stat(player['time'], '⚡')}")
    st.markdown("</div>", unsafe_allow_html=True)

# -------------------------------
# Decision Log
# -------------------------------
st.markdown("""<hr style="border:none;border-top:1px solid #eee;margin:1rem 0 0.5rem 0;">""", unsafe_allow_html=True)
st.subheader("🧾 Decision Log")
if player["decision_log"]:
    for i, d in enumerate(player["decision_log"], 1):
        st.write(f"**Round {i}:** {d}")
else:
    st.caption("No decisions logged yet.")
