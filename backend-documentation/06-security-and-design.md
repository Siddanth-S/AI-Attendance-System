# Security, Design Decisions, and Trade-offs

## Authentication Design

### Teacher Authentication
- **Mechanism**: Username + password
- **Password storage**: bcrypt hash (never plaintext). `bcrypt.hashpw(pwd.encode(), bcrypt.gensalt())`
- **Verification**: `bcrypt.checkpw(input.encode(), stored_hash.encode())`
- **Session**: On login, `teacher_data` dict is placed in `st.session_state`. No JWT, no cookie — Streamlit manages browser session via WebSocket.
- **Logout**: `del st.session_state.teacher_data` + `st.rerun()`

### Student Authentication
- **Mechanism**: Face recognition only — no password
- **How it works**: Camera photo → dlib 128-dim embedding → SVC predicts student_id → Euclidean distance gate
- **Why no password for students**: Students log in frequently in class. A face scan is faster than typing credentials. The trade-off is lower security — if someone looks similar to a student, they could log in.
- **Session**: `student_data` dict in `st.session_state`

---

## Security Considerations

### What's secure
- Teacher passwords are properly bcrypt-hashed with per-password salts
- Supabase credentials are in `.streamlit/secrets.toml` (not hardcoded, not in git)
- `.gitignore` excludes `secrets.toml`

### What's NOT secure (known limitations)
1. **No server-side session validation**: `st.session_state` is client-side memory per browser tab. There's no server-side token validation. If Streamlit restarts, sessions are lost.
2. **Supabase anon key in use**: The key in secrets is the public anon key. Row-level security (RLS) policies in Supabase should protect against unauthorized cross-user access — but this is not implemented in the app itself.
3. **Student face auth can be spoofed**: A photo of a student's face could potentially fool the detector depending on the threshold.
4. **No rate limiting**: No protection against brute force login attempts on teacher accounts.
5. **Subject codes are guessable**: Short codes like "CS101" — anyone who guesses a code can enroll. No additional confirmation from teacher.
6. **`get_all_students()` returns all embeddings**: Every face scan fetches ALL students from Supabase including their 128-dim embedding arrays. At scale this is a security and performance problem.

---

## Key Design Decisions

### 1. Streamlit as the full stack
**Decision**: Use Streamlit instead of a traditional frontend + backend split.  
**Consequence**: No REST API, no auth tokens, no CORS. All logic is Python on the server. Great for rapid prototyping; not suitable for high-traffic production.

### 2. SVC for face recognition instead of cosine similarity alone
**Decision**: Use sklearn SVC trained on all embeddings, followed by an Euclidean distance gate.  
**Why SVC over pure nearest-neighbor**: With multiple students, SVC creates optimal decision boundaries in 128-dim space. Euclidean distance alone would require iterating through all students and picking the closest — SVC does this more efficiently.  
**Why still use distance gate**: SVC always assigns a class, even for unknown faces. The `0.6` Euclidean distance threshold prevents a random face from being assigned to a student.

### 3. Retrain on every registration
**Decision**: Call `train_classifier()` after every new student registration, which clears all cache and retrains SVC from scratch.  
**Why not incremental**: scikit-learn SVC doesn't support incremental learning natively. For the scale (30-50 students), retraining from scratch takes < 1 second.  
**Side effect**: All `@st.cache_resource` items are cleared, including dlib models. The next face scan will be slower.

### 4. Attendance sessions inferred from timestamps
**Decision**: No `sessions` table. A session = group of `attendance_logs` rows with the same timestamp string.  
**How `total_classes` is computed**: `len(set(log['timestamp'] for log in attendance))` — count unique timestamps.  
**Risk**: If two attendance sessions happen in the same second, they'd be merged into one session count.

### 5. Inline Supabase queries in dialog components
**Decision**: Some dialogs (`dialog_enroll.py`, `dialog_voice_attendance.py`, `dialog_auto_enroll.py`) query Supabase directly instead of going through `db.py`.  
**Consequence**: The data access layer is inconsistent. `db.py` is not a complete repository — it's partial. Some queries bypass it.

### 6. Voice attendance is optional
**Decision**: `voice_embedding` is nullable. Students without voice profiles are simply excluded from voice attendance sessions.  
**Consequence**: A teacher can still do voice attendance for the subset of students who registered voices. Students without voice profiles need face attendance.

---

## Performance Considerations

| Concern | Current Behavior | Better Approach at Scale |
|---|---|---|
| Fetching all student embeddings on every face scan | `get_all_students()` — full table scan | Store embeddings in pgvector, use ANN search |
| SVC retrain on every registration | Clears all cache, retrains from scratch | Incremental learning or periodic batch retrain |
| dlib model reload after registration | cache.clear() wipes dlib models too | Separate cache keys for models vs classifier |
| No database indexing assumptions | Unknown — Supabase auto-indexes PKs and FKs | Add index on `attendance_logs(student_id)`, `attendance_logs(subject_id)` |
| Single voice sample per student | One utterance → less accurate embedding | Average multiple utterances during enrollment |
