import streamlit as st
from src.components.header import header_home
from src.components.footer import footer_home
from src.ui.base_layout import style_base_layout, style_background_home


def home_screen():
    style_background_home()
    style_base_layout()

    # Extra home-specific styles
    st.markdown("""
        <style>
        /* Force indigo on ALL buttons on this page */
        .stApp button, .stApp button[kind="primary"],
        .stApp button[kind="secondary"], .stApp button[kind="tertiary"],
        .stApp [data-testid="stBaseButton-primary"] button,
        .stApp [data-testid="stBaseButton-secondary"] button {
            background: #2563EB !important;
            color: white !important;
            border: none !important;
            box-shadow: 0 4px 18px rgba(37,99,235,0.4) !important;
            font-weight: 600 !important;
            transition: all 0.2s ease !important;
        }
        .stApp button:hover {
            background: #1D4ED8 !important;
            transform: translateY(-2px) !important;
            box-shadow: 0 6px 24px rgba(37,99,235,0.55) !important;
        }
        /* Back to home button: make it subtle */
        .stApp [data-testid="stBaseButton-secondary"] button {
            background: rgba(255,255,255,0.1) !important;
            border: 1px solid rgba(255,255,255,0.2) !important;
            box-shadow: none !important;
        }
        /* Home heading colors override to white */
        .stApp h2 { color: white !important; }
        </style>
    """, unsafe_allow_html=True)

    header_home()

    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

    col1, col2 = st.columns(2, gap="large")

    with col1:
        st.markdown("""
            <div style="margin-bottom:1rem; animation: fadeSlideUp 0.4s ease 0.1s both;">
                <div style="font-size:2.5rem; margin-bottom:0.6rem;">🎓</div>
                <h2 style="color:white !important; margin:0; font-size:1.25rem; font-weight:700;">
                    Student Portal
                </h2>
                <p style="color:rgba(255,255,255,0.5); font-size:0.82rem; margin:0.4rem 0 1.2rem 0; line-height:1.5;">
                    View your attendance · Enroll in subjects · Check in quickly
                </p>
            </div>
        """, unsafe_allow_html=True)
        if st.button('Enter as Student →', type='primary', width='stretch'):
            st.session_state['login_type'] = 'student'
            st.rerun()

    with col2:
        st.markdown("""
            <div style="margin-bottom:1rem; animation: fadeSlideUp 0.4s ease 0.2s both;">
                <div style="font-size:2.5rem; margin-bottom:0.6rem;">🧑‍🏫</div>
                <h2 style="color:white !important; margin:0; font-size:1.25rem; font-weight:700;">
                    Teacher Portal
                </h2>
                <p style="color:rgba(255,255,255,0.5); font-size:0.82rem; margin:0.4rem 0 1.2rem 0; line-height:1.5;">
                    Take attendance · Manage subjects · View records
                </p>
            </div>
        """, unsafe_allow_html=True)
        if st.button('Enter as Teacher →', type='primary', width='stretch'):
            st.session_state['login_type'] = 'teacher'
            st.rerun()

    footer_home()
