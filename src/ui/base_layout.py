import streamlit as st


def style_background_home():
    st.markdown("""
        <style>
        .stApp { background: #0F172A !important; }

        /* Home portal cards */
        section[data-testid="stMain"] [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
            background: rgba(255,255,255,0.05) !important;
            border: 1px solid rgba(255,255,255,0.1) !important;
            border-radius: 1.25rem !important;
            padding: 2rem !important;
            transition: background 0.2s ease, border-color 0.2s ease !important;
        }
        section[data-testid="stMain"] [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:hover {
            background: rgba(37,99,235,0.12) !important;
            border-color: rgba(37,99,235,0.4) !important;
        }
        </style>
    """, unsafe_allow_html=True)


def style_background_dashboard():
    st.markdown("""
        <style>
        .stApp { background: #0F172A !important; }
        </style>
    """, unsafe_allow_html=True)


def style_base_layout():
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

        /* ── Reset ───────────────────────────── */
        #MainMenu, footer, header { visibility: hidden; }
        .block-container { padding-top: 1.5rem !important; max-width: 1080px !important; }
        * { font-family: 'Inter', sans-serif !important; }

        /* ── Animations ─────────────────────── */
        @keyframes fadeSlideUp {
            from { opacity: 0; transform: translateY(16px); }
            to   { opacity: 1; transform: translateY(0); }
        }
        @keyframes fadeIn {
            from { opacity: 0; }
            to   { opacity: 1; }
        }
        .main .block-container { animation: fadeIn 0.3s ease both; }

        /* ── Typography ─────────────────────── */
        h1 {
            font-size: 2.1rem !important; font-weight: 800 !important;
            letter-spacing: -0.025em !important; line-height: 1.2 !important;
            color: #F1F5F9 !important; margin-bottom: 0.15rem !important;
        }
        h2 {
            font-size: 1.45rem !important; font-weight: 700 !important;
            letter-spacing: -0.015em !important; color: #F1F5F9 !important;
            margin-bottom: 0.1rem !important;
        }
        h3 {
            font-size: 1.05rem !important; font-weight: 600 !important;
            color: #E2E8F0 !important; margin-bottom: 0.1rem !important;
        }
        p, label, .stMarkdown p { font-size: 0.9rem !important; line-height: 1.6 !important; }

        /* ── Primary button ─────────────────── */
        button[kind="primary"] {
            background: #2563EB !important;
            color: #ffffff !important;
            border: none !important;
            border-radius: 0.55rem !important;
            font-weight: 600 !important;
            font-size: 0.875rem !important;
            padding: 0.58rem 1.2rem !important;
            box-shadow: 0 2px 8px rgba(37,99,235,0.35) !important;
            transition: background 0.15s, transform 0.15s, box-shadow 0.15s !important;
        }
        button[kind="primary"]:hover {
            background: #1D4ED8 !important;
            transform: translateY(-2px) !important;
            box-shadow: 0 6px 20px rgba(37,99,235,0.5) !important;
        }
        button[kind="primary"]:active { transform: translateY(0) !important; }

        /* ── Secondary button ───────────────── */
        button[kind="secondary"] {
            background: #1E293B !important;
            color: #CBD5E1 !important;
            border: 1.5px solid #334155 !important;
            border-radius: 0.55rem !important;
            font-weight: 500 !important;
            font-size: 0.875rem !important;
            padding: 0.58rem 1.2rem !important;
            transition: border-color 0.15s, color 0.15s, transform 0.15s !important;
        }
        button[kind="secondary"]:hover {
            border-color: #2563EB !important;
            color: #93C5FD !important;
            transform: translateY(-1px) !important;
        }

        /* ── Tertiary button ────────────────── */
        button[kind="tertiary"] {
            background: transparent !important;
            color: #64748B !important;
            border: 1.5px solid #334155 !important;
            border-radius: 0.55rem !important;
            font-weight: 500 !important;
            font-size: 0.875rem !important;
            padding: 0.58rem 1.2rem !important;
            transition: all 0.15s !important;
        }
        button[kind="tertiary"]:hover {
            color: #F87171 !important;
            border-color: #7F1D1D !important;
            background: rgba(239,68,68,0.08) !important;
        }

        /* ── Text inputs ────────────────────── */
        [data-testid="stTextInput"] input {
            background: #1E293B !important;
            border: 1.5px solid #334155 !important;
            border-radius: 0.55rem !important;
            color: #F1F5F9 !important;
            font-size: 0.9rem !important;
            padding: 0.55rem 0.85rem !important;
            transition: border-color 0.15s, box-shadow 0.15s !important;
        }
        [data-testid="stTextInput"] input::placeholder { color: #475569 !important; }
        [data-testid="stTextInput"] input:focus {
            border-color: #2563EB !important;
            box-shadow: 0 0 0 3px rgba(37,99,235,0.2) !important;
            outline: none !important;
        }
        [data-testid="stTextInput"] label,
        [data-testid="stSelectbox"] label,
        [data-testid="stFileUploader"] label {
            color: #94A3B8 !important;
            font-size: 0.8rem !important;
            font-weight: 600 !important;
            letter-spacing: 0.04em !important;
            text-transform: uppercase !important;
        }

        /* ── Selectbox ──────────────────────── */
        [data-testid="stSelectbox"] > div > div {
            background: #1E293B !important;
            border: 1.5px solid #334155 !important;
            border-radius: 0.55rem !important;
            color: #F1F5F9 !important;
        }

        /* ── Divider ─────────────────────────── */
        hr { border: none !important; border-top: 1px solid #1E293B !important; margin: 0.85rem 0 !important; }

        /* ── Containers / cards ─────────────── */
        [data-testid="stVerticalBlockBorderWrapper"] {
            background: #1E293B !important;
            border: 1px solid #334155 !important;
            border-radius: 1rem !important;
            box-shadow: 0 2px 12px rgba(0,0,0,0.25) !important;
        }

        /* ── Alerts ──────────────────────────── */
        [data-testid="stAlert"] { border-radius: 0.6rem !important; font-size: 0.875rem !important; }

        /* ── Toast ───────────────────────────── */
        [data-testid="stToast"] { border-radius: 0.75rem !important; background: #1E293B !important; color: #F1F5F9 !important; }

        /* ── Dataframe ───────────────────────── */
        [data-testid="stDataFrame"] { border-radius: 0.75rem !important; overflow: hidden !important; }

        /* ── Camera ──────────────────────────── */
        [data-testid="stCameraInput"] video,
        [data-testid="stCameraInput"] img { border-radius: 0.65rem !important; }

        /* ── Spinner ─────────────────────────── */
        [data-testid="stSpinner"] p { color: #60A5FA !important; font-size: 0.85rem !important; }
        </style>
    """, unsafe_allow_html=True)
