import re
import streamlit as st

def clamp(n, lo, hi):
    return max(lo, min(hi, n))

def contains_any(text, keywords):
    t = text.lower()
    return any(k in t for k in keywords)

def count_numbers(text):
    return len(re.findall(r"\b\d+(\.\d+)?\b", text))

# Agent 1: Intent Decoder
def intent_decoder(decision_text, context=""):
    text = decision_text.strip()
    ctx = context.strip()

    timeframe = "Not specified"
    m = re.search(r"\b(in|within|over)\s+(\d+)\s+(day|days|week|weeks|month|months|quarter|quarters|year|years)\b", text.lower())
    if m:
        timeframe = f"{m.group(2)} {m.group(3)}"

    return {
        "decision": text,
        "context": ctx,
        "timeframe": timeframe,
        "signals": {
            "urgency": contains_any(text, ["asap", "immediately", "right away", "urgent"]),
            "scale": contains_any(text, ["scale", "roll out", "rollout", "expand", "enterprise-wide"]),
            "certainty": contains_any(text, ["no-brainer", "sure", "guaranteed", "can’t fail", "can't fail"]),
        },
    }

# Agent 2: Bias Detector
def bias_detector(intent):
    text = intent["decision"].lower()
    flags = []

    if contains_any(text, ["no-brainer", "sure", "guaranteed", "can’t fail", "can't fail"]):
        flags.append("Overconfidence bias")
    if contains_any(text, ["everyone", "obvious", "clearly"]):
        flags.append("Social proof / groupthink")
    if contains_any(text, ["quick", "fast", "asap", "immediately"]):
        flags.append("Optimism / planning fallacy")
    if contains_any(text, ["we've already invested", "sunk cost", "too much to stop"]):
        flags.append("Sunk cost fallacy")

    if not flags:
        flags.append("No strong bias detected (based on visible signals)")

    return flags

# Confidence Score (POC heuristic)
def confidence_score(decision_text, context_text):
    text = (decision_text or "") + " " + (context_text or "")
    t = text.lower()

    score = 55
    nums = count_numbers(text)
    score += clamp(nums * 4, 0, 20)

    if contains_any(t, ["because", "due to", "based on", "data", "analysis", "pilot", "experiment", "evidence"]):
        score += 10

    if contains_any(t, ["no-brainer", "guaranteed", "can't fail", "can’t fail", "zero risk", "no risk"]):
        score -= 15

    if len((decision_text or "").strip()) < 40:
        score -= 10
    if len((context_text or "").strip()) < 20:
        score -= 5

    return clamp(score, 0, 100)

# Agent 3: Counterargument Generator (Disagree Harder)
def counterargument_generator(intent, disagree_level):
    text = intent["decision"].lower()
    ctx = intent["context"].lower()

    counters = []

    if contains_any(text, ["launch", "rollout", "ship", "release"]):
        counters.append("Launching on an aggressive timeline increases execution risk and reduces time for validation.")
    if intent["signals"]["scale"]:
        counters.append("Scaling before validating assumptions can amplify losses and create operational/technical debt.")
    if intent["signals"]["urgency"]:
        counters.append("Urgency can crowd out risk discovery—what critical unknowns are you skipping because of time pressure?")
    if contains_any(text, ["marketing", "campaign", "spend"]):
        counters.append("Upfront spend can create commitment bias—consider staged investment tied to measurable outcomes.")
    if intent["signals"]["certainty"]:
        counters.append("High certainty may be masking untested assumptions—what evidence would change your mind?")

    if contains_any(ctx, ["budget", "$", "limited"]):
        counters.append("With a constrained budget, downside scenarios matter more—what if adoption is 50% of forecast?")

    if not counters:
        counters.append("The decision may be underestimating uncertainty and external dependencies (people, vendors, systems, approvals).")

    hard_additions = [
        "Pre-mortem: assume this fails in 6 months—what is the most likely reason?",
        "What is the strongest argument a skeptic would make that you are currently ignoring?",
        "If your key assumption is wrong, what irreversible cost (reputation, money, talent) do you incur?",
        "What alternative achieves 80% of the upside with 20% of the risk?",
    ]

    max_counters = {1: 2, 2: 3, 3: 4, 4: 5, 5: 6}[disagree_level]
    counters = counters[:max_counters]

    if disagree_level >= 3:
        counters.append(hard_additions[0])
    if disagree_level >= 5:
        counters.append(hard_additions[2])

    return counters

