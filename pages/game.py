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
# Style (fixed header layout)
# -------------------------------------------------
st.markdown(
    """
<style>
div.block-container {
  max-width: 1280px;
  padding-top: 3rem; /* more breathing space at top */
}

/* Header layout */
.header-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-start; /* align top edge cleanly */
  margin-bottom: 1.5rem;
  padding-top: 0.5rem;
}
.header-title {
  font-size: 1.8rem;
  font-weight: 800;
  line-height: 1.25;
  margin: 0;
}
.rounds {
  text-align: right;
  font-size: 0.9rem;
}
.rounds progress {
  width: 180px;         /* a bit wider */
  height: 8px;
  border-radius: 4px;
  accent-color: #1f6feb;
  display: block;
  margin-top: 0.4rem;   /* spacing between label & bar */
}

/* Section hierarchy */
h4 { font-size: 1rem !important; font-weight: 700 !important; }
.section-title { font-size: 1.1rem; font-weight: 750; margin-top: 1rem; }

/* Columns */
div[data-testid="column"] { padding-left: 0.5rem !important; padding-right: 0.5rem !important; }

/* Inputs */
div[data-testid="stNumberInput"] > div { width: 100% !important; }
div[data-testid="stNumberInput"] input { width: 100% !important; font-size: 0.9rem; }

/* Progress bar */
.stProgress > div > div { height: 6px !important; border-radius: 3px !important; }
</style>
""",
    unsafe_allow_html=True,
)

# -------------------------------------------------
# Header (clean + aligned)
# -------------------------------------------------
rp = p["rounds_played"]
tr = fs.get("rounds", 10)
pct_rounds = min(1.0, float(rp) / max(1, float(tr)))

st.markdown(
    f"""
<div class="header-row">
  <div class="header-title">💰 Savings Monopoly</div>
  <div class="rounds">
    <div><b>Game Progress</b></div>
    <progress value="{pct_rounds}" max="1"></progress>
    <div>{rp}/{tr} rounds played</div>
  </div>
</div>
""",
    unsafe_allow_html=True,
)

# -------------------------------------------------
# KPI ROW – all 4 KPIs in ONE row & ONE box
# -------------------------------------------------
remaining = int(p["income"] - p["fixed_costs"])

with st.container(border=True):
    c1, c2, c3, c4 = st.columns(4, gap="medium")

    # --------- K1: Budget Overview ---------
    with c1:
        st.markdown("#### 💰 Budget Overview")
        st.markdown(f"**Monthly Income:** {fmt(p['income'])}")
        st.markdown(f"**Fixed Costs:** {fmt(p['fixed_costs'])}")
        st.markdown(f"**Remaining:** {fmt(remaining)}")

    # --------- K2: Savings Goal ---------
    with c2:
        st.markdown("#### 🎯 Savings Goal")
        goal = fs.get("goal", 5000)
        pct = p["savings"] / goal if goal else 0
        st.progress(min(1.0, pct))
        st.markdown(f"**{fmt(p['savings'])} / {fmt(goal)}** ({int(pct * 100)}%)")
        p["allocation"]["savings"] = st.number_input(
            "Monthly allocation (Savings):",
            0,
            remaining,
            int(p["allocation"]["savings"]),
            50,
            key="alloc_sav",
        )

    # --------- K3: Emergency Fund ---------
    with c3:
        st.markdown("#### 🛟 Emergency Fund")
        st.markdown(f"**Balance:** {fmt(p['ef_balance'])}")
        st.caption(f"Cap: {fmt(p['ef_cap'])}")
        p["allocation"]["ef"] = st.number_input(
            "Monthly allocation (EF):",
            0,
            remaining,
            int(p["allocation"]["ef"]),
            50,
            key="alloc_ef",
        )

    # --------- K4: Wants Fund ---------
    with c4:
        st.markdown("#### 🎉 Wants Fund")
        st.markdown(f"**Balance:** {fmt(p['wants_balance'])}")
        st.caption("Cap: None")
        p["allocation"]["wants"] = st.number_input(
            "Monthly allocation (Wants):",
            0,
            remaining,
            int(p["allocation"]["wants"]),
            50,
            key="alloc_w",
        )

