# Interview Questions — Based Entirely on This Codebase

These questions are grounded in actual code in this repository. Every question can be answered by pointing to a specific file and line.

---

## Round 1: Architecture and Framework

**Q1. Walk me through how this application works at a high level. What happens when a user opens the app?**

*What you must cover*:
- `app.py` is the entry point, `main()` runs on every interaction
- `st.set_page_config()` configures the browser tab
- `st.session_state['login_type']` controls routing via a `match` statement
- On first load, `login_type` is `None`, so `home_screen()` renders
- No HTTP request/response — Streamlit reruns the entire script on every user action

*Follow-up*: "What is `st.session_state` and why does Streamlit need it?"
- Python re-runs top to bottom on every button click. Normal variables are reset each time. `st.session_state` is a persistent dictionary that survives between reruns within the same browser session.

---

**Q2. This app has no `routes.py`, no `controllers/` folder, no Express server. How does navigation work?**

*Answer*:
- Navigation is done via a state machine in `st.session_state['login_type']`
- Changing this variable and calling `st.rerun()` causes a different screen function to execute
- Within teacher screen: `st.session_state.teacher_login_type` switches between login/register forms
- Within student screen: `st.session_state.student_mode` switches login/register modes
- After login: presence of `teacher_data` or `student_data` in session state redirects to dashboard

---

## Round 2: Database Layer

**Q3. Look at `db.py`. Why is `teacher_login()` implemented the way it is — fetching the user then checking the password in Python — instead of sending the password to the database?**

*Answer*:
- Passwords are stored as bcrypt hashes in Supabase
- PostgreSQL doesn't know how to run bcrypt — that's an application-layer operation
- The flow is: SELECT by username → get hashed password → `bcrypt.checkpw()` in Python
- You can't do `WHERE password = bcrypt(input)` in SQL without a custom function
- This is the correct pattern for bcrypt authentication

*Follow-up*: "What does bcrypt.gensalt() do and why is it important?"
- It generates a random salt embedded in the hash. Two calls to `hash_pass("abc")` produce different hashes. This prevents rainbow table attacks.

---

**Q4. Look at `get_teacher_subjects()` in `db.py`. It uses a Supabase query with `subject_students(count)` and `attendance_logs(timestamp)`. What is happening here, and what post-processing is done in Python?**

*Answer*:
- Supabase's PostgREST syntax allows nested selects via foreign key relationships
- `subject_students(count)` returns the count of enrolled students for each subject
- `attendance_logs(timestamp)` returns all timestamp values from attendance records for each subject
- In Python after the query:
  - `sub['total_students']` is extracted from `subject_students[0]['count']`
  - `total_classes` is computed as `len(set(log['timestamp'] for log in attendance))` — unique timestamps = unique sessions
  - The nested raw data is then removed from the dict before returning

---

**Q5. `get_attendance_for_teacher()` uses `subjects!inner(*)`. What does the `!inner` mean and why is it necessary?**

*Answer*:
- In Supabase/PostgREST, a normal join returns attendance logs even if the subject join fails (left join)
- `!inner` forces an inner join — only return attendance_logs where a matching subject record exists
- The `.eq('subjects.teacher_id', teacher_id)` filter then filters to only subjects owned by this teacher
- Without `!inner`, the filter on a nullable joined column might not work correctly

---

**Q6. Why does `create_attendance()` take a list (`logs`) instead of a single object?**

*Answer*:
- When a teacher runs attendance for a subject, ALL enrolled students get a record — both present and absent ones
- This is a bulk insert — potentially 30-60 rows at once
- Supabase's `.insert()` accepts either a dict (single row) or a list of dicts (multiple rows)
- Single INSERT call is more efficient than 30-60 individual INSERTs (fewer network round trips)

---

## Round 3: Face Recognition Pipeline

**Q7. Explain the complete face recognition pipeline — from a raw image to knowing which student is present.**

*Answer* (trace `face_pipeline.py`):
1. **Detection**: `dlib.get_frontal_face_detector()` finds face bounding boxes using HOG features
2. **Landmark detection**: `dlib.shape_predictor()` finds 68 facial landmark coordinates (eye corners, nose tip, mouth corners, jawline)
3. **Embedding**: `dlib.face_recognition_model_v1()` (ResNet) computes a 128-dimensional vector. Same person → vectors are close. Different people → vectors are far.
4. **Classification**: SVC (linear kernel) trained on all stored embeddings predicts the student_id
5. **Verification**: Euclidean distance between the predicted student's stored embedding and the new embedding. If distance > 0.6, reject the match.

