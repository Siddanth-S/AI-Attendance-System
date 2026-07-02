import streamlit as st

from src.ui.base_layout import style_background_dashboard, style_base_layout
from src.components.header import header_dashboard
from src.components.footer import footer_dashboard
from PIL import Image
import numpy as np
from src.pipelines.face_pipeline import predict_attendance, get_face_embeddings, train_classifier
from src.pipelines.voice_pipeline import get_voice_embedding
from src.database.db import get_all_students, create_student, get_student_subjects, get_student_attendance, unenroll_student_to_subject
import time

from src.components.dialog_enroll import enroll_dialog
from src.components.subject_card import subject_card


def student_dashboard():
    student_data = st.session_state.student_data
    student_id = student_data['student_id']

    c1, c2 = st.columns([2, 1], vertical_alignment='center', gap='large')
    with c1:
        header_dashboard()
    with c2:
        st.markdown(f"""
            <div style="display:flex; align-items:center; justify-content:flex-end; gap:0.6rem;">
                <div style="background:rgba(37,99,235,0.15); border-radius:999px; padding:0.3rem 0.9rem;
                            font-size:0.85rem; font-weight:600; color:#93C5FD;">
                    🎓 {student_data['name']}
                </div>
            </div>
        """, unsafe_allow_html=True)
        if st.button("Logout", type='secondary', key='loginbackbtn'):
            st.session_state['is_logged_in'] = False
            st.session_state['student_mode'] = 'login'
            del st.session_state.student_data
            st.rerun()

    st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)

    c1, c2 = st.columns([2, 1], vertical_alignment='center')
    with c1:
        st.markdown("""
            <h2 style="color:#F1F5F9; margin-bottom:0.1rem;">My Subjects</h2>
            <p style="color:#64748B; margin-top:0; margin-bottom:0.5rem;">Your enrolled courses and attendance stats.</p>
        """, unsafe_allow_html=True)
    with c2:
        if st.button('+ Enroll in Subject', type='primary', width='stretch'):
            enroll_dialog()

    st.divider()

    with st.spinner('Loading subjects...'):
        subjects = get_student_subjects(student_id)
        logs = get_student_attendance(student_id)

    stats_map = {}
    for log in logs:
        sid = log['subject_id']
        if sid not in stats_map:
            stats_map[sid] = {"total": 0, "attended": 0}
        stats_map[sid]['total'] += 1
        if log.get('is_present'):
            stats_map[sid]['attended'] += 1

    if not subjects:
        st.markdown("""
            <div style="background:#1E293B; border:1.5px dashed #334155; border-radius:1rem;
                        padding:2rem; text-align:center; margin-top:1rem;">
                <p style="color:#94A3B8; font-size:0.95rem; margin:0;">
                    You haven't enrolled in any subjects yet. Ask your teacher for a join code.
                </p>
            </div>
        """, unsafe_allow_html=True)
    else:
        cols = st.columns(2)
        for i, sub_node in enumerate(subjects):
            sub = sub_node['subjects']
            sid = sub['subject_id']
            stats = stats_map.get(sid, {"total": 0, "attended": 0})

            attended = stats['attended']
            total = stats['total']
            pct = int((attended / total * 100)) if total > 0 else 0
            pct_color = "#10B981" if pct >= 75 else "#F59E0B" if pct >= 50 else "#EF4444"

            def unenroll_button(s=sub, sid=sid):
                if st.button(f"Unenroll from {s['name']}", key=f"unenroll_{sid}",
                             type='tertiary'):
                    unenroll_student_to_subject(student_id, sid)
                    st.toast(f"Unenrolled from {s['name']}")
                    st.rerun()

            pct_emoji = '🟢' if pct >= 75 else '🟡' if pct >= 50 else '🔴'

            with cols[i % 2]:
                subject_card(
                    name=sub['name'],
                    code=sub['subject_code'],
                    section=sub['section'],
                    stats=[
                        ('📅', 'Classes', total),
                        ('✅', 'Attended', attended),
                        (pct_emoji, 'Rate', f'{pct}%'),
                    ],
                    footer_callback=unenroll_button
                )

    footer_dashboard()


