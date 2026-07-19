import streamlit as st
from dotenv import load_dotenv
from backend import search_and_answer   # ← you write this

load_dotenv()

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="FIFA Referee AI",
    page_icon="⚽",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* ---- Global ---- */
html, body, [data-testid="stAppViewContainer"] {
    background-color: #0f1117;
    color: #f0f0f0;
}

[data-testid="stHeader"] { background: transparent; }

/* ---- Header ---- */
.app-header {
    text-align: center;
    padding: 2rem 0 1.5rem 0;
}
.app-header h1 {
    font-size: 2.4rem;
    font-weight: 800;
    color: #ffffff;
    margin-bottom: 0.3rem;
    letter-spacing: -0.5px;
}
.app-header p {
    color: #9ca3af;
    font-size: 1rem;
    margin: 0;
}

/* ---- Divider ---- */
.divider {
    border: none;
    border-top: 1px solid #1f2937;
    margin: 1.5rem 0;
}

/* ---- Input label ---- */
.input-label {
    font-size: 0.85rem;
    font-weight: 600;
    color: #9ca3af;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 0.4rem;
}

/* ---- Streamlit textarea override ---- */
textarea {
    background-color: #1a1d27 !important;
    border: 1px solid #2d3748 !important;
    border-radius: 10px !important;
    color: #f0f0f0 !important;
    font-size: 0.97rem !important;
}
textarea:focus {
    border-color: #22c55e !important;
    box-shadow: 0 0 0 2px rgba(34,197,94,0.15) !important;
}

/* ---- Analyze button ---- */
div[data-testid="stButton"] > button {
    width: 100%;
    background-color: #22c55e;
    color: #000;
    font-weight: 700;
    font-size: 0.95rem;
    border: none;
    border-radius: 10px;
    padding: 0.65rem 1.5rem;
    transition: background 0.2s;
}
div[data-testid="stButton"] > button:hover {
    background-color: #16a34a;
    color: #fff;
}

/* ---- Result cards ---- */
.result-card {
    background: #1a1d27;
    border: 1px solid #2d3748;
    border-radius: 12px;
    padding: 1.1rem 1.3rem;
    margin-bottom: 0.8rem;
}
.result-card-header {
    font-size: 0.75rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #6b7280;
    margin-bottom: 0.4rem;
}
.result-card-value {
    font-size: 1rem;
    font-weight: 600;
    color: #f9fafb;
    line-height: 1.4;
}

/* Law badge */
.law-badge {
    display: inline-block;
    background: rgba(34,197,94,0.12);
    border: 1px solid rgba(34,197,94,0.35);
    color: #4ade80;
    font-size: 0.82rem;
    font-weight: 700;
    border-radius: 6px;
    padding: 0.2rem 0.65rem;
    margin-bottom: 0.8rem;
}

/* Decision badge */
.decision-badge {
    display: inline-block;
    background: rgba(251,191,36,0.1);
    border: 1px solid rgba(251,191,36,0.3);
    color: #fbbf24;
    font-size: 0.82rem;
    font-weight: 700;
    border-radius: 6px;
    padding: 0.2rem 0.65rem;
    margin-bottom: 0.8rem;
}

/* Explanation block */
.explanation-block {
    background: #1a1d27;
    border-left: 3px solid #22c55e;
    border-radius: 0 10px 10px 0;
    padding: 1rem 1.2rem;
    color: #d1d5db;
    font-size: 0.97rem;
    line-height: 1.7;
    margin-bottom: 0.8rem;
}

/* Source block */
.source-block {
    background: #111318;
    border: 1px solid #1f2937;
    border-radius: 10px;
    padding: 0.9rem 1.1rem;
    font-size: 0.83rem;
    color: #6b7280;
    font-style: italic;
    line-height: 1.6;
}
.source-block span {
    color: #9ca3af;
    font-style: normal;
    font-weight: 600;
}

/* ---- Example pills ---- */
.example-pill {
    display: inline-block;
    background: #1a1d27;
    border: 1px solid #2d3748;
    border-radius: 20px;
    padding: 0.3rem 0.8rem;
    font-size: 0.8rem;
    color: #9ca3af;
    cursor: pointer;
    margin: 0.2rem;
    transition: border-color 0.15s;
}
.example-pill:hover { border-color: #22c55e; color: #4ade80; }

/* ---- Spinner override ---- */
[data-testid="stSpinner"] { color: #22c55e !important; }
</style>
""", unsafe_allow_html=True)

# ── Header ─────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="app-header">
    <h1>⚽ FIFA Referee AI</h1>
    <p>Describe any football situation and get the official ruling and explanation.</p>
</div>
<hr class="divider"/>
""", unsafe_allow_html=True)

# ── Session state ──────────────────────────────────────────────────────────────
if "result" not in st.session_state:
    st.session_state.result = None
if "situation" not in st.session_state:
    st.session_state.situation = ""

# ── Example situations ─────────────────────────────────────────────────────────
EXAMPLES = [
    "A player scores directly from a throw-in",
    "The ball hits the referee and goes into the goal during open play",
    "A substitute enters the pitch before the substituted player has left",
    "A goalkeeper drops the ball and picks it up again without an opponent touching it",
]

st.markdown('<p class="input-label">Try an example</p>', unsafe_allow_html=True)

cols = st.columns(2)
for i, example in enumerate(EXAMPLES):
    with cols[i % 2]:
        if st.button(example, key=f"ex_{i}", use_container_width=True):
            st.session_state.situation_input = example
            st.session_state.result = None

st.markdown('<hr class="divider"/>', unsafe_allow_html=True)

# ── Input ──────────────────────────────────────────────────────────────────────
st.markdown('<p class="input-label">Describe the situation</p>', unsafe_allow_html=True)

situation = st.text_area(
    label="situation",
    label_visibility="collapsed",
    value=st.session_state.situation,
    placeholder=(
        "e.g. A striker scored but VAR noticed his teammate was offside "
        "before the assist. Why was the goal cancelled?"
    ),
    height=110,
    key="situation_input",
)

analyze = st.button("Analyze Situation", use_container_width=True)

# ── Run analysis ───────────────────────────────────────────────────────────────
if analyze and situation.strip():
    st.session_state.situation = situation
    with st.spinner("Checking the rulebook…"):
        st.session_state.result = search_and_answer(situation)

# ── Display results ────────────────────────────────────────────────────────────
result = st.session_state.result

if result:
    st.markdown('<hr class="divider"/>', unsafe_allow_html=True)

    # Law + Decision badges
    st.markdown(
        f'<span class="law-badge">📖 {result["law"]}</span>&nbsp;&nbsp;'
        f'<span class="decision-badge">⚡ {result["decision"]}</span>',
        unsafe_allow_html=True,
    )

    # Explanation
    st.markdown(
        f'<div class="explanation-block">{result["explanation"]}</div>',
        unsafe_allow_html=True,
    )

    # Sources
    if result.get("sources"):
        sources_html = "<br>".join(f"· {s}" for s in result["sources"])
        st.markdown(
            f'<div class="source-block"><span>Sources</span><br>{sources_html}</div>',
            unsafe_allow_html=True,
        )


elif analyze and not situation.strip():
    st.warning("Please describe a situation first.")

# ── Footer ─────────────────────────────────────────────────────────────────────
st.markdown('<hr class="divider"/>', unsafe_allow_html=True)
st.markdown(
    '<p style="text-align:center;color:#374151;font-size:0.78rem;">'
    'Powered by FIFA Laws of the Game · MongoDB Atlas Vector Search · Groq'
    '</p>',
    unsafe_allow_html=True,
)