# Agent 4: Second-Order Impacts
def second_order_impacts(intent, disagree_level):
    text = intent["decision"].lower()
    impacts = []

    if contains_any(text, ["launch", "rollout", "ship", "release", "scale", "expand"]):
        impacts.append("Operational load may spike faster than team capacity, increasing failure rate and burnout.")
    if contains_any(text, ["integration", "integrations", "platform", "systems"]):
        impacts.append("Integration delays can cascade into missed timelines and budget overruns.")
    impacts.append("If early outcomes disappoint, reversing course may be reputationally costly.")
    impacts.append("Short-term optimization may reduce long-term optionality (harder pivots, locked-in commitments).")

    if disagree_level >= 4:
        impacts.append("Stakeholder trust can degrade if timelines are missed—slowing approvals for future initiatives.")

    return impacts

def derisk_recommendations(disagree_level):
    recs = [
        "Run a time-bound pilot to validate key assumptions before full commitment.",
        "Define explicit go/no-go criteria (metrics, thresholds, owners, dates).",
        "Stage funding/spend in tranches tied to outcomes rather than upfront commitments.",
        "Add a decision checkpoint before any irreversible investment (contracts, major hiring, public commitments).",
    ]
    return recs[: (3 if disagree_level <= 3 else 4)]

# Streamlit UI
st.set_page_config(page_title="AI That Disagrees With You", layout="wide")
st.title("AI That Disagrees With You (Intelligently) — POC")
st.caption("A constructive devil’s advocate for high-stakes decisions. Designed to surface blind spots, bias, and second-order effects.")

with st.form("decision_form"):
    decision_text = st.text_area(
        "Describe the decision you are about to make",
        value="We should launch Product X in 3 months; it’s a no-brainer and will capture market share quickly. Let’s push marketing spend ASAP and scale integrations.",
        height=140,
    )
    context_text = st.text_area(
        "Optional context (constraints, assumptions, goals)",
        value="Budget limited to $500k; growth is the priority.",
        height=80,
    )
    disagree_level = st.slider(
        "Disagree Harder 😈",
        min_value=1,
        max_value=5,
        value=3,
        help="Controls how strongly the system challenges the decision.",
    )
    submitted = st.form_submit_button("Challenge My Decision")

if submitted:
    intent = intent_decoder(decision_text, context_text)
    biases = bias_detector(intent)
    conf = confidence_score(decision_text, context_text)
    counterargs = counterargument_generator(intent, disagree_level)
    impacts = second_order_impacts(intent, disagree_level)
    recs = derisk_recommendations(disagree_level)

    col1, col2 = st.columns([2, 1])

    with col2:
        st.subheader("Decision Confidence Score")
        st.metric(label="Confidence (heuristic)", value=f"{conf}/100")
        st.progress(conf / 100)

        st.subheader("Bias Signals Detected")
        for b in biases:
            st.markdown(f"- {b}")

        st.subheader("Parsed Intent (POC)")
        st.json(intent)

    with col1:
        st.subheader("AI Disagreement")
        st.markdown("**Key Counterarguments**")
        for c in counterargs:
            st.markdown(f"- {c}")

        st.markdown("**Second-Order Impacts**")
        for i in impacts:
            st.markdown(f"- {i}")

        st.markdown("**De-risking Recommendations**")
        for r in recs:
            st.markdown(f"- {r}")

    st.success("Done. This tool challenges decisions; it does not make them. Human judgment remains in control.")