def student_screen():
    style_background_dashboard()
    style_base_layout()

    if "student_data" in st.session_state:
        student_dashboard()
        return

    c1, c2 = st.columns([2, 1], vertical_alignment='center', gap='large')
    with c1:
        header_dashboard()
    with c2:
        if st.button("← Back to Home", type='secondary', key='loginbackbtn'):
            st.session_state['login_type'] = None
            st.session_state['student_mode'] = 'login'
            st.rerun()

    # Toggle between login and register mode
    if 'student_mode' not in st.session_state:
        st.session_state.student_mode = 'login'

    col_title, col_toggle = st.columns([2, 1], vertical_alignment='center')
    with col_title:
        st.markdown("""
            <div style="margin-top:2rem; margin-bottom:1rem;">
                <h2 style="color:#F1F5F9; margin:0;">Student Login</h2>
                <p style="color:#64748B; margin:0.25rem 0 0 0;">
                    Look at the camera — RollCall will recognize you automatically.
                </p>
            </div>
        """, unsafe_allow_html=True)
    with col_toggle:
        st.markdown("<div style='height:2rem'></div>", unsafe_allow_html=True)
        if st.session_state.student_mode == 'login':
            if st.button("✨ New student? Register", type='secondary', width='stretch'):
                st.session_state.student_mode = 'register'
                st.rerun()
        else:
            if st.button("← Back to Login", type='secondary', width='stretch'):
                st.session_state.student_mode = 'login'
                st.rerun()

    photo_source = st.camera_input(
        "Take a photo to log in" if st.session_state.student_mode == 'login'
        else "Take a photo to register your face"
    )

    show_registration = st.session_state.student_mode == 'register'

    if photo_source and st.session_state.student_mode == 'login':
        img = np.array(Image.open(photo_source))
        with st.spinner('Scanning your face...'):
            detected, all_ids, num_faces = predict_attendance(img)

            if num_faces == 0:
                st.warning('No face detected. Please try again in better lighting.')
            elif num_faces > 1:
                st.warning('Multiple faces detected. Only one student at a time.')
            else:
                if detected:
                    student_id = list(detected.keys())[0]
                    all_students = get_all_students()
                    student = next((s for s in all_students if s['student_id'] == student_id), None)
                    if student:
                        st.session_state.is_logged_in = True
                        st.session_state.user_role = 'student'
                        st.session_state.student_data = student
                        st.toast(f"Welcome back, {student['name']}!", icon="👋")
                        time.sleep(1)
                        st.rerun()
                else:
                    st.info("Face not recognized. Switch to Register mode using the button above.")

    if show_registration:
        st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
        if not photo_source:
            st.markdown("""
                <div style="background:rgba(37,99,235,0.12); border:1px solid rgba(37,99,235,0.3);
                            border-radius:0.75rem; padding:0.9rem 1.1rem; margin-bottom:0.75rem;">
                    <p style="color:#93C5FD; margin:0; font-size:0.875rem;">
                        📸 Take a photo above first — it will be used to identify you in future sessions.
                    </p>
                </div>
            """, unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown("""
                <h3 style="color:#F1F5F9; margin-top:0;">Create your profile</h3>
                <p style="color:#64748B; font-size:0.85rem; margin-top:-0.5rem;">
                    Fill in your details below. Make sure your face is visible in the photo above.
                </p>
            """, unsafe_allow_html=True)

            new_name = st.text_input("Full Name", placeholder='e.g. Hamza Rizvi')

            st.markdown("""
                <p style="font-weight:600; color:#F1F5F9; margin-bottom:0.2rem;">
                    Voice Enrollment <span style="font-weight:400; color:#94A3B8;">(optional)</span>
                </p>
                <p style="color:#64748B; font-size:0.82rem; margin-top:0;">
                    Record yourself saying "I am present" to enable voice-based attendance.
                </p>
            """, unsafe_allow_html=True)

            audio_data = None
            try:
                audio_data = st.audio_input('Record a short phrase')
            except Exception:
                st.caption('Audio input unavailable on this device.')

            if st.button('Create Account', type='primary', width='stretch'):
                if not photo_source:
                    st.warning('Please take a photo first so RollCall can recognize you.')
                elif not new_name:
                    st.warning('Please enter your full name.')
                else:
                    with st.spinner('Setting up your profile...'):
                        img = np.array(Image.open(photo_source))
                        encodings = get_face_embeddings(img)
                        if encodings:
                            face_emb = encodings[0].tolist()
                            voice_emb = None
                            if audio_data:
                                voice_emb = get_voice_embedding(audio_data.read())
                            response_data = create_student(new_name, face_embedding=face_emb, voice_embedding=voice_emb)
                            if response_data:
                                train_classifier()
                                st.session_state.is_logged_in = True
                                st.session_state.user_role = 'student'
                                st.session_state.student_data = response_data[0]
                                st.toast(f"Welcome to RollCall, {new_name}!", icon="🎉")
                                time.sleep(1)
                                st.rerun()
                        else:
                            st.error("Couldn't capture facial features. Try retaking the photo.")

    footer_dashboard()
