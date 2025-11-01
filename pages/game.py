# pages/game.py

import streamlit as st
import json
import random
import time

# -------------------------------
# Helpers
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
# Guard
# -------------------------------
if "player" not in st.session_state or "facilitator_settings" not in st.session_state:
    st.warning("No player data found. Please start from the setup page.")
    st.stop()

player = st.session_state.player
fs = st.session_state.facilitator_settings

# Defaults
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
player.setdefault("wants_cap", None)
player.setdefault("wants_balance", 0)
player.setdefault("allocation", {
    "savings": max(0, player["income"] - player["fixed_costs"]) // 2,
    "ef": 0,
    "wants": max(0, player["income"] - player["fixed_costs"]) // 2,
})
st.set_page_config(layout="wide")
st.session_state.player = player

# -------------------------------
# CSS — compact headers + real KPI boxes using :has()
# -------------------------------
st.markdown("""
<style>
/* Layout / padding (prevents title cut) */
div.block-container{
  max-width:1280px;
  padding-top:4rem!important;
  padding-bottom:0.8rem!important;
  margin:0 auto;
  overflow:visible!important;
  background:transparent!important;
}

/* Global heading scale (smaller everywhere) */
h1, .header-title{ font-size:1.9rem!important; }
h2{ font-size:1.35rem!important; }
h3{ font-size:1.15rem!important; }
h4, h5, h6{ font-size:0.95rem!important; }

/* Header row */
.header-row{
  display:flex;justify-content:space-between;align-items:flex-end;margin-bottom:0.8rem;
}
.header-title{
  font-weight:800;line-height:1.1;margin:0;white-space:nowrap;overflow:visible;
}
.rounds{ text-align:right; font-size:0.9rem; }
.rounds progress{ width:140px;height:5px;border-radius:3px;accent-color:#1f6feb;margin-top:4px; }

/* Tighter column gutters */
div[data-testid="column"]{ padding-left:.6rem!important; padding-right:.6rem!important; }

/* Real card styling via :has() marker */
div[data-testid="stVerticalBlock"]:has(> .kpi-marker){
  background:#fff!important; border-radius:16px; box-shadow:0 3px 10px rgba(0,0,0,.06);
  padding:16px 18px!important;
}

/* Number inputs full width + compact */
div[data-testid="stNumberInput"]>div{ width:100%!important; }
div[data-testid="stNumberInput"] input{ width:100%!important; font-size:.95rem; }

/* Slim progress bars */
.stProgress>div>div{ height:6px!important; border-radius:3px!important; }

/* Remove stray rules */
hr,.stDivider{ display:none!important; }
</style>
""", unsafe_allow_html=True)

# -------------------------------
# Header
# -------------------------------
rp = player["rounds_played"]
tr = fs.get("rounds", 12)
pct_rounds = min(1.0, max(0.0, float(rp)/max(1,float(tr))))

st.markdown(f"""
<div class="header-row">
  <div class="header-title">💰 Savings Monopoly</div>
  <div class="rounds"><b>Rounds:</b> {rp}/{tr}<br><progress value="{pct_rounds}" max="1"></progress></div>
</div>
""", unsafe_allow_html=True)

# -------------------------------
# KPI ROW (cards now truly wrap their content)
# -------------------------------
remaining = player["income"] - player["fixed_costs"]
k1, k2, k3, k4 = st.columns(4, gap="small")

with k1:
    box = st.container()
    box.markdown('<span class="kpi-marker kpi-budget"></span>', unsafe_allow_html=True)
    st.markdown("#### 💰 Budget Overview")
    st.markdown(f"**Monthly Income:** {format_currency(player['income'])}")
    st.markdown(f"**Fixed Costs:** {format_currency(player['fixed_costs'])}")
    st.markdown(f"**Remaining:** {format_currency(remaining)}")

with k2:
    box = st.container()
    box.markdown('<span class="kpi-marker kpi-savings"></span>', unsafe_allow_html=True)
    st.markdown("#### 🎯 Savings Goal")
    goal_value = fs.get("goal", 5000)
    savings_value = player.get("savings", 0)
    pct = (savings_value / goal_value) if goal_value else 0.0
    st.progress(max(0.0, min(1.0, pct)))
    st.markdown(f"**{format_currency(savings_value)} / {format_currency(goal_value)}** ({int(max(0,min(1,pct))*100)}%)")
    alloc_sav = st.number_input(
        "Monthly allocation:", min_value=0, value=int(player["allocation"]["savings"]),
        step=50, key="alloc_savings_input"
    )
    player["allocation"]["savings"] = alloc_sav

