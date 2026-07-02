import streamlit as st


def header_home():
    st.markdown("""
        <div style="text-align:center; padding: 2.5rem 0 1.5rem 0;">
            <div style="display:inline-flex; align-items:center; gap:12px; margin-bottom:12px;">
                <div style="width:46px; height:46px; background:#2563EB; border-radius:10px;
                            display:flex; align-items:center; justify-content:center;">
                    <span style="font-size:1.5rem; color:white;">✓</span>
                </div>
                <span style="font-size:2rem; font-weight:800; color:white; letter-spacing:-0.02em;">RollCall</span>
            </div>
            <p style="color:rgba(255,255,255,0.5); font-size:0.9rem; margin:0; font-weight:400;">
                Simple, fast attendance for every classroom
            </p>
        </div>
    """, unsafe_allow_html=True)


def header_dashboard():
    st.markdown("""
        <div style="display:inline-flex; align-items:center; gap:10px; padding: 0.25rem 0;">
            <div style="width:34px; height:34px; background:#2563EB; border-radius:8px;
                        display:flex; align-items:center; justify-content:center;">
                <span style="font-size:1rem; color:white;">✓</span>
            </div>
            <span style="font-size:1.35rem; font-weight:800; color:#F1F5F9; letter-spacing:-0.02em;">RollCall</span>
        </div>
    """, unsafe_allow_html=True)