*Follow-up*: "Why do you need both the SVC prediction AND the distance check?"
- SVC always assigns a class — it has no concept of "I don't know this person". If an unknown face appears, SVC would assign it to whoever it's closest to in embedding space. The distance threshold rejects faces that are genuinely too far from any known person.

---

**Q8. `get_trained_model()` is decorated with `@st.cache_resource`. What does this mean and what is the consequence when `train_classifier()` is called?**

*Answer*:
- `@st.cache_resource` means the function runs once and the result is cached in memory for the server process's lifetime
- Every subsequent call returns the cached result without re-executing
- `train_classifier()` calls `st.cache_resource.clear()` which wipes ALL cached resources (not just `get_trained_model`)
- This means `load_dlib_models()` and `load_voice_encoder()` are also cleared
- The next call to any face or voice function will reload the models from disk (slower)
- A better design would use separate cache keys and only clear the SVC cache

---

**Q9. In `predict_attendance()`, there's special handling for when there's only one student in the database. What is it and why?**

*Answer (line 93-96)*:
```python
if len(all_students) >= 2:
    predicted_id = int(clf.predict([encoding])[0])
else:
    predicted_id = int(all_students[0])
```
- scikit-learn SVC requires at least 2 classes to train and predict
- With only one student registered, `clf.fit()` would fail, and `clf.predict()` is meaningless
- The code bypasses SVC and directly assigns the only known student
- The Euclidean distance check still runs — so if the face is genuinely different, it's rejected

---

**Q10. Face embeddings are stored in Supabase as arrays. Walk me through the exact type conversions from enrollment to recognition.**

*Answer*:
- **Registration**: `encodings[0].tolist()` — converts `np.ndarray` (128,) to Python `list[float]`
- **Storage**: Supabase stores it as a JSON array in the column
- **Retrieval**: `get_all_students()` returns the list as a Python list (JSON-parsed by supabase-py)
- **Training**: `np.array(embedding)` converts back to numpy for SVC training
- **Distance check**: `np.linalg.norm(student_embedding - encoding)` — both are numpy arrays at this point

---

## Round 4: Voice Recognition Pipeline

**Q11. How does the voice pipeline handle a classroom recording where multiple students are talking? Walk through `process_bulk_audio()`.**

*Answer*:
1. `librosa.load(audio, sr=16000)` — loads audio at 16kHz sample rate
2. `librosa.effects.split(audio, top_db=30)` — Voice Activity Detection. Returns `(start, end)` sample pairs where audio is 30dB above background noise
3. Segments shorter than 0.5 seconds (`sr * 0.5` samples) are skipped (too short for reliable embedding)
4. For each valid segment: extract → embed → compare against all `candidates_dict` entries using cosine similarity
5. Best score per student across all segments is kept
6. Returns `{student_id: best_score}` for identified students

---

**Q12. Why does `identify_speaker()` use `np.dot()` for similarity? Isn't that just the dot product, not cosine similarity?**

