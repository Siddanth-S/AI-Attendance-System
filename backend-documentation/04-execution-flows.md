# Complete Execution Flows

Every feature traced from user action → database and back.

---

## Flow 1: Teacher Registration

**Trigger**: User clicks "Create Account" in teacher register form

```mermaid
sequenceDiagram
    participant U as User (Browser)
    participant TS as teacher_screen.py
    participant DB as db.py
    participant SB as Supabase

    U->>TS: Fills username, name, password, confirm
    U->>TS: Clicks "Create Account"
    TS->>TS: register_teacher(username, name, pass, confirm)
    TS->>TS: Validates: all fields filled, pass == confirm
    TS->>DB: check_teacher_exists(username)
    DB->>SB: SELECT username FROM teachers WHERE username=?
    SB-->>DB: [] (empty = available)
    DB-->>TS: False (username free)
    TS->>DB: create_teacher(username, password, name)
    DB->>DB: hash_pass(password) → bcrypt hash
    DB->>SB: INSERT INTO teachers {username, hash, name}
    SB-->>DB: inserted row
    DB-->>TS: response.data
    TS->>TS: st.success(), sleep(2), set login_type='login', st.rerun()
```

**Files visited**: `teacher_screen.py` → `db.py` → `database/config.py`  
**Functions**: `teacher_screen_register()` → `register_teacher()` → `check_teacher_exists()` → `create_teacher()` → `hash_pass()`

---

## Flow 2: Teacher Login

**Trigger**: User clicks "Login" in teacher login form

```mermaid
sequenceDiagram
    participant U as User
    participant TS as teacher_screen.py
    participant DB as db.py
    participant SB as Supabase

    U->>TS: Enters username + password, clicks Login
    TS->>TS: login_teacher(username, password)
    TS->>DB: teacher_login(username, password)
    DB->>SB: SELECT * FROM teachers WHERE username=?
    SB-->>DB: [{teacher_id, username, password_hash, name}]
    DB->>DB: check_pass(input_password, stored_hash) via bcrypt
    DB-->>TS: teacher dict (if match) or None
    alt Login successful
        TS->>TS: session_state.teacher_data = teacher
        TS->>TS: session_state.is_logged_in = True
        TS->>TS: st.toast("Welcome back!"), rerun()
        TS->>TS: teacher_dashboard() renders
    else Login failed
        TS->>U: st.error("Incorrect username or password")
    end
```

---

## Flow 3: Student Registration (Face + Optional Voice)

**Trigger**: Student in register mode, takes photo, fills name, clicks "Create Account"

```mermaid
sequenceDiagram
    participant U as User
    participant SS as student_screen.py
    participant FP as face_pipeline.py
    participant VP as voice_pipeline.py
    participant DB as db.py
    participant SB as Supabase

    U->>SS: Takes photo via st.camera_input
    U->>SS: Types full name
    U->>SS: (Optional) Records voice via st.audio_input
    U->>SS: Clicks "Create Account"
    SS->>SS: Validates: photo exists, name not empty
    SS->>FP: get_face_embeddings(np.array(Image.open(photo)))
    FP->>FP: load_dlib_models() [from cache]
    FP->>FP: detector(image, 1) → face rectangles
    FP->>FP: sp(image, face) → 68 landmarks
    FP->>FP: facerec.compute_face_descriptor() → 128-dim array
    FP-->>SS: [np.array shape (128,)]
    SS->>SS: face_emb = encodings[0].tolist()
    alt Voice provided
        SS->>VP: get_voice_embedding(audio_data.read())
        VP->>VP: librosa.load() → 16kHz mono array
        VP->>VP: preprocess_wav() → normalized wav
        VP->>VP: encoder.embed_utterance() → 256-dim array
        VP-->>SS: [256 floats] or None
    end
    SS->>DB: create_student(name, face_emb, voice_emb)
    DB->>SB: INSERT INTO students {name, face_embedding, voice_embedding}
    SB-->>DB: [{student_id, name, ...}]
    DB-->>SS: response.data (list with one dict)
    SS->>FP: train_classifier()
    FP->>FP: st.cache_resource.clear()
    FP->>FP: get_trained_model() → retrains SVC with new student
    FP->>DB: get_all_students()
    DB->>SB: SELECT * FROM students
    SB-->>DB: all students with embeddings
    SS->>SS: session_state.student_data = response_data[0]
    SS->>SS: st.rerun() → student_dashboard() renders
```

