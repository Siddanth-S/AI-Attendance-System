import streamlit as st


def subject_card(name, code, section, stats=None, footer_callback=None):
    stats_html = ""
    if stats:
        chips = "".join(
            f'<div style="display:flex;flex-direction:column;align-items:center;'
            f'background:#0F172A;border:1px solid #334155;border-radius:0.6rem;'
            f'padding:0.45rem 0.9rem;min-width:64px;">'
            f'<span style="font-size:1rem;">{icon}</span>'
            f'<span style="font-size:0.95rem;font-weight:700;color:#F1F5F9;line-height:1.2;">{value}</span>'
            f'<span style="font-size:0.68rem;color:#64748B;font-weight:500;'
            f'text-transform:uppercase;letter-spacing:0.05em;">{label}</span>'
            f'</div>'
            for icon, label, value in stats
        )
        stats_html = f'<div style="display:flex;gap:0.5rem;flex-wrap:wrap;margin-top:0.75rem;">{chips}</div>'

    html = f"""
    <div style="
        background:#1E293B;
        border-radius:0.9rem;
        border:1px solid #334155;
        border-left:4px solid #2563EB;
        padding:1.15rem 1.4rem 0.6rem 1.4rem;
        margin-bottom:0.9rem;
        box-shadow:0 2px 10px rgba(0,0,0,0.2);
        animation: fadeSlideUp 0.35s ease both;
    ">
        <h3 style="margin:0;color:#F1F5F9;font-size:1rem;font-weight:700;">{name}</h3>
        <div style="display:flex;gap:0.5rem;margin-top:0.3rem;flex-wrap:wrap;align-items:center;">
            <span style="background:rgba(37,99,235,0.2);color:#93C5FD;font-size:0.73rem;
                         font-weight:600;padding:2px 9px;border-radius:999px;">{code}</span>
            <span style="color:#475569;font-size:0.78rem;">Section {section}</span>
        </div>
        {stats_html}
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)

    if footer_callback:
        footer_callback()
