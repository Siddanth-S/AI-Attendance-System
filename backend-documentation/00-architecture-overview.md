# Architecture Overview

## What Kind of Application Is This?

This is a **Streamlit application**. Streamlit is a Python framework that runs a web server entirely in Python — there is no separate frontend build, no REST API, no Express/FastAPI server. Every Python file is both the UI layer and the backend logic simultaneously.

**Critical mental model**: When a user clicks a button in Streamlit, the entire Python script re-runs from top to bottom. State is preserved across re-runs using `st.session_state`. All computation happens server-side.

---

## Directory Structure and Why Each Folder Exists

```
app.py                         ← Single entry point. Boots the app, handles routing.
requirements.txt               ← All Python dependencies
.streamlit/
  secrets.toml                 ← Environment variables (Supabase credentials)
  config.toml                  ← Streamlit theme configuration

src/
  database/
    config.py                  ← Creates and exports the Supabase client (singleton)
    db.py                      ← ALL database read/write operations live here

  pipelines/
    face_pipeline.py           ← Face detection + recognition ML pipeline
    voice_pipeline.py          ← Voice speaker identification pipeline

  screens/
    home_screen.py             ← Landing page (choose Student or Teacher)
    student_screen.py          ← Student login, registration, dashboard
    teacher_screen.py          ← Teacher login, registration, dashboard + all tabs

  components/
    dialog_add_photo.py        ← Modal: add classroom photos for face attendance
    dialog_attendance_results.py ← Modal: review + confirm attendance before saving
    dialog_auto_enroll.py      ← Modal: auto-enroll via QR code deep link
    dialog_create_subject.py   ← Modal: teacher creates a new subject
    dialog_enroll.py           ← Modal: student manually enters join code
    dialog_share_subject.py    ← Modal: generate QR code + share link for a subject
    dialog_voice_attendance.py ← Modal: record classroom audio for voice attendance
    footer.py                  ← Footer HTML component
    header.py                  ← Logo + brand header component
    subject_card.py            ← Subject info card with stats

  ui/
    base_layout.py             ← Global CSS injected on every page (no logic)
```

---

## Layered Architecture (Informal)

```
┌─────────────────────────────────────────────────────┐
│                    app.py                           │  ← Router
├──────────────────┬──────────────────────────────────┤
│  screens/        │  components/dialogs/             │  ← Business Logic + UI
├──────────────────┴──────────────────────────────────┤
│         pipelines/ (face + voice ML)                │  ← ML Processing Layer
├─────────────────────────────────────────────────────┤
│              database/db.py                         │  ← Data Access Layer
├─────────────────────────────────────────────────────┤
│           database/config.py (Supabase)             │  ← Database Connection
└─────────────────────────────────────────────────────┘
```

---

## Routing — How Pages Are Selected

The app uses `st.session_state['login_type']` as a **state machine router**. There are no URL routes or HTTP endpoints.

```python
# app.py
match st.session_state['login_type']:
    case 'teacher':  → teacher_screen()
    case 'student':  → student_screen()
    case None:       → home_screen()
```

Additional state variables drill deeper:

| State Variable | Values | Controls |
|---|---|---|
| `login_type` | `None`, `'student'`, `'teacher'` | Which top-level screen renders |
| `teacher_login_type` | `'login'`, `'register'` | Teacher: login form vs register form |
| `student_mode` | `'login'`, `'register'` | Student: login mode vs register mode |
| `teacher_data` | dict or absent | If present → teacher dashboard renders |
| `student_data` | dict or absent | If present → student dashboard renders |
| `current_teacher_tab` | `'take_attendance'`, `'manage_subjects'`, `'attendance_records'` | Active tab in teacher dashboard |

---

## External Services and Libraries

| Library | Purpose | Where Used |
|---|---|---|
| `supabase-py` | PostgreSQL BaaS — all persistent storage | `database/config.py`, `database/db.py`, dialogs |
| `dlib` | Face detection (HOG) + 128-dim face embedding | `pipelines/face_pipeline.py` |
| `face_recognition_models` | Pre-trained model files for dlib | `pipelines/face_pipeline.py` |
| `scikit-learn SVC` | Classify face embeddings → student identity | `pipelines/face_pipeline.py` |
| `resemblyzer` | 256-dim voice speaker embedding (GE2E model) | `pipelines/voice_pipeline.py` |
| `librosa` | Audio loading + voice activity detection | `pipelines/voice_pipeline.py` |
| `bcrypt` | Password hashing for teacher accounts | `database/db.py` |
| `segno` | QR code generation for subject share links | `components/dialog_share_subject.py` |
| `Pillow` | Open images from camera/upload into numpy arrays | `screens/`, `components/dialog_add_photo.py` |
| `numpy` | Numerical ops: embedding arrays, Euclidean distance | Both pipelines |
| `pandas` | Build DataFrames for attendance result tables | `screens/teacher_screen.py`, dialogs |

---

## Environment Variables

Only two secrets exist, both in `.streamlit/secrets.toml`:

| Variable | Value | Consumed In |
|---|---|---|
| `SUPABASE_URL` | Supabase project URL | `database/config.py` via `st.secrets["SUPABASE_URL"]` |
| `SUPABASE_KEY` | Supabase anon/service key (JWT) | `database/config.py` via `st.secrets["SUPABASE_KEY"]` |

`st.secrets` is Streamlit's built-in secrets manager — it reads from `.streamlit/secrets.toml` locally and from Streamlit Cloud's secrets panel when deployed.

---

## Session State — The App's Memory

Since Streamlit re-runs the entire script on every user interaction, `st.session_state` is the only way to persist data between interactions. Think of it as an in-memory dictionary scoped to one browser session.

Key session state variables and their lifecycle:

```
login_type          Set by home_screen buttons. Cleared on "Back to Home".
teacher_data        Set by teacher_login(). Deleted on logout.
student_data        Set by face recognition or registration. Deleted on logout.
student_mode        'login'|'register'. Reset to 'login' on back/logout.
teacher_login_type  'login'|'register'. Toggles teacher auth forms.
current_teacher_tab Active tab name. Persists during teacher session.
attendance_images   List of PIL Images accumulated for face scan.
voice_attendance_results  (DataFrame, logs) tuple from voice scan.
```
