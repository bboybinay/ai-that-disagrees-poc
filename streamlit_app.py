import os
import streamlit as st

# -----------------------------
# Agent logic (mock POC)
# -----------------------------
def intent_decoder(decision_text, context=""):
    return {
        "decision": decision_text.strip(),
        "actor": "Leadership Team",
        "action": "Proposed decision",
        "timeframe": "Near term",
        "stated_goals": "As provided by user",
        "confidence_clues": ["urgent tone" if "ASAP" in decision_text.upper() else "neutral"]
    }

def bias_detector(intent_struct):
    text = intent_struct["decision"].lower()
    flags = []

    if "no-brainer" in text or "sure" in text:
        flags.append("Overconfidence bias")
    if "everyone" in text or "obvious" in text:
        flags.append("Groupthink / social proof")
    if any(k in text for k in ["quick", "fast", "easy", "scale quickly"]):
        flags.append("Optimism bias")

    if not flags:
        flags.append("No strong bias detected")

    return flags

def counterargument_generator():
    return [
        "Market adoption may be slower than expected due to competitive pressure.",
        "Early launch could lock resources and reduce flexibility to pivot.",
        "Financial projections assume optimistic conversion rates that may not materialize."
    ]

def second_order_impacts():
    return [
        "Revenue impact could be marginal in year one under realistic adoption.",
        "Operational strain may increase due to accelerated timelines.",
        "Reputational risk if expectations are not met publicly."
    ]

def derisk_recommendations():
    return [
        "Run a limited pilot before full-scale launch.",
        "Define clear go/no-go success criteria.",
        "Maintain contingency budget and rollback options."
    ]

# -----------------------------
# Streamlit UI
# -----------------------------
st.set_page_config(page_title="AI That Disagrees With You", layout="wide")
st.title("AI That Disagrees With You (Intelligently)")
st.caption("A constructive devil’s advocate for high-stakes decisions")

with st.form("decision_form"):
    decision_text = st.text_area(
        "Describe the decision you are about to make",
        value="We should launch Product X in 3 months; it’s a no-brainer and will capture market share quickly.",
        height=150
    )
    context_text = st.text_area(
        "Optional context (constraints, assumptions, goals)",
        value="Budget limited to $500k; growth is the priority",
        height=80
    )
    submitted = st.form_submit_button("Challenge My Decision")

if submitted:
    intent = intent_decoder(decision_text, context_text)
    biases = bias_detector(intent)
    counterargs = counterargument_generator()
    impacts = second_order_impacts()
    recs = derisk_recommendations()

    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("🧠 AI Disagreement")
        st.markdown("**Key Counterarguments**")
        for c in counterargs:
            st.markdown(f"- {c}")

        st.markdown("**Second-Order Impacts**")
        for i in impacts:
            st.markdown(f"- {i}")

        st.markdown("**De-risking Recommendations**")
        for r in recs:
            st.markdown(f"- {r}")

    with col2:
        st.subheader("⚠️ Bias Signals Detected")
        for b in biases:
            st.markdown(f"- {b}")

    st.success("Decision challenged successfully. Human judgment remains in control.")


