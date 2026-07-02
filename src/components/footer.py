import streamlit as st


def footer_home():
    st.markdown("""
        <div style="margin-top: 3rem; text-align:center;">
            <p style="color: rgba(255,255,255,0.25); font-size:0.78rem; margin:0;">
                © 2025 RollCall
            </p>
        </div>
    """, unsafe_allow_html=True)


def footer_dashboard():
    st.markdown("""
        <div style="margin-top: 3rem; text-align:center; padding-bottom: 1rem;">
            <p style="color: #475569; font-size:0.78rem; margin:0;">
                © 2025 RollCall
            </p>
        </div>
    """, unsafe_allow_html=True)