with k3:
    box = st.container()
    box.markdown('<span class="kpi-marker kpi-ef"></span>', unsafe_allow_html=True)
    st.markdown("#### 🛟 Emergency Fund")
    st.markdown(f"**Balance:** {format_currency(player['ef_balance'])}")
    st.caption(f"Cap: {format_currency(player['ef_cap'])}")
    alloc_ef = st.number_input(
        "Monthly allocation:", min_value=0, value=int(player["allocation"]["ef"]),
        step=50, key="alloc_ef_input"
    )
    player["allocation"]["ef"] = alloc_ef

with k4:
    box = st.container()
    box.markdown('<span class="kpi-marker kpi-wants"></span>', unsafe_allow_html=True)
    st.markdown("#### 🎉 Wants Fund")
    st.markdown(f"**Balance:** {format_currency(player['wants_balance'])}")
    st.caption("Cap: None")
    alloc_wants = st.number_input(
        "Monthly allocation:", min_value=0, value=int(player["allocation"]["wants"]),
        step=50, key="alloc_wants_input"
    )
    player["allocation"]["wants"] = alloc_wants

st.session_state.player = player

# -------------------------------
# Row 2: Game + Progress/Wellbeing cards (also real boxes)
# -------------------------------
left, right = st.columns([2, 1], gap="large")

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
        if not pool:
            st.error("No life cards available for this round type.")
            st.stop()
        player["current_card"] = random.choice(pool)
        player["choice_made"] = False
        st.session_state.player = player

    if not player.get("current_card"):
        st.caption("Draw a life card to start the month.")
    else:
        card = player["current_card"]
        st.subheader(card.get("title", "Life Event"))
        desc = card.get("description", "")
        if desc:
            st.write(desc)

        options = []
        for opt in card.get("options", []):
            label = opt.get("label", "Option")
            money = opt.get("money", 0)
            wellbeing = opt.get("wellbeing", 0)
            time_cost = opt.get("time", 0)
            options.append(f"{label} → Money: {money}, Wellbeing: {wellbeing}, Time: {time_cost}")

        if options:
            choice = st.radio("Choose an option:", options, key="decision_choice")

            sum_alloc = (player["allocation"]["savings"] +
                         player["allocation"]["ef"] +
                         player["allocation"]["wants"])
            if sum_alloc != remaining:
                st.warning(
                    f"Your monthly allocations ({format_currency(sum_alloc)}) must equal the remaining budget "
                    f"({format_currency(remaining)}). Adjust the fields above."
                )

            if st.button("💾 Save Decision", key="save_decision"):
                if sum_alloc != remaining:
                    st.error("Allocations do not match remaining budget.")
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
                                st.error("💸 Not enough funds to cover this.")
                                st.stop()
                            player["savings"] -= need
                    else:
                        player["savings"] += delta_money

                    player["emotion"] = max(0, min(10, player["emotion"] + delta_wellbeing))
                    if player["time"] - delta_time < 0:
                        st.error("⏳ Not enough time energy to take this option.")
                        st.stop()
                    player["time"] -= delta_time

                    player["rounds_played"] += 1
                    player["decision_log"].append(f"{card['title']} — {choice}")
                    player["choice_made"] = True
                    player["current_card"] = None
                    st.session_state.player = player

                    st.success("✅ Decision saved!")
                    time.sleep(0.4)
                    st.rerun()

with right:
    gp = st.container()
    gp.markdown('<span class="kpi-marker kpi-progress"></span>', unsafe_allow_html=True)
    st.markdown("#### 📈 Game Progress")
    st.markdown(f"**Rounds:** {rp}/{tr}")
    st.progress(pct_rounds)

    wb = st.container()
    wb.markdown('<span class="kpi-marker kpi-wellbeing"></span>', unsafe_allow_html=True)
    st.markdown("#### ❤️⚡ Wellbeing / Time Overview")
    st.markdown(f"**Wellbeing:** {render_emoji_stat(player['emotion'], '❤️')}")
    st.markdown(f"**Time:** {render_emoji_stat(player['time'], '⚡')}")

# -------------------------------
# Decision Log
# -------------------------------
st.markdown("""<hr style="display:block;border:none;border-top:1px solid #eee;margin:1rem 0 0.5rem 0;">""",
            unsafe_allow_html=True)
st.subheader("🧾 Decision Log")
if player["decision_log"]:
    for i, d in enumerate(player["decision_log"], 1):
        st.write(f"**Round {i}:** {d}")
else:
    st.caption("No decisions logged yet.")