# -------------------------------------------------
# Game Logic – new per-fund delta logic
# -------------------------------------------------
def simulate_choice_and_validate(p, selected):
    """
    Simulate: starting from current pots, add monthly allocation,
    then apply the card deltas. Return whether it's valid and
    the resulting new state if yes.
    """

    # Deltas from the card (new schema)
    s_delta = selected.get("savings_delta", 0)
    ef_delta = selected.get("ef_delta", 0)
    w_delta = selected.get("wants_delta", 0)
    wellbeing_delta = selected.get("wellbeing", 0)
    time_cost = selected.get("time", 0)

    # 1) Apply monthly allocation inflows
    alloc_sav = p["allocation"].get("savings", 0)
    alloc_ef = p["allocation"].get("ef", 0)
    alloc_w = p["allocation"].get("wants", 0)

    savings_after_alloc = p["savings"] + alloc_sav
    ef_after_alloc = min(p["ef_cap"], p["ef_balance"] + alloc_ef)
    wants_after_alloc = p["wants_balance"] + alloc_w

    # 2) Apply card deltas on top
    new_savings = savings_after_alloc + s_delta
    new_ef = ef_after_alloc + ef_delta
    new_wants = wants_after_alloc + w_delta

    # 3) Validate pots non-negative
    if new_savings < 0:
        return False, "Not enough in your savings pot to cover this decision.", None
    if new_ef < 0:
        return False, "Not enough in your emergency fund to cover this decision.", None
    if new_wants < 0:
        return False, "Not enough in your wants fund to cover this decision.", None

    # 4) Validate time
    new_time = p["time"] - time_cost
    if new_time < 0:
        return False, "Not enough time/energy to take this action.", None

    # 5) Validate wellbeing
    new_emotion = p["emotion"] + wellbeing_delta
    if new_emotion < 0 or new_emotion > 10:
        return False, "This decision would push well-being out of range (0–10).", None

    # Clamp wellbeing inside range just in case
    new_emotion = max(0, min(10, new_emotion))

    # If everything is fine, return the prospective new state
    new_state = {
        "savings": new_savings,
        "ef_balance": new_ef,
        "wants_balance": new_wants,
        "time": new_time,
        "emotion": new_emotion,
    }
    return True, "", new_state


def end_popup(msg, success=False):
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
# Game Round + Stats
# -------------------------------------------------
left, right = st.columns([2, 1], gap="large")

with left:
    st.markdown('<div class="section-title">🎴 Game Round</div>', unsafe_allow_html=True)

    # End conditions (global)
    if p["emotion"] <= 0:
        end_popup("💥 You burned out! Game over.", success=False)
    if p["savings"] >= fs.get("goal", 5000):
        end_popup("🎉 You reached your savings goal early! Great job.", success=True)
    if p["time"] <= 0:
        p["emotion"] = max(0, p["emotion"] - 2)
        p["time"] = 3
        st.warning("⏳ You ran out of time. -2 wellbeing, time reset to 3.")

    if p["rounds_played"] >= tr:
        if p["savings"] >= fs.get("goal", 5000):
            end_popup("🏆 The game ended — you achieved your goal! 🥳", success=True)
        else:
            end_popup(
                f"⏰ The game ended after {tr} rounds — goal not reached. Try again!",
                success=False,
            )

    # Draw button
    draw_disabled = bool(p.get("current_card") or p["rounds_played"] >= tr)
    draw = st.button("🎴 Draw Life Card", type="primary", disabled=draw_disabled)

    # Load cards once
    if "life_cards" not in st.session_state:
        with open("data/life_cards.json", "r") as f:
            st.session_state.life_cards = json.load(f)

    # Draw a new card (no monthly income applied here; it's inside simulation)
    if draw and not draw_disabled:
        p["current_card"] = random.choice(st.session_state.life_cards)
        p["choice_made"] = False
        st.session_state.player = p

    # Show card / choices
    if not p.get("current_card"):
        st.caption("Draw a life card to start the month.")
    else:
        card = p["current_card"]
        st.subheader(card.get("title", "Life Event"))
        if card.get("description"):
            st.write(card["description"])

        options = card.get("options", [])

        # New display string: show deltas per fund + wellbeing + time
        display_opts = [
            f"{opt['label']} → Savings: {opt.get('savings_delta',0)}, "
            f"EF: {opt.get('ef_delta',0)}, Wants: {opt.get('wants_delta',0)}, "
            f"Wellbeing: {opt.get('wellbeing',0)}, Time: {opt.get('time',0)}"
            for opt in options
        ]

        choice = st.radio("Choose an option:", display_opts, key="decision_choice")

        if st.button("💾 Save Decision", key="save_decision"):
            selected = options[display_opts.index(choice)]

            # 1) Simulate: allocation inflows + card deltas, validate
            ok, msg, new_state = simulate_choice_and_validate(p, selected)

            if not ok:
                st.warning(f"❗ {msg} Please choose a different option.")
            else:
                # 2) Commit new balances and stats
                p["savings"] = new_state["savings"]
                p["ef_balance"] = new_state["ef_balance"]
                p["wants_balance"] = new_state["wants_balance"]
                p["time"] = new_state["time"]
                p["emotion"] = new_state["emotion"]

                # 3) Finish the round
                p["rounds_played"] += 1
                p["decision_log"].append(f"{card['title']} — {choice}")
                p["choice_made"] = True
                p["current_card"] = None

                st.session_state.player = p
                st.success("✅ Decision saved! Next round starting...")
                time.sleep(0.4)
                st.rerun()

with right:
    st.markdown('<div class="section-title">❤️⚡ Wellbeing / Time</div>', unsafe_allow_html=True)
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