*Answer*:
- Cosine similarity = dot product / (magnitude_a × magnitude_b)
- GE2E (resemblyzer's VoiceEncoder) outputs L2-normalized embeddings (unit vectors, magnitude = 1)
- For unit vectors: cosine similarity = dot product (the denominator is 1×1 = 1)
- So `np.dot(new_embedding, stored_embedding)` IS cosine similarity for these embeddings
- This is a valid optimization that depends on the embedding model's normalization behavior

---

## Round 5: System Design Questions

**Q13. Right now, `get_all_students()` fetches every student's embedding on every face scan. What problem does this create at scale and how would you fix it?**

*Answer*:
- At 1000 students: each face scan fetches 1000 × 128 float arrays = ~500KB of data per request
- At 10,000 students: 5MB per scan, slow network calls, slow SVC inference
- **Fix 1**: Use PostgreSQL's `pgvector` extension (available in Supabase) to store embeddings in a proper vector column and do ANN (approximate nearest neighbor) search in the database
- **Fix 2**: Cache the trained SVC in Redis or a persistent file — only retrain when new students are added, not on every face scan
- **Fix 3**: Partition students by class section — only load students enrolled in the specific subject being scanned

---

**Q14. This app has no "attendance session" table. How does it know how many times a teacher has taken attendance for a subject?**

*Answer* (from `get_teacher_subjects()` in `db.py`):
```python
unique_sessions = len(set(log['timestamp'] for log in attendance))
sub['total_classes'] = unique_sessions
```
- All rows inserted in one attendance run share the same ISO timestamp string (set at the moment the teacher clicks "Confirm")
- Counting unique timestamps = counting attendance sessions
- **Problem**: If two teachers take attendance within the same second (unlikely but possible), their sessions might collide. A better design would use a proper `sessions` table with a session_id.

---

**Q15. How does QR code enrollment work end-to-end? What URL format does it use?**

*Answer*:
- Teacher clicks "Share" on a subject → `share_subject_dialog(subject_name, subject_code)`
- `join_url = "rollcall-main.streamlit.app/?join-code=CS101"` (subject_code as query param)
- `segno.make(join_url)` generates a QR code encoding this URL
- When student scans: browser opens the URL
- In `app.py`: `join_code = st.query_params.get('join-code')` — reads the query parameter
- If `join_code` exists and student is logged in: `auto_enroll_dialog(join_code)` opens
- Dialog validates subject exists, checks if already enrolled, then calls `enroll_student_to_subject()`

---

## Round 6: Deep Follow-ups

**Q16. Why does the face recognition use a linear kernel SVC specifically? What would a different kernel do?**

*Answer*:
- 128 dimensions is already very high-dimensional
- In high-dimensional space, linear separation is usually sufficient — classes are likely linearly separable
- Linear kernel SVC: `O(n_samples × n_features)` training, fast
- RBF kernel: maps to infinite-dimensional space, slower, often overkill for already-high-dimensional inputs
- `class_weight='balanced'` handles the common case where not all students have the same number of registered photos

---

**Q17. There are some Supabase queries done directly in dialog components (not through db.py). Is this a design problem? What would you do differently?**

*Answer*:
- Yes, it's inconsistent. `dialog_enroll.py`, `dialog_auto_enroll.py`, `dialog_voice_attendance.py` all query Supabase directly
- This means the data access layer (db.py) is not the single source of truth for database interactions
- If the table structure changes, you have to update multiple files
- **Better design**: Move ALL Supabase calls into `db.py`, add functions like `get_enrolled_students_with_voice(subject_id)`, `find_subject_by_code(code)`, etc.
- This follows the Repository Pattern — a single module owns all DB communication

---

**Q18. What happens if two teachers run attendance for the same subject at exactly the same time? Is there a race condition?**

*Answer*:
- `create_attendance()` does a bulk INSERT — Supabase's PostgreSQL handles concurrent inserts safely (no race condition on the insert itself)
- However: both sessions would use the same ISO timestamp (if within the same second), so `total_classes` count would show one session instead of two
- More importantly: if both teachers insert a row for the same student+subject+timestamp combination and there's a UNIQUE constraint on (student_id, subject_id, timestamp), the second insert would fail
- Without such a constraint, you'd get duplicate rows
- The app doesn't currently handle this edge case

---

## Quick Reference Cheat Sheet

| Topic | File | Key Lines |
|---|---|---|
| Entry point + routing | `app.py` | 9-33 |
| Supabase client init | `database/config.py` | 1-9 |
| Password hashing | `database/db.py` | 6-10 |
| Teacher auth | `database/db.py` | 13-33 |
| All DB operations | `database/db.py` | entire file |
| dlib model loading | `face_pipeline.py` | 13-25 |
| 128-dim embedding | `face_pipeline.py` | 27-38 |
| SVC training | `face_pipeline.py` | 41-67 |
| Face recognition | `face_pipeline.py` | 75-106 |
| Voice enrollment | `voice_pipeline.py` | 13-23 |
| Speaker identification | `voice_pipeline.py` | 26-43 |
| Bulk voice processing | `voice_pipeline.py` | 47-74 |
| Student registration | `screens/student_screen.py` | 221-244 |
| Face login | `screens/student_screen.py` | 161-183 |
| Face attendance flow | `screens/teacher_screen.py` | 148-194 |
| Attendance confirmation | `components/dialog_attendance_results.py` | 9-31 |
| QR enrollment | `components/dialog_auto_enroll.py` | entire file |
| QR generation | `components/dialog_share_subject.py` | 8-32 |
