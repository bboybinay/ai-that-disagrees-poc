"""
Streamlit POC for "AI That Disagrees With You (Intelligently)"
Run locally: streamlit run streamlit_app.py
This app runs in "mock" mode by default (no API keys required). If OPENAI_API_KEY is set and openai is installed,
it will attempt to use the OpenAI API for richer outputs.
"""

# Note: This file is safe to run locally. It intentionally avoids executing Streamlit-specific calls
# at import time so it can be parsed in environments without streamlit installed.

def get_streamlit_app_code():
    return r\"\"\"import os, streamlit as st, json

OPENAI_KEY = os.getenv("OPENAI_API_KEY")
USE_OPENAI = False
if OPENAI_KEY:
    try:
        import openai
        openai.api_key = OPENAI_KEY
        USE_OPENAI = True
    except Exception:
        USE_OPENAI = False

def intent_decoder(decision_text, context=""):
    result = {
        "decision": decision_text.strip(),
        "actor": "Leadership Team",
        "action": "Launch Product X",
        "timeframe": "3 months",
        "stated_goals": "Capture new market, grow revenue",
        "confidence_clues": ["urgent tone" if "ASAP" in decision_text.upper() else "neutral"]
    }
    return result

def bias_detector(intent_struct):
    text = intent_struct["decision"].lower()
    flags = []
    if "sure" in text or "no-brainer" in text:
        flags.append("overconfidence")
    if "everyone" in text or "obvious" in text:
        flags.append("social-proof")
    if "short term" in intent_struct.get("stated_goals","").lower():
        flags.append("present_bias")
    optimism_keywords = ["fast", "quick", "easy", "low cost", "scale quickly", "no risk", "no-brainer"]
    if any(k in text for k in optimism_keywords):
        flags.append("optimism_bias")
    return {"bias_flags": list(set(flags)) or ["no_strong_bias_detected"], "explanations": [f"Detected {f}" for f in flags]}

def counterargument_generator(intent_struct, bias_info):
    decision = intent_struct["decision"]
    if USE_OPENAI:
        try:
            prompt = f"Act as a constructive devil's advocate. Provide 3 concise counterarguments to the decision: {decision}. Be specific about what could go wrong and propose risk-mitigation alternatives."
            resp = openai.Completion.create(engine="text-davinci-003", prompt=prompt, max_tokens=300)
            text = resp.choices[0].text.strip()
            parts = [p.strip("- ").strip() for p in text.splitlines() if p.strip()]
            return {"counterarguments": parts[:3]}
        except Exception:
            pass
    c1 = f"Factual: Market adoption for Product X may be slower than expected due to existing competitors and required integrations."
    c2 = f"Long-term: Launching now could lock resources and reduce ability to pivot if early signals are negative."
    c3 = f"Skeptical: Projections assume 30% conversion—if conversion is half, ROI turns negative in year 1."
    return {"counterarguments": [c1, c2, c3]}

def second_order_impact_agent(intent_struct):
    impacts = [
        {"area":"Revenue", "scenario":"Best case", "impact":"+20% over 12 months"},
        {"area":"Revenue", "scenario":"Realistic", "impact":"+2% over 12 months"},
        {"area":"Reputation", "scenario":"If failure occurs", "impact":"Negative press, client churn risk"},
        {"area":"Operational", "scenario":"Integration delays", "impact":"2-4 weeks delay, extra cost $150k"}
    ]
    return {"impacts": impacts}

def de_risk_recommendations(counterargs, impacts):
    recs = [
        "Run a 6-week pilot with 2 key clients to validate assumptions before full launch.",
        "Define go/no-go criteria tied to conversion and retention metrics.",
        "Allocate a contingency budget and maintain option to rollback marketing spend."
    ]
    return {"recommendations": recs}

def run_pipeline(decision_text, context=""):
    intent = intent_decoder(decision_text, context)
    bias = bias_detector(intent)
    counters = counterargument_generator(intent, bias)
    impacts = second_order_impact_agent(intent)
    recs = de_risk_recommendations(counters, impacts)
    return {"intent": intent, "bias": bias, "counterarguments": counters, "impacts": impacts, "recommendations": recs}

# --- Streamlit UI ---
import streamlit as st
st.set_page_config(page_title="AI That Disagrees - POC", layout="wide")
st.title("AI That Disagrees With You (Intelligently) — POC")
st.write("Constructive devil's advocate agentic demo. Enter a decision, and the system will challenge it. (Mock mode)")

with st.form("decision_form"):
    decision_text = st.text_area("Enter a decision (one paragraph)", value="We should launch Product X in 3 months; it's a no-brainer and will capture market share quickly. Let's push marketing spend ASAP and scale integrations.", height=150)
    context_text = st.text_area("Optional context (constraints, goals, timeframe)", value="Budget limited to $500k; priority: growth", height=80)
    submitted = st.form_submit_button("Run AI Disagreement")

if submitted:
    with st.spinner("Running agents..."):
        result = run_pipeline(decision_text, context_text)
    # Layout results
    col1, col2 = st.columns([2,1])
    with col1:
        st.subheader("Original Decision")
        st.write(result["intent"]["decision"])
        st.subheader("Structured Intent")
        st.json(result["intent"])
        st.subheader("Counterarguments (Devil's Advocate)")
        for i,c in enumerate(result["counterarguments"]["counterarguments"],1):
            st.markdown(f"**{i}.** {c}")
        st.subheader("De-risk Recommendations")
        for r in result["recommendations"]["recommendations"]:
            st.markdown(f"- {r}")
    with col2:
        st.subheader("Bias Detection")
        st.write(", ".join(result["bias"]["bias_flags"]))
        for e in result["bias"]["explanations"]:
            st.caption(e)
        st.subheader("Second-Order Impacts (summary)")
        for imp in result["impacts"]["impacts"]:
            st.markdown(f"- **{imp['area']}** ({imp['scenario']}) → {imp['impact']}")
    st.success("Done. Use the recommendations to adjust the decision or run again with altered assumptions.")
\"\"\"

# Write the file out
