# RollCall — AI-Powered Attendance Tracker

> Simple, fast, biometric attendance for every classroom.

RollCall is a full-stack web application that automates classroom attendance using **face recognition** and **voice identification**. Teachers upload classroom photos or record audio; the AI identifies which enrolled students are present and logs the results to a cloud database — no manual roll calls, no paper sheets.

---

## Table of Contents

1. [What It Does](#what-it-does)
2. [Live Demo](#live-demo)
3. [Tech Stack](#tech-stack)
4. [Architecture Overview](#architecture-overview)
5. [Project Structure](#project-structure)
6. [Database Schema](#database-schema)
7. [Face Recognition Pipeline](#face-recognition-pipeline)
8. [Voice Recognition Pipeline](#voice-recognition-pipeline)
9. [Feature Walkthrough](#feature-walkthrough)
   - [Home Screen](#home-screen)
   - [Teacher Portal](#teacher-portal)
   - [Student Portal](#student-portal)
10. [Session State & Routing](#session-state--routing)
11. [UI System](#ui-system)
12. [Environment Variables & Secrets](#environment-variables--secrets)
13. [Local Setup](#local-setup)
14. [Supabase Table Setup](#supabase-table-setup)
15. [Dependencies Explained](#dependencies-explained)
16. [Known Limitations & Design Notes](#known-limitations--design-notes)

---

## What It Does

| Role | Capabilities |
|---|---|
| **Teacher** | Register / log in with credentials, create subjects, take attendance via face scan (photos) or voice recording (audio), review and confirm results before saving, view historical attendance records, share a QR code join link so students can self-enroll instantly |
| **Student** | Register with a selfie (+ optional voice sample), log in by looking at the camera (no password needed), enroll in subjects via subject code or QR link, view personal attendance percentage per subject with color-coded status |

The core idea: **a teacher photographs the classroom or records the class saying "I am present" — the AI does the rest.**

---

## Live Demo

The app is deployed on Streamlit Community Cloud:

```
https://rollcall-main.streamlit.app
```

Deep-link auto-enrollment (shared by teachers via QR code):

```
https://rollcall-main.streamlit.app/?join-code=CS101
```

When a student opens this link and is logged in, a confirmation dialog auto-fires and enrolls them in that subject immediately.

---

## Tech Stack

| Layer | Technology | Why |
|---|---|---|
| Frontend + Backend | Python + Streamlit | Single-language full-stack: no REST API needed, no build step, all logic runs server-side |
| Database | Supabase (PostgreSQL via PostgREST) | Hosted Postgres with a simple Python client, handles auth-level access control via API keys |
| Face Detection | dlib HOG face detector | Fast CPU-based frontal face detection with proven accuracy |
| Face Landmarks | dlib 68-point shape predictor | Locates eyes, nose, mouth, jawline — required input for the embedding model |
| Face Embedding | dlib ResNet face recognition model | Produces 128-dimensional vectors where same-person faces cluster together |
| Face Classification | scikit-learn SVC (linear kernel) | Classifies a new face embedding into a known student identity |
| Voice Embedding | Resemblyzer GE2E speaker encoder | Produces 256-dimensional speaker vectors where same-voice recordings point in the same direction |
| Audio Processing | librosa | Decodes any audio format, resamples to 16kHz, runs Voice Activity Detection |
| Password Security | bcrypt | Hashes teacher passwords before storing — passwords are never stored in plaintext |
| QR Code Generation | segno | Generates PNG QR codes for subject join links |
| Image Handling | Pillow (PIL) | Opens camera captures and uploaded files into numpy arrays |
| Numerical Computing | NumPy | Embedding arithmetic, Euclidean distance, cosine similarity |
| Data Tables | Pandas | Builds attendance result DataFrames for display and aggregation |
| Typography | Google Fonts — Inter | Clean, modern sans-serif for the dark UI |

---

## Architecture Overview

RollCall is a **pure Python Streamlit application**. There is no separate REST API, no Express server, no frontend build process, and no JavaScript written. Every component — UI rendering, ML inference, business logic, and database calls — runs server-side in Python.

**Critical Streamlit mental model**: When a user clicks a button, the **entire Python script re-runs from the top**. Data that needs to survive between re-runs is stored in `st.session_state` (an in-memory dictionary scoped to one browser session). All ML model loading and database-fetched data is cached using `@st.cache_resource` to avoid re-running expensive operations on every click.

```
┌─────────────────────────────────────────────────────────────┐
│                         app.py                              │
│   Entry point — sets page config, reads session state,      │
│   routes to the correct screen function                     │
├──────────────────────────┬──────────────────────────────────┤
│      src/screens/        │     src/components/dialogs/      │
│  home_screen.py          │  dialog_add_photo.py             │
│  teacher_screen.py       │  dialog_attendance_results.py    │
│  student_screen.py       │  dialog_auto_enroll.py           │
│                          │  dialog_create_subject.py        │
│  Business logic +        │  dialog_enroll.py                │
│  page-level layout       │  dialog_share_subject.py         │
│                          │  dialog_voice_attendance.py      │
│                          │  header.py / footer.py           │
│                          │  subject_card.py                 │
├──────────────────────────┴──────────────────────────────────┤
│              src/pipelines/                                 │
│   face_pipeline.py    — dlib detection + SVC classification │
│   voice_pipeline.py   — Resemblyzer GE2E + cosine match    │
├─────────────────────────────────────────────────────────────┤
│                  src/database/db.py                         │
│   All Supabase read/write operations (Data Access Layer)    │
├─────────────────────────────────────────────────────────────┤
│              src/database/config.py                         │
│   Supabase client singleton — reads credentials from        │
│   st.secrets, creates and exports the client object         │
└─────────────────────────────────────────────────────────────┘
```

---

## Project Structure

```
rollcall/
│
├── app.py                             ← Entry point. Sets Streamlit page config,
│                                        initialises session state, and routes to
│                                        home_screen / teacher_screen / student_screen
│                                        based on st.session_state['login_type'].
│                                        Also handles the ?join-code= query param for
│                                        QR-link auto-enrollment.
│
├── requirements.txt                   ← All Python dependencies (see Dependencies section).
│
├── .streamlit/
│   ├── secrets.toml                   ← SUPABASE_URL and SUPABASE_KEY.
│   │                                    NOT committed to git. Add to Streamlit Cloud
│   │                                    secrets panel when deploying.
│   └── config.toml                    ← Streamlit dark theme configuration.
│                                        Sets primaryColor, backgroundColor,
│                                        secondaryBackgroundColor, textColor.
│
└── src/
    │
    ├── database/
    │   ├── config.py                  ← Creates the Supabase Client singleton using
    │   │                                st.secrets. Imported everywhere that needs DB.
    │   └── db.py                      ← Every database operation lives here.
    │                                    Functions: check_teacher_exists, create_teacher,
    │                                    teacher_login, get_all_students, create_student,
    │                                    create_subject, get_teacher_subjects,
    │                                    enroll_student_to_subject,
    │                                    unenroll_student_to_subject,
    │                                    get_student_subjects, get_student_attendance,
    │                                    create_attendance, get_attendance_for_teacher.
    │                                    Also holds hash_pass() and check_pass()
    │                                    for bcrypt password operations.
    │
    ├── pipelines/
    │   ├── face_pipeline.py           ← Full face recognition pipeline.
    │   │                                load_dlib_models() — cached, loads once.
    │   │                                get_face_embeddings() — image → [128-dim vectors].
    │   │                                get_trained_model() — cached SVC trained on DB.
    │   │                                train_classifier() — clears cache, retrains SVC.
    │   │                                predict_attendance() — image → {student_id: True}.
    │   │
    │   └── voice_pipeline.py          ← Full voice speaker-ID pipeline.
    │                                    load_voice_encoder() — cached GE2E model.
    │                                    get_voice_embedding() — audio bytes → 256-dim vec.
    │                                    identify_speaker() — one embedding vs candidates.
    │                                    process_bulk_audio() — full recording → {sid: score}.
    │
    ├── screens/
    │   ├── home_screen.py             ← Landing page. Two portal cards (Student, Teacher).
    │   │                                Applies home-specific background + CSS overrides.
    │   │
    │   ├── teacher_screen.py          ← Entire teacher experience:
    │   │                                teacher_screen() — top-level router.
    │   │                                teacher_screen_login() — login form.
    │   │                                teacher_screen_register() — register form.
    │   │                                teacher_dashboard() — header, logout, tab buttons.
    │   │                                teacher_tab_take_attendance() — photo/voice flow.
    │   │                                teacher_tab_manage_subjects() — CRUD for subjects.
    │   │                                teacher_tab_attendance_records() — history table.
    │   │
    │   └── student_screen.py          ← Entire student experience:
    │                                    student_screen() — routes login vs dashboard.
    │                                    student_dashboard() — subjects grid + stats.
    │                                    (login/register handled inline in student_screen)
    │
    ├── components/
    │   ├── dialog_add_photo.py        ← @st.dialog modal. Two tabs: Camera (live capture)
    │   │                                and Upload (multi-file). Appends PIL Images to
    │   │                                st.session_state.attendance_images.
    │   │
    │   ├── dialog_attendance_results.py ← show_attendance_result() renders a DataFrame
    │   │                                  with present/absent status + Discard/Confirm buttons.
    │   │                                  attendance_result_dialog() wraps it in @st.dialog.
    │   │                                  On Confirm: calls create_attendance(logs).
    │   │
    │   ├── dialog_auto_enroll.py      ← @st.dialog triggered by ?join-code= query param.
    │   │                                Looks up the subject, checks if already enrolled,
    │   │                                prompts Yes/No, calls enroll_student_to_subject().
    │   │
    │   ├── dialog_create_subject.py   ← @st.dialog. Three fields: code, name, section.
    │   │                                Calls create_subject() on submit.
    │   │
    │   ├── dialog_enroll.py           ← @st.dialog. Student enters a subject code manually.
    │   │                                Validates code exists, checks not already enrolled,
    │   │                                calls enroll_student_to_subject().
    │   │
    │   ├── dialog_share_subject.py    ← @st.dialog. Generates QR code PNG via segno for
    │   │                                the subject's join URL. Two-column layout: copy link
    │   │                                (left) + QR code image (right).
    │   │
    │   ├── dialog_voice_attendance.py ← @st.dialog. Teacher records classroom audio.
    │   │                                On "Analyze Audio": fetches enrolled students' voice
    │   │                                embeddings, calls process_bulk_audio(), builds results
    │   │                                DataFrame, shows show_attendance_result() inline.
    │   │
    │   ├── footer.py                  ← footer_home() and footer_dashboard(). Pure HTML
    │   │                                copyright line, styled differently per context.
    │   │
    │   ├── header.py                  ← header_home() — centered logo + tagline.
    │   │                                header_dashboard() — compact inline logo.
    │   │
    │   └── subject_card.py            ← subject_card(name, code, section, stats, callback).
    │                                    Renders a dark card with blue left-border accent,
    │                                    stat chips (icon + value + label), and an optional
    │                                    Streamlit widget callback for action buttons.
    │
    └── ui/
        └── base_layout.py             ← style_base_layout() injects ~180 lines of CSS
                                         on every page: Inter font, reset rules, animations,
                                         typography, button styles (primary/secondary/tertiary),
                                         input fields, selectboxes, dividers, containers,
                                         alerts, toasts, dataframe, camera input, spinner.
                                         style_background_home() adds glass-card hover effect.
                                         style_background_dashboard() sets dark background.
```

---

## Database Schema

The database is hosted on **Supabase** (PostgreSQL). The `supabase-py` client communicates via PostgREST (a REST layer auto-generated from the database schema). No raw SQL is written in the application code — all queries use the fluent builder API.

### Entity Relationship Diagram

```
teachers ──< subjects ──< subject_students >── students
                │                                   │
                └───────< attendance_logs >──────────┘
```

- One teacher owns many subjects
- One subject has many students through `subject_students` (many-to-many)
- `attendance_logs` records one row per student per attendance session (present OR absent)
- A "session" is not a separate table — it is inferred by grouping `attendance_logs` rows that share the same `timestamp` string

---

### `teachers` table

| Column | Type | Constraints | Description |
|---|---|---|---|
| `teacher_id` | integer | PRIMARY KEY, auto-increment | Internal identifier |
| `username` | text | UNIQUE, NOT NULL | Login identifier |
| `password` | text | NOT NULL | bcrypt hash of the real password |
| `name` | text | NOT NULL | Display name shown in the dashboard header |

---

### `students` table

| Column | Type | Constraints | Description |
|---|---|---|---|
| `student_id` | integer | PRIMARY KEY, auto-increment | Internal identifier |
| `name` | text | NOT NULL | Display name |
| `face_embedding` | JSONB | nullable | 128-float array from dlib ResNet. Serialised as JSON list |
| `voice_embedding` | JSONB | nullable | 256-float array from GE2E encoder. Optional — students can skip voice enrollment |

---

### `subjects` table

| Column | Type | Constraints | Description |
|---|---|---|---|
| `subject_id` | integer | PRIMARY KEY, auto-increment | Internal identifier |
| `subject_code` | text | NOT NULL | e.g. `CS101`. Doubles as the student join code |
| `name` | text | NOT NULL | e.g. `Introduction to Computer Science` |
| `section` | text | NOT NULL | e.g. `A` |
| `teacher_id` | integer | FK → teachers | Owner of this subject |

---

### `subject_students` table

| Column | Type | Constraints | Description |
|---|---|---|---|
| `student_id` | integer | FK → students | |
| `subject_id` | integer | FK → subjects | |

Composite primary key on `(student_id, subject_id)` prevents duplicate enrollments.

---

### `attendance_logs` table

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | integer | PRIMARY KEY, auto-increment | |
| `student_id` | integer | FK → students | |
| `subject_id` | integer | FK → subjects | |
| `timestamp` | text | NOT NULL | ISO 8601 string: `2025-06-01T10:30:00` |
| `is_present` | boolean | NOT NULL | `true` = present, `false` = absent |

**How sessions work**: When a teacher confirms attendance, `create_attendance(logs)` does a bulk INSERT where every row in that batch shares the same `timestamp` string (captured once via `datetime.now()`). `get_teacher_subjects()` later counts unique timestamps to derive `total_classes`.

---

### All Database Functions in `db.py`

| Function | Operation | Table(s) | Notes |
|---|---|---|---|
| `hash_pass(pwd)` | — | — | bcrypt.hashpw, returns string |
| `check_pass(pwd, hashed)` | — | — | bcrypt.checkpw, returns bool |
| `check_teacher_exists(username)` | SELECT | teachers | Returns True if username taken |
| `create_teacher(username, password, name)` | INSERT | teachers | Stores bcrypt hash, not raw password |
| `teacher_login(username, password)` | SELECT | teachers | Fetches row, bcrypt-verifies in Python |
| `get_all_students()` | SELECT * | students | Full table scan — used to train the SVC. All embeddings are returned |
| `create_student(name, face_embedding, voice_embedding)` | INSERT | students | Both embeddings are nullable |
| `create_subject(subject_code, name, section, teacher_id)` | INSERT | subjects | |
| `get_teacher_subjects(teacher_id)` | SELECT + joins | subjects, subject_students, attendance_logs | Nested aggregation: extracts student count and unique-timestamp class count in Python |
| `enroll_student_to_subject(student_id, subject_id)` | INSERT | subject_students | |
| `unenroll_student_to_subject(student_id, subject_id)` | DELETE | subject_students | Deletes row matching both FKs |
| `get_student_subjects(student_id)` | SELECT + join | subject_students, subjects | Returns each enrollment with full subject object nested |
| `get_student_attendance(student_id)` | SELECT + join | attendance_logs, subjects | All logs for the student with subject details |
| `create_attendance(logs)` | BULK INSERT | attendance_logs | `logs` is a list of dicts; one row per enrolled student |
| `get_attendance_for_teacher(teacher_id)` | SELECT + inner join | attendance_logs, subjects | `subjects!inner(*)` filters to only this teacher's subjects |

---

## Face Recognition Pipeline

**File**: `src/pipelines/face_pipeline.py`

The pipeline does two distinct things:
1. **Embedding extraction** — convert a raw image into one or more 128-number vectors representing each detected face
2. **Identity prediction** — given a new face vector, determine which enrolled student it belongs to (or reject it if it doesn't match anyone)

### Pipeline Flow

```
Raw Image (numpy RGB array, H × W × 3)
            │
            ▼
┌─────────────────────────────────────────┐
│  dlib HOG Frontal Face Detector         │  ← Scans the image for face bounding boxes.
│  detector(image_np, upsample=1)         │    upsample=1 improves detection of small faces.
└─────────────────────────────────────────┘
            │  Returns: list of dlib rectangles
            ▼
┌─────────────────────────────────────────┐
│  dlib 68-Point Shape Predictor          │  ← For each bounding box, finds 68 landmark
│  sp(image_np, face_rect)               │    coordinates: eyes, eyebrows, nose, mouth,
└─────────────────────────────────────────┘    chin, jawline.
            │  Returns: shape object (68 2D points)
            ▼
┌─────────────────────────────────────────┐
│  dlib ResNet Face Recognition Model     │  ← Deep neural network. Takes the image +
│  facerec.compute_face_descriptor(       │    landmarks, produces a 128-dimensional
│      image_np, shape, num_jitters=1)    │    float vector. num_jitters=1 averages
└─────────────────────────────────────────┘    over 1 random perturbation for stability.
            │  Returns: dlib vector → converted to np.ndarray shape (128,)
            ▼
┌─────────────────────────────────────────┐
│  scikit-learn SVC (linear kernel)       │  ← Trained on all students' stored embeddings.
│  clf.predict([new_embedding])           │    Classifies the new embedding into the
└─────────────────────────────────────────┘    closest known student_id.
            │  Returns: predicted student_id
            ▼
┌─────────────────────────────────────────┐
│  Euclidean Distance Rejection Gate      │  ← Computes np.linalg.norm(stored - new).
│  threshold = 0.6                        │    If distance > 0.6, the face is too different
└─────────────────────────────────────────┘    from the predicted student — rejected.
            │
            ▼
    {student_id: True}   ← Only confirmed matches are returned
```

---

### `load_dlib_models()` — `face_pipeline.py:13`

**Decorator**: `@st.cache_resource` — this function runs **exactly once** per server process. Results are stored in memory and reused on every subsequent call.

Loads three objects:
- `dlib.get_frontal_face_detector()` — a pre-trained HOG + SVM pipeline that finds face bounding boxes
- `dlib.shape_predictor(...)` — the 68-point facial landmark model, file path from `face_recognition_models` package
- `dlib.face_recognition_model_v1(...)` — a ResNet-34 architecture trained with metric learning to produce 128-dim embeddings

**Why cache?** The three dlib model files total approximately 100MB. Loading them from disk takes 2–5 seconds. Without caching, every user interaction would trigger a reload.

---

### `get_face_embeddings(image_np)` — `face_pipeline.py:27`

**Called from**: `student_screen.py` (student registration), `predict_attendance()`

**Input**: RGB numpy array (any resolution)

**Steps**:
1. Loads dlib models via the cached `load_dlib_models()`
2. `detector(image_np, 1)` — detects face rectangles. `1` = upsample factor, better at small faces
3. For each rectangle:
   - `sp(image_np, face)` — 68 landmark coordinates
   - `facerec.compute_face_descriptor(image_np, shape, 1)` — the last `1` is `num_jitters`, which slightly perturbs the image before computing the embedding and averages the result for robustness
   - Converts dlib vector to `np.ndarray`
4. Returns a list, one 128-dim array per detected face

**Output**: `List[np.ndarray]` — empty list if no faces found

**Why 128 dimensions?** This is the output size of dlib's ResNet face model. The model was trained with a triplet/metric learning objective: same-person faces should be within 0.6 Euclidean distance of each other; different people should be farther than 0.6. 128 dimensions is a sweet spot — compact enough to store and compare cheaply, expressive enough to distinguish individuals.

---

### `get_trained_model()` — `face_pipeline.py:41`

**Decorator**: `@st.cache_resource` — cached until explicitly invalidated by `train_classifier()`

**What it does**: Fetches all students from Supabase, builds training data, fits an SVC.

**Steps**:
1. `get_all_students()` — full table scan, returns all student rows with embeddings
2. Builds `X = [np.array(embedding) for each student]` and `y = [student_id for each student]`
3. Skips students with no `face_embedding` (voice-only or incomplete registrations)
4. Creates `SVC(kernel='linear', probability=True, class_weight='balanced')`:
   - `kernel='linear'` — works excellently in high-dimensional spaces (128 dims). Linear SVMs find a maximum-margin hyperplane separating each class
   - `probability=True` — enables Platt scaling so `predict_proba()` works (not currently used in prediction, but set for potential future use)
   - `class_weight='balanced'` — automatically adjusts weights inversely proportional to class frequency, handling the case where some students might have more training samples than others
5. `clf.fit(X, y)` — trains the classifier

**Returns**:
- `None` — no students in the database at all
- `0` — students exist but none have a face embedding (all skipped)
- `dict` with keys: `'clf'` (trained SVC), `'X'` (training embeddings), `'y'` (training labels)

---

### `train_classifier()` — `face_pipeline.py:70`

**Called from**: `student_screen.py` immediately after every successful student registration

**What it does**:
1. `st.cache_resource.clear()` — clears ALL cached resources across the app
2. Calls `get_trained_model()` which re-fetches students from Supabase and retrains

**Side effect**: Clearing ALL caches also evicts the dlib models, so the next inference call will reload them (one-time ~3 second hit). The reason for clearing everything (not just the SVC) is that `@st.cache_resource` does not support partial invalidation by key.

**Returns**: `bool` — True if retraining succeeded

---

### `predict_attendance(class_image_np)` — `face_pipeline.py:75`

**Called from**: `teacher_screen.py` (Run Face Analysis), `student_screen.py` (face login)

**Input**: RGB numpy array of a classroom photo or selfie

**Full algorithm**:
1. `get_face_embeddings(class_image_np)` — extract embeddings for every face in the image
2. `get_trained_model()` — load the cached SVC
3. Early exit if no model: return `({}, [], num_faces)`
4. For each face embedding:
   - **If ≥2 enrolled students**: `clf.predict([encoding])` → predicted `student_id`
   - **If only 1 enrolled student**: SVC requires ≥2 classes to train, so this edge case bypasses the classifier and assigns that single student directly
   - Retrieve the training embedding for the predicted student: `X_train[y_train.index(predicted_id)]`
   - Compute Euclidean distance: `np.linalg.norm(stored_embedding - new_embedding)`
   - **Accept if distance ≤ 0.6**: mark the student as detected
   - **Reject if distance > 0.6**: the SVC's guess is too far — likely a stranger or a bad photo

**Why the two-stage check?** The SVC always produces a prediction — it has no "none of the above" option. Without the distance gate, a photo of a completely unknown person would still get matched to the closest student. The Euclidean threshold is the rejection mechanism.

**Returns**: `(detected_students, all_student_ids, num_faces_in_image)`

---

## Voice Recognition Pipeline

**File**: `src/pipelines/voice_pipeline.py`

The voice pipeline identifies individual speakers within a classroom audio recording. It uses a pre-trained speaker encoder (GE2E) to convert voice into numerical vectors, then compares them against stored voice profiles.

### Pipeline Flow

```
Raw Audio Bytes (from st.audio_input().read())
            │
            ▼
┌─────────────────────────────────────────────┐
│  librosa.load(io.BytesIO(bytes), sr=16000)  │  ← Decodes any audio format (WAV, M4A, WebM).
│                                             │    Resamples to 16kHz mono. Both steps are
└─────────────────────────────────────────────┘    required by the GE2E model.
            │  Returns: (audio_array, sample_rate=16000)
            ▼
┌─────────────────────────────────────────────┐
│  librosa.effects.split(audio, top_db=30)    │  ← Voice Activity Detection (VAD).
│  [BULK MODE ONLY]                           │    Returns (start_sample, end_sample) pairs
└─────────────────────────────────────────────┘    for segments at least 30dB above silence.
            │  Skips segments shorter than 0.5 seconds
            ▼
┌─────────────────────────────────────────────┐
│  resemblyzer.preprocess_wav(audio_array)    │  ← Resemblyzer's normalization:
│                                             │    trims leading/trailing silence,
└─────────────────────────────────────────────┘    normalizes amplitude to a standard range.
            │
            ▼
┌─────────────────────────────────────────────┐
│  VoiceEncoder.embed_utterance(wav)          │  ← GE2E (Generalized End-to-End) neural
│                                             │    network. Produces an L2-normalized
└─────────────────────────────────────────────┘    256-dimensional speaker embedding vector.
            │  Returns: np.ndarray shape (256,)
            ▼
┌─────────────────────────────────────────────┐
│  np.dot(new_embedding, stored_embedding)    │  ← Cosine similarity between the new
│  threshold = 0.65                           │    voice and each enrolled student's
└─────────────────────────────────────────────┘    stored voice profile.
            │
            ▼
    {student_id: best_score}   ← Only students who exceed the threshold are returned
```

---

### `load_voice_encoder()` — `voice_pipeline.py:9`

**Decorator**: `@st.cache_resource`

Loads `VoiceEncoder()` from the Resemblyzer library. This is a GE2E (Generalized End-to-End) model pre-trained on thousands of speakers. It maps utterances of any length into a fixed 256-dimensional L2-normalized space where:
- Two recordings of the same person → close vectors (high cosine similarity)
- Recordings of different people → distant vectors (low cosine similarity)

---

### `get_voice_embedding(audio_bytes)` — `voice_pipeline.py:13`

**Called from**: `student_screen.py` during student registration (voice enrollment step)

**Input**: Raw audio bytes from `st.audio_input().read()`

**Steps**:
1. `librosa.load(io.BytesIO(audio_bytes), sr=16000)` — decodes the audio from any format and resamples to 16kHz mono (GE2E requirement)
2. `preprocess_wav(audio)` — Resemblyzer's normalization pipeline
3. `encoder.embed_utterance(wav)` — runs the GE2E network; output is 256-dim, L2-normalized
4. `.tolist()` — converts numpy array to Python list for JSON storage in Supabase

**Output**: `List[float]` with 256 values, or `None` if audio is corrupt/too short/wrong format

**Error handling**: Entire function wrapped in try/except. Error is shown via `st.error()` and `None` is returned.

---

### `identify_speaker(new_embedding, candidates_dict, threshold=0.65)` — `voice_pipeline.py:26`

**Called from**: `process_bulk_audio()` for each audio segment

**Input**:
- `new_embedding`: 256-dim list/array from a voice segment
- `candidates_dict`: `{student_id: voice_embedding}` for all enrolled students who have voice profiles
- `threshold`: minimum cosine similarity to accept a match (default 0.65)

**Algorithm**:
1. Loops through all candidates
2. Computes `np.dot(new_embedding, stored_embedding)` — this is cosine similarity because GE2E embeddings are L2-normalized by design (dot product of unit vectors = cosine)
3. Tracks the candidate with the highest similarity score
4. If that score ≥ 0.65 → returns that student_id and score
5. If < 0.65 → returns `(None, score)` — no match

**Why cosine similarity instead of Euclidean distance?** Speaker embeddings encode voice *direction* in high-dimensional space, not magnitude. Two recordings of the same person at different loudness levels should produce vectors pointing in the same direction. Cosine similarity is magnitude-invariant. (Euclidean distance would change if one recording is louder, even for the same speaker.)

---

### `process_bulk_audio(audio_bytes, candidates_dict, threshold=0.65)` — `voice_pipeline.py:47`

**Called from**: `dialog_voice_attendance.py` when the teacher clicks "Analyze Audio"

**Input**: Full classroom recording (everyone speaking one at a time or in sequence)

**Steps**:
1. `librosa.load(...)` — decode + resample to 16kHz
2. `librosa.effects.split(audio, top_db=30)` — Voice Activity Detection. Returns `(start, end)` sample pairs for every region at least 30dB above the noise floor. This segments the recording into individual speech bursts
3. For each segment:
   - Skip if duration < 0.5 seconds (too short for a reliable embedding — filters noise bursts and keyboard clicks)
   - `preprocess_wav(segment)` + `embed_utterance()` → 256-dim embedding
   - `identify_speaker(embedding, candidates_dict)` → `(student_id | None, score)`
   - If a match: store only the **best score** seen so far for that student (a student might speak multiple times — the highest-confidence segment wins)
4. Returns `{student_id: best_score}` for all positively identified students

**Returns**: Only students who were identified. Absent students simply don't appear in the dict.

---

### How Enrollment and Voice Attendance Connect

```
ENROLLMENT (student_screen.py — registration)
─────────────────────────────────────────────
st.audio_input()
   └─ .read()
       └─ get_voice_embedding(bytes)   →  [256 floats]
           └─ create_student(..., voice_embedding=[256 floats])
               └─ Supabase: students.voice_embedding = [...]


ATTENDANCE (dialog_voice_attendance.py)
───────────────────────────────────────
Supabase: SELECT subject_students + students WHERE subject_id = X
   └─ candidates_dict = {student_id: voice_embedding, ...}   (only students WITH voice profiles)
       └─ st.audio_input().read()
           └─ process_bulk_audio(bytes, candidates_dict)
               └─ {student_id: similarity_score}
                   └─ Build results DataFrame → show_attendance_result()
                       └─ Teacher confirms → create_attendance(logs)
```

---

## Feature Walkthrough

### Home Screen

**File**: `src/screens/home_screen.py`

The landing page applies the home-specific glassmorphism background (`style_background_home()`), renders the centered RollCall logo and tagline, then presents two side-by-side portal cards in a two-column layout:

- **Student Portal** card — "View your attendance · Enroll in subjects · Check in quickly" → clicking sets `st.session_state['login_type'] = 'student'` and reruns
- **Teacher Portal** card — "Take attendance · Manage subjects · View records" → sets `login_type = 'teacher'`

On hover, the cards glow blue (CSS `rgba(37,99,235,0.12)` background + blue border).

---

### Teacher Portal

#### Teacher Login (`teacher_screen_login`)

Two text inputs (Username, Password) with a Login button and a "Register instead" toggle.

On login:
1. `teacher_login(username, password)` queries the `teachers` table for the username
2. `bcrypt.checkpw()` verifies the password against the stored hash in Python (not in SQL)
3. On success: sets `st.session_state.teacher_data`, `is_logged_in = True`, `user_role = 'teacher'`, shows a welcome toast, reruns to the dashboard

#### Teacher Register (`teacher_screen_register`)

Four fields: Username, Full Name, Password, Confirm Password.

On submit:
1. `check_teacher_exists(username)` — rejects if username is taken
2. Password match validation
3. `create_teacher(username, password, name)` — bcrypt-hashes the password, inserts into `teachers`
4. Switches to login mode after 2 seconds

#### Teacher Dashboard (`teacher_dashboard`)

After login, the dashboard shows:
- A compact RollCall header (top-left) + teacher name badge (top-right) + Logout button
- Three tab buttons rendered as a 3-column `st.columns` row:

| Tab Button | `current_teacher_tab` value | Content |
|---|---|---|
| 📸 Take Attendance | `take_attendance` | Face scan + voice attendance |
| 📚 Subjects | `manage_subjects` | Subject cards + create/share |
| 📋 Records | `attendance_records` | Historical attendance table |

Active tab button renders as `type='primary'` (blue); inactive as `type='secondary'` (dark border).

---

#### Take Attendance Tab (`teacher_tab_take_attendance`)

**Face Attendance flow**:

1. Teacher picks a subject from a `st.selectbox`
2. **Add Photos** button → `add_photos_dialog()`:
   - **Camera tab**: `st.camera_input` for live snapshots. Each captured photo is appended to `st.session_state.attendance_images` as a PIL Image
   - **Upload tab**: `st.file_uploader(accept_multiple_files=True)` for JPG/PNG. Uploaded files appended to the same list
3. A 4-column photo gallery shows all accumulated images
4. **Run Face Analysis** button (disabled until photos exist):
   - Converts each PIL Image to numpy RGB array
   - Calls `predict_attendance(img_np)` on each → collects all detected student IDs across all photos
   - Fetches the full enrolled student list for the selected subject from Supabase
   - For each enrolled student: marks Present if their ID was detected in any photo, Absent otherwise
   - Builds a results list: `{Name, ID, Source (which photo), Status (✅/❌)}`
   - Creates one `attendance_to_log` dict per student: `{student_id, subject_id, timestamp, is_present}`
   - Opens `attendance_result_dialog(DataFrame, logs)` for review
5. **Clear Photos** button — empties `st.session_state.attendance_images`

**Voice Attendance flow**:

6. **Voice Attendance** button → `voice_attendance_dialog(selected_subject_id)`:
   - Teacher records audio via `st.audio_input`
   - On "Analyze Audio": fetches enrolled students + their voice embeddings
   - Calls `process_bulk_audio(audio_bytes, candidates_dict)`
   - Builds the same results/logs structure as face attendance
   - Shows `show_attendance_result()` inline inside the dialog

**Attendance Confirmation** (`dialog_attendance_results.py`):
- Shows a DataFrame with Name, ID, Source, Status
- Two buttons: **Discard** (clear results, close) and **Confirm & Save** (calls `create_attendance(logs)` → bulk INSERT into `attendance_logs`, then clears state)

---

#### Subjects Tab (`teacher_tab_manage_subjects`)

- **New Subject** button → `create_subject_dialog(teacher_id)`:
  - Three fields: Subject Code (e.g. `CS101`), Subject Name, Section
  - Calls `create_subject()` on submit

- Subject list rendered as `subject_card` components, one per subject:
  - Blue left-border dark card
  - Shows subject name, code badge, section, stat chips (student count, class sessions)
  - **Share** button → `share_subject_dialog(name, code)`:
    - Generates `rollcall-main.streamlit.app/?join-code={code}` URL
    - Creates QR code PNG via `segno.make(url).save(out, kind='png', scale=10)`
    - Two-column layout: copy link + subject code (left) | QR code image (right)

---

#### Records Tab (`teacher_tab_attendance_records`)

- `get_attendance_for_teacher(teacher_id)` fetches all `attendance_logs` rows for this teacher's subjects via an inner join
- Builds a Pandas DataFrame with columns: `ts_group` (for grouping), `Time` (formatted), `Subject`, `Subject Code`, `is_present`
- Groups by `(ts_group, Time, Subject, Subject Code)`, aggregates: `Present_Count = sum(is_present)`, `Total_Count = count(is_present)`
- Derives: `Attendance Stats = "✅ 24 / 30 Students"`
- Sorts by timestamp descending, displays as `st.dataframe` (sortable, filterable)

---

### Student Portal

#### Student Login — Face Recognition

The student screen uses `st.camera_input` for both login and registration.

**Login mode**:
1. Student takes a selfie
2. `predict_attendance(img_array)` runs face recognition
3. Three outcomes:
   - **0 faces detected**: warning — try again in better lighting
   - **>1 face detected**: warning — only one student at a time
   - **1 face, recognized**: loads student data from `get_all_students()`, sets `student_data` in session state → dashboard
   - **1 face, not recognized**: info message suggesting to switch to Register mode

**Register mode**:
1. Student takes a selfie (same camera input, different label text)
2. Fills in Full Name
3. Optionally records a voice sample (`st.audio_input`) — shown with the label "Voice Enrollment (optional)"
4. On "Create Account":
   - `get_face_embeddings(img)` extracts the 128-dim face vector
   - If no face found → error, stop
   - `get_voice_embedding(audio_bytes)` extracts 256-dim voice vector (or `None` if skipped)
   - `create_student(name, face_emb, voice_emb)` inserts into Supabase
   - `train_classifier()` forces SVC retraining so the new student is immediately recognizable
   - Student is logged in instantly (no second login step needed)

---

#### Student Dashboard (`student_dashboard`)

- Header with RollCall logo + student name badge + Logout button
- "My Subjects" section with "Enroll in Subject" button
- Subjects rendered as a **2-column grid** of `subject_card` components
- Per-subject statistics computed from `get_student_attendance(student_id)`:
  - Total classes (all `attendance_logs` rows for this subject)
  - Attended (rows where `is_present = true`)
  - Attendance rate % with color emoji: 🟢 ≥75% (safe), 🟡 ≥50% (borderline), 🔴 <50% (danger)
- Each card has an **Unenroll** tertiary button that calls `unenroll_student_to_subject()` and reruns

**Manual enrollment** (`dialog_enroll.py`):
- Student enters a subject code
- Query `subjects` table to find the subject
- Check `subject_students` to prevent duplicate enrollment
- `enroll_student_to_subject(student_id, subject_id)` → inserts into join table

**QR deep-link enrollment** (`dialog_auto_enroll.py`):
- Triggered from `app.py` when `?join-code=` is present in the URL and the student is logged in
- Shows subject name, Yes/No buttons
- On Yes: `enroll_student_to_subject()`, clears query params, reruns
- On No: clears query params, reruns

---

## Session State & Routing

The app implements **routing via a state machine** in `st.session_state`. There are no URL routes and no HTTP GET/POST handlers. The entire routing tree is:

```
st.session_state['login_type']
├── None          → home_screen()
├── 'teacher'     → teacher_screen()
│   ├── no teacher_data + teacher_login_type == 'login'     → teacher_screen_login()
│   ├── no teacher_data + teacher_login_type == 'register'  → teacher_screen_register()
│   └── teacher_data present                                → teacher_dashboard()
│       ├── current_teacher_tab == 'take_attendance'        → teacher_tab_take_attendance()
│       ├── current_teacher_tab == 'manage_subjects'        → teacher_tab_manage_subjects()
│       └── current_teacher_tab == 'attendance_records'     → teacher_tab_attendance_records()
└── 'student'     → student_screen()
    ├── no student_data + student_mode == 'login'    → camera login form
    ├── no student_data + student_mode == 'register' → camera + registration form
    └── student_data present                         → student_dashboard()
```

**Complete session state reference**:

| Variable | Type | Set by | Cleared by | Purpose |
|---|---|---|---|---|
| `login_type` | str / None | Home portal buttons | Back to Home buttons | Top-level screen selector |
| `teacher_login_type` | str | Register/Login toggle | Back to Home | Teacher auth form variant |
| `teacher_data` | dict | `teacher_login()` | Logout button | Presence triggers teacher dashboard |
| `student_mode` | str | Toggle button | Back / Logout | Student camera mode |
| `student_data` | dict | Face login / register | Logout button | Presence triggers student dashboard |
| `is_logged_in` | bool | Login functions | Logout | General auth flag |
| `user_role` | str | Login functions | Logout | `'teacher'` or `'student'` |
| `current_teacher_tab` | str | Tab buttons | — | Which teacher tab is active |
| `attendance_images` | list | `add_photos_dialog` | Clear/Confirm buttons | Accumulated classroom photos |
| `voice_attendance_results` | tuple/None | `voice_attendance_dialog` | Discard/Confirm | Voice scan results pending review |
| `photo_tab` | str | Tab buttons in dialog | — | Camera vs Upload in add-photo dialog |

---

## UI System

The entire UI uses a custom dark-theme design system implemented via injected CSS — no external CSS framework, no Tailwind, no Bootstrap.

### Color Palette

| Token | Hex | Usage |
|---|---|---|
| Background | `#0F172A` | App background (Slate 950) |
| Surface | `#1E293B` | Cards, inputs, containers (Slate 800) |
| Border | `#334155` | Dividers, input borders (Slate 700) |
| Primary | `#2563EB` | Buttons, accents, left border on cards (Blue 600) |
| Primary hover | `#1D4ED8` | Button hover state (Blue 700) |
| Primary muted | `rgba(37,99,235,0.15)` | Badge backgrounds, glow effects |
| Text primary | `#F1F5F9` | Headings, body text (Slate 100) |
| Text secondary | `#94A3B8` | Labels, captions (Slate 400) |
| Text muted | `#64748B` | Subtitles, placeholder (Slate 500) |
| Text link | `#93C5FD` | Highlighted text, badges (Blue 300) |
| Success | `#10B981` | Attendance ≥75% (Emerald 500) |
| Warning | `#F59E0B` | Attendance ≥50% (Amber 500) |
| Danger | `#EF4444` | Attendance <50% (Red 500) |

### Component Styles

**Button variants**:
- `type='primary'` — indigo fill, white text, blue box-shadow, lifts 2px on hover
- `type='secondary'` — dark surface, slate border, text turns blue on hover
- `type='tertiary'` — transparent, grey border, text + border turn red on hover (used for destructive actions like Unenroll)

**Text inputs**: dark surface, 1.5px slate border, blue focus ring (`box-shadow: 0 0 0 3px rgba(37,99,235,0.2)`), placeholder in muted grey, uppercase label tracking

**Subject cards**: raw HTML via `st.markdown(unsafe_allow_html=True)` — dark surface with a 4px blue left-border accent, stat chips (icon + bold number + small grey label) arranged horizontally

**Animations**:
- `fadeSlideUp` — `opacity: 0 → 1`, `translateY(16px → 0)` over 0.35s. Applied to portal cards and subject cards
- `fadeIn` — opacity only, applied to the main page container

---

## Environment Variables & Secrets

Only two secrets are required:

**`.streamlit/secrets.toml`** (local development — do NOT commit this file):
```toml
SUPABASE_URL = "https://xxxxxxxxxxx.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

**Streamlit Community Cloud deployment**: Add these in App Settings → Secrets (same key names, same format).

Both are read in `src/database/config.py` via:
```python
st.secrets["SUPABASE_URL"]
st.secrets["SUPABASE_KEY"]
```

The Supabase key can be either the `anon` public key (if Row Level Security is configured) or the `service_role` key (full access — use only in trusted server environments like Streamlit Cloud).

---

## Local Setup

### Prerequisites

- Python 3.10, 3.11, or 3.13
- CMake and a C++ compiler (required to build `dlib`)
  - macOS: `brew install cmake`
  - Ubuntu/Debian: `sudo apt install cmake build-essential libopenblas-dev liblapack-dev`
  - Windows: Install Visual Studio Build Tools + CMake
- A Supabase project (free tier is sufficient)

### Installation

```bash
# 1. Clone
git clone <your-repo-url>
cd ai-attendance-project-app

# 2. Create virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 3. Install all dependencies
pip install -r requirements.txt
# Note: dlib-bin and face_recognition_models may take several minutes to compile/install

# 4. Create secrets file
mkdir -p .streamlit
cat > .streamlit/secrets.toml << EOF
SUPABASE_URL = "https://your-project.supabase.co"
SUPABASE_KEY = "your-supabase-key"
EOF

# 5. Run
streamlit run app.py
```

The app opens at `http://localhost:8501`.

---

## Supabase Table Setup

Run this SQL in your Supabase project's SQL Editor (Dashboard → SQL Editor → New query):

```sql
-- Teachers
CREATE TABLE teachers (
  teacher_id SERIAL PRIMARY KEY,
  username   TEXT UNIQUE NOT NULL,
  password   TEXT NOT NULL,
  name       TEXT NOT NULL
);

-- Students (biometric embeddings stored as JSONB)
CREATE TABLE students (
  student_id      SERIAL PRIMARY KEY,
  name            TEXT NOT NULL,
  face_embedding  JSONB,          -- 128 floats, nullable
  voice_embedding JSONB           -- 256 floats, nullable
);

-- Subjects
CREATE TABLE subjects (
  subject_id   SERIAL PRIMARY KEY,
  subject_code TEXT NOT NULL,
  name         TEXT NOT NULL,
  section      TEXT NOT NULL,
  teacher_id   INTEGER REFERENCES teachers(teacher_id) ON DELETE CASCADE
);

-- Enrollment join table
CREATE TABLE subject_students (
  student_id INTEGER REFERENCES students(student_id) ON DELETE CASCADE,
  subject_id INTEGER REFERENCES subjects(subject_id) ON DELETE CASCADE,
  PRIMARY KEY (student_id, subject_id)
);

-- Attendance logs (one row per student per session, present or absent)
CREATE TABLE attendance_logs (
  id         SERIAL PRIMARY KEY,
  student_id INTEGER REFERENCES students(student_id) ON DELETE CASCADE,
  subject_id INTEGER REFERENCES subjects(subject_id) ON DELETE CASCADE,
  timestamp  TEXT NOT NULL,
  is_present BOOLEAN NOT NULL
);
```

---

## Dependencies Explained

```
# Core framework
streamlit              Web framework — UI, server, session state, secrets, dialogs

# Data
numpy                  Embedding arithmetic: Euclidean distance, dot product, array ops
pandas                 Build and aggregate attendance DataFrames for display

# Face recognition stack
dlib-bin               Compiled dlib binaries — HOG detector, shape predictor, ResNet embedder
face_recognition_models  Pre-trained model weight files for dlib (pip-installable package)
scikit-learn           SVC classifier for mapping 128-dim face embeddings → student identities
setuptools<70.0.0      Version pin required for dlib-bin build compatibility

# Voice recognition stack
resemblyzer            GE2E speaker encoder — 256-dim voice embeddings, cosine speaker ID
librosa                Audio decode/resample, Voice Activity Detection (effects.split)

# Database
supabase               Supabase Python client — wraps PostgREST, fluent builder query API

# Security
bcrypt                 Password hashing for teacher accounts (salted, slow hash)

# Utilities
segno                  QR code generation — produces PNG output for subject share dialog
pillow                 PIL Image — opens camera captures and uploaded files for numpy conversion
```

---

## Known Limitations & Design Notes

### Face Pipeline

**One embedding per student**: Only one photo is taken at registration. Production systems store multiple embeddings per student (different lighting, angles, headwear) and average or ensemble them. Students registering in bad lighting may fail recognition later.

**Full table scan for training**: `get_all_students()` fetches every student row including full 128-float embedding arrays on every `get_trained_model()` call. At 30–50 students this is fine. Beyond ~500 students this payload becomes large and slow — a vector database (pgvector, Pinecone) with approximate nearest-neighbor search would be needed.

**Cache invalidation nuclear option**: `train_classifier()` calls `st.cache_resource.clear()` which evicts ALL cached objects — including the dlib model files. The next inference call takes 3–5 seconds to reload dlib. A more targeted cache invalidation strategy would be needed at scale.

**SVC minimum class count**: The SVC requires at least 2 classes. With exactly 1 registered student, the pipeline bypasses the classifier entirely and assigns any face with distance ≤ 0.6 to that student.

---

### Voice Pipeline

**Single enrollment utterance**: Each student provides exactly one voice sample during registration. Real speaker verification systems average embeddings over 5–10 utterances recorded in different conditions for robustness.

**Threshold is a judgment call**: The cosine similarity threshold of 0.65 is not derived from data — it is a starting estimate. Background classroom noise, microphone quality, and the distance from students to the recording device all affect whether 0.65 is too strict or too permissive for a given environment.

**Voice attendance is all-or-nothing per student**: A student who skips voice enrollment at registration time can never be identified by voice. The dialog shows a warning if no enrolled students in the selected subject have voice profiles.

**No de-duplication across segments**: If two students speak at nearly the same time and their voices overlap in a segment, the segment embedding will be a blend and may match neither or the wrong person.

---

### Database

**No sessions table**: A "class session" is identified by grouping `attendance_logs` rows with the same `timestamp` string. If two attendance runs happen to be triggered within the same second, their rows are grouped into one session. In practice this is extremely unlikely.

**Direct Supabase queries outside `db.py`**: The dialog components `dialog_enroll.py`, `dialog_auto_enroll.py`, `dialog_voice_attendance.py`, and `teacher_screen.py` (face scan flow) query Supabase directly without going through the data access layer in `db.py`. This makes those paths harder to test or refactor.

**No Row Level Security**: The current setup uses the Supabase API key for all operations with no per-user RLS policies. A teacher querying attendance records with a crafted request could theoretically access another teacher's data. For production, RLS policies should be added to restrict `subjects` and `attendance_logs` access to the owning teacher.

**Passwords hashed in Python, not Supabase**: `bcrypt` hashing is done application-side. This is correct but means if someone directly inserts a row into `teachers` via the Supabase dashboard, they could bypass the hash. The anon key should not have INSERT permissions on the `teachers` table in production.

---

### General

**No email verification or password reset**: Teacher accounts have no email field, so there is no account recovery flow.

**Streamlit re-render cost**: Streamlit re-runs the full script on every user interaction. All expensive operations (ML inference, large DB fetches) are protected by `@st.cache_resource` or `with st.spinner()`. Avoid adding blocking operations outside these guards.

**Single-page app with no navigation history**: The browser back button does not navigate between screens — it exits the Streamlit app entirely. The `st.session_state` router has no history stack.

---

© 2025 RollCall