---

## Flow 4: Student Face Login

**Trigger**: Student in login mode takes a photo

```mermaid
sequenceDiagram
    participant U as User
    participant SS as student_screen.py
    participant FP as face_pipeline.py
    participant DB as db.py
    participant SB as Supabase

    U->>SS: Takes photo via st.camera_input (login mode)
    SS->>FP: predict_attendance(np.array(Image.open(photo)))
    FP->>FP: get_face_embeddings(image) → list of 128-dim arrays
    FP->>FP: get_trained_model() [from cache]
    Note over FP: If cache miss: fetches all students, trains SVC
    FP->>FP: For each encoding: clf.predict() → student_id
    FP->>FP: Euclidean distance check ≤ 0.6
    FP-->>SS: ({student_id: True}, all_ids, num_faces)
    alt No face detected (num_faces == 0)
        SS->>U: st.warning("No face detected")
    else Multiple faces
        SS->>U: st.warning("Multiple faces detected")
    else Face recognized
        SS->>DB: get_all_students()
        DB->>SB: SELECT * FROM students
        SB-->>DB: all students
        SS->>SS: Find student where student_id matches
        SS->>SS: session_state.student_data = student
        SS->>SS: st.rerun() → dashboard
    else Face not recognized
        SS->>U: st.info("Face not recognized. Switch to Register mode")
    end
```

---

## Flow 5: Teacher Takes Face Attendance

**Trigger**: Teacher adds photos, clicks "Run Face Analysis"

```mermaid
sequenceDiagram
    participant T as Teacher
    participant TS as teacher_screen.py
    participant FP as face_pipeline.py
    participant SB as Supabase
    participant D as dialog_attendance_results.py
    participant DB as db.py

    T->>TS: Selects subject from dropdown
    T->>TS: Adds photos via dialog_add_photo
    T->>TS: Clicks "Run Face Analysis"
    loop For each photo in attendance_images
        TS->>FP: predict_attendance(img.convert('RGB'))
        FP-->>TS: ({student_id: True}, ..., num_faces)
        TS->>TS: all_detected_ids[student_id].append("Photo N")
    end
    TS->>SB: SELECT subject_students, students WHERE subject_id=?
    SB-->>TS: [{student_id, students: {name, ...}}]
    loop For each enrolled student
        TS->>TS: Check if student_id in all_detected_ids
        TS->>TS: Build result row: {Name, ID, Source, Status}
        TS->>TS: Build log row: {student_id, subject_id, timestamp, is_present}
    end
    TS->>D: attendance_result_dialog(DataFrame, logs)
    D->>T: Shows table with Present/Absent
    alt Teacher clicks "Confirm & Save"
        D->>DB: create_attendance(logs)
        DB->>SB: INSERT INTO attendance_logs (bulk)
        D->>TS: st.rerun()
    else Teacher clicks "Discard"
        D->>TS: Clears images, rerun
    end
```

---

## Flow 6: Teacher Takes Voice Attendance

**Trigger**: Teacher clicks "Voice Attendance", records audio, clicks "Analyze Audio"

