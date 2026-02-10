import os
import re
import json
import streamlit as st

# Optional OpenAI (single-call) integration
# Streamlit Cloud: set Secrets -> OPENAI_API_KEY="..."
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
HAS_OPENAI = bool(OPENAI_API_KEY)

def clamp(n, lo, hi):
    return max(lo, min(hi, n))

def contains_any(text, keywords):
    t = (text or "").lower()
    return any(k in t for k in keywords)

def count_numbers(text):
    return len(re.findall(r"\b\d+(\.\d+)?\b", text or ""))

# -----------------------------
# Agent 1: Intent Decoder (POC heuristic)
# -----------------------------
def intent_decoder(decision_text, context=""):
    text = (decision_text or "").strip()
    ctx = (context or "").strip()

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

# -----------------------------
# Agent 2: Bias Detector (POC heuristic)
# -----------------------------
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

# -----------------------------
# Confidence Score (POC heuristic)
# -----------------------------
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

# -----------------------------
# Template mode (no LLM)
# -----------------------------
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
        "If your key assumption is wrong, what irreversible cost (reputation, money, talent) do you incur?",
    ]
    if disagree_level >= 3:
        counters.append(hard_additions[0])
    if disagree_level >= 5:
        counters.append(hard_additions[1])

    # Make levels visibly different
    max_n = {1: 2, 2: 3, 3: 4, 4: 5, 5: 6}[disagree_level]
    return counters[:max_n]

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

# -----------------------------
# OpenAI single-call (Counterarguments + Impacts + Recommendations in one shot)
# -----------------------------
def openai_one_call(intent, disagree_level):
    """
    Makes a single LLM call and returns dict with keys:
    - counterarguments: list[str]
    - impacts: list[str]
    - recommendations: list[str]
    """
    # Lazy import so template mode works even if openai isn't installed.
    from openai import OpenAI
    client = OpenAI(api_key=OPENAI_API_KEY)

    mode = {1:"gentle",2:"constructive",3:"devils_advocate",4:"hard_pushback",5:"brutally_honest"}[disagree_level]

    prompt = f"""
You are a constructive devil's advocate AI. Your job is to CHALLENGE a human decision, not to decide for them.

Decision:
{intent['decision']}

Context:
{intent['context']}

Parsed signals:
{json.dumps(intent['signals'], indent=2)}

Disagreement intensity: {disagree_level}/5 ({mode})

Return ONLY valid JSON with this exact schema:
{{
  "counterarguments": ["..."],
  "impacts": ["..."],
  "recommendations": ["..."]
}}

Rules:
- Be specific to the decision and context.
- Counterarguments should increase in sharpness with intensity.
- Impacts should focus on second-order effects (downstream consequences).
- Recommendations must be practical de-risking steps (pilot, checkpoints, metrics, staged investment, etc.).
- No extra keys, no markdown, no prose outside JSON.
"""

    # Temperature slightly increases with intensity for variety, but stays controlled.
    temperature = 0.3 + (disagree_level * 0.08)

    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role":"user", "content": prompt}],
        temperature=temperature,
        max_tokens=1000,
    )

    raw = resp.choices[0].message.content.strip()

    # Robust JSON parse (strip accidental leading/trailing text if any)
    try:
        return json.loads(raw)
    except Exception:
        # Try to salvage JSON if the model wrapped it with text
        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(raw[start:end+1])
        raise

# -----------------------------
# Streamlit UI
# -----------------------------
st.set_page_config(page_title="AI That Disagrees With You", layout="wide")
st.title("AI That Disagrees With You (Intelligently) — POC")
st.caption("Most AI accelerates decisions.")
st.caption("This AI improves them.")

with st.form("decision_form"):
    decision_text = st.text_area(
        "Describe the decision you are about to make",
        value="We should launch Product X in 3 months; it’s a no-brainer and will capture market share quickly. Let’s push marketing spend ASAP and scale integrations.",
        height=140,
    )
    context_text = st.text_area(
        "Optional context (constraints, assumptions, goals)",
        value="Budget limited to $500k; growth is the priority. Assumption: 30% conversion; CAC $50.",
        height=90,
    )
    disagree_level = st.slider(
        "Disagree Harder 😈",
        min_value=1,
        max_value=5,
        value=3,
        help="Controls how strongly the system challenges the decision.",
    )
    use_openai = st.checkbox("Use OpenAI (single call) for smarter outputs", value=False, disabled=not HAS_OPENAI)
    submitted = st.form_submit_button("Challenge My Decision")

if not HAS_OPENAI:
    st.info("Tip: To enable OpenAI mode on Streamlit Cloud, add OPENAI_API_KEY in App Settings → Secrets.")

if submitted:
    mode_label = {1:"Gentle nudge 🤝",2:"Constructive challenge 🧐",3:"Devil’s advocate 😈",4:"Hard pushback ⚠️",5:"Brutally honest 🔥"}[disagree_level]
    st.info(f"Disagreement mode: **{mode_label}**")

    intent = intent_decoder(decision_text, context_text)
    biases = bias_detector(intent)
    conf = confidence_score(decision_text, context_text)

    # Generate outputs
    llm_error = None
    if use_openai and HAS_OPENAI:
        try:
            out = openai_one_call(intent, disagree_level)
            counterargs = out.get("counterarguments", [])
            impacts = out.get("impacts", [])
            recs = out.get("recommendations", [])
        except Exception as e:
            llm_error = str(e)
            counterargs = counterargument_generator(intent, disagree_level)
            impacts = second_order_impacts(intent, disagree_level)
            recs = derisk_recommendations(disagree_level)
    else:
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

        with st.expander("How the AI interpreted your decision (Parsed Intent)"):
            st.json(intent)

        if llm_error:
            st.warning("OpenAI call failed; fell back to template mode.")
            st.caption(llm_error[:300])

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