```mermaid
sequenceDiagram
    participant T as Teacher
    participant VAD as dialog_voice_attendance.py
    participant VP as voice_pipeline.py
    participant SB as Supabase
    participant DAR as dialog_attendance_results.py

    T->>VAD: Clicks "Voice Attendance" button
    VAD->>T: Dialog opens with audio recorder
    T->>VAD: Records classroom audio
    T->>VAD: Clicks "Analyze Audio"
    VAD->>SB: SELECT subject_students+students WHERE subject_id=?
    SB-->>VAD: enrolled students with voice_embeddings
    VAD->>VAD: Build candidates_dict = {student_id: voice_embedding}
    Note over VAD: Filters only students with voice profiles
    VAD->>VP: process_bulk_audio(audio_bytes, candidates_dict)
    VP->>VP: librosa.load → 16kHz audio
    VP->>VP: librosa.effects.split → voice segments (VAD)
    loop For each segment > 0.5 seconds
        VP->>VP: preprocess_wav + embed_utterance → 256-dim vector
        VP->>VP: identify_speaker(embedding, candidates_dict)
        VP->>VP: np.dot(new, stored) for each candidate
        VP->>VP: Return best match if score ≥ 0.65
    end
    VP-->>VAD: {student_id: best_score}
    VAD->>VAD: Build results DataFrame + attendance_to_log
    VAD->>VAD: session_state.voice_attendance_results = (df, logs)
    VAD->>DAR: show_attendance_result(df, logs)
    T->>DAR: Clicks "Confirm & Save"
    DAR->>SB: INSERT INTO attendance_logs (bulk)
```

---

## Flow 7: Student Enrolls in Subject via QR Code

**Trigger**: Student scans QR code → opens app URL with `?join-code=CS101`

```mermaid
sequenceDiagram
    participant S as Student
    participant APP as app.py
    participant AED as dialog_auto_enroll.py
    participant DB as db.py
    participant SB as Supabase

    S->>APP: Opens URL: rollcall.app/?join-code=CS101
    APP->>APP: join_code = st.query_params.get('join-code') → "CS101"
    APP->>APP: Checks login_type == 'student' (else forces student screen)
    APP->>APP: Checks is_logged_in and user_role == 'student'
    APP->>AED: auto_enroll_dialog("CS101")
    AED->>SB: SELECT subject_id, name FROM subjects WHERE subject_code='CS101'
    SB-->>AED: [{subject_id: 5, name: "CS101"}]
    AED->>SB: SELECT * FROM subject_students WHERE subject_id=5 AND student_id=?
    SB-->>AED: [] (not enrolled yet)
    AED->>S: "Would you like to enroll in CS101?"
    S->>AED: Clicks "Yes, enroll now!"
    AED->>DB: enroll_student_to_subject(student_id, subject_id)
    DB->>SB: INSERT INTO subject_students {student_id, subject_id}
    AED->>APP: st.query_params.clear(), rerun()
```

---

## Flow 8: Teacher Shares Subject (QR Code Generation)

**Trigger**: Teacher clicks "Share" button on a subject card

```mermaid
sequenceDiagram
    participant T as Teacher
    participant TS as teacher_screen.py
    participant DS as dialog_share_subject.py
    participant SEG as segno (QR library)

    T->>TS: Clicks "🔗 Share · [Subject Name]"
    TS->>DS: share_subject_dialog(subject_name, subject_code)
    DS->>DS: join_url = "rollcall-main.streamlit.app/?join-code=CS101"
    DS->>SEG: segno.make(join_url)
    SEG-->>DS: QR code object
    DS->>DS: qr.save(BytesIO, kind='png', scale=10)
    DS->>T: Shows st.code(join_url) + st.image(qr_bytes)
```

Note: No database query in this flow. The QR code is generated purely from the subject_code already in memory.

---

## Password Security Flow

```
Registration:
  raw_password (str)
      → bcrypt.hashpw(pwd.encode(), bcrypt.gensalt())
      → hash stored in Supabase (60-char bcrypt string starting with $2b$)

Login:
  input_password (str) + stored_hash (str from DB)
      → bcrypt.checkpw(input.encode(), hash.encode())
      → bool (True = match)
```

bcrypt is a one-way hash. The original password cannot be recovered. The salt is embedded in the hash string itself, so `gensalt()` is called at registration and does not need to be stored separately.
