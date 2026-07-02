# Database Schema and Interactions

## Database: Supabase (PostgreSQL)

Supabase is PostgreSQL hosted as a service. The app uses the `supabase-py` client which wraps a REST API (PostgREST) over the database. All queries are made via the client's fluent builder API — not raw SQL.

---

## Tables

### `teachers`
Stores teacher accounts.

| Column | Type | Notes |
|---|---|---|
| `teacher_id` | int (PK) | Auto-generated |
| `username` | text | Unique. Used for login |
| `password` | text | bcrypt hash. Never stored as plaintext |
| `name` | text | Display name |

### `students`
Stores student accounts and their biometric embeddings.

| Column | Type | Notes |
|---|---|---|
| `student_id` | int (PK) | Auto-generated |
| `name` | text | Display name |
| `face_embedding` | array/json | 128-dimensional float array from dlib |
| `voice_embedding` | array/json | 256-dimensional float array from resemblyzer. Optional. |

### `subjects`
Stores courses/classes created by teachers.

| Column | Type | Notes |
|---|---|---|
| `subject_id` | int (PK) | Auto-generated |
| `subject_code` | text | e.g. "CS101". Used as join code for enrollment |
| `name` | text | e.g. "Introduction to Computer Science" |
| `section` | text | e.g. "A" |
| `teacher_id` | int (FK → teachers) | Which teacher owns this subject |

### `subject_students`
Join table. Tracks which students are enrolled in which subjects.

| Column | Type | Notes |
|---|---|---|
| `student_id` | int (FK → students) | |
| `subject_id` | int (FK → subjects) | |

### `attendance_logs`
One row per student per attendance session.

| Column | Type | Notes |
|---|---|---|
| `student_id` | int (FK → students) | |
| `subject_id` | int (FK → subjects) | |
| `timestamp` | text | ISO format: "2025-01-01T10:30:00" |
| `is_present` | boolean | True = present, False = absent |

---

## Entity Relationship Diagram

```
teachers ──< subjects ──< subject_students >── students
                │                                  │
                └──< attendance_logs >─────────────┘
```

- One teacher has many subjects
- One subject has many students (through subject_students)
- One student belongs to many subjects (through subject_students)
- attendance_logs records presence per student per subject per session

---

## Every Database Query — Exact Analysis

### `check_teacher_exists(username)` — `db.py:13`
```python
supabase.table("teachers").select("username").eq("username", username).execute()
```
- **Table**: teachers
- **Type**: SELECT
- **Purpose**: Uniqueness check before registration
- **Returns**: True if username taken, False if available

### `create_teacher(username, password, name)` — `db.py:20`
```python
supabase.table("teachers").insert(data).execute()
```
- **Table**: teachers
- **Type**: INSERT
- **Data**: `{username, password: bcrypt_hash, name}`

### `teacher_login(username, password)` — `db.py:27`
```python
supabase.table("teachers").select("*").eq("username", username).execute()
```
- **Table**: teachers
- **Type**: SELECT (fetch all columns for username match)
- **Post-query logic**: bcrypt.checkpw() in Python — not done in SQL

### `get_all_students()` — `db.py:36`
```python
supabase.table('students').select("*").execute()
```
- **Table**: students
- **Type**: SELECT ALL
- **Purpose**: Used by face pipeline to build training data for SVC
- **Warning**: Fetches ALL students including face_embedding arrays. Potentially large payload.

### `create_student(name, face_embedding, voice_embedding)` — `db.py:40`
```python
supabase.table('students').insert(data).execute()
```
- **Table**: students
- **Type**: INSERT
- **Data**: `{name, face_embedding: [128 floats], voice_embedding: [256 floats] or None}`

### `create_subject(subject_code, name, section, teacher_id)` — `db.py:46`
```python
supabase.table("subjects").insert(data).execute()
```
- **Table**: subjects
- **Type**: INSERT

### `get_teacher_subjects(teacher_id)` — `db.py:51`
```python
supabase.table('subjects')
  .select("*, subject_students(count), attendance_logs(timestamp)")
  .eq("teacher_id", teacher_id)
  .execute()
```
- **Table**: subjects (with joins to subject_students and attendance_logs)
- **Type**: SELECT with nested aggregation
- **Post-query logic** (Python, not SQL):
  - Extracts `subject_students[0].count` → `total_students`
  - Counts unique timestamps in `attendance_logs` → `total_classes` (a "session" = unique timestamp)
  - Cleans up nested fields before returning

### `enroll_student_to_subject(student_id, subject_id)` — `db.py:69`
```python
supabase.table('subject_students').insert(data).execute()
```
- **Table**: subject_students
- **Type**: INSERT

### `unenroll_student_to_subject(student_id, subject_id)` — `db.py:75`
```python
supabase.table('subject_students').delete()
  .eq('student_id', student_id)
  .eq('subject_id', subject_id)
  .execute()
```
- **Table**: subject_students
- **Type**: DELETE (targeted by both FKs)

### `get_student_subjects(student_id)` — `db.py:81`
```python
supabase.table('subject_students').select('*, subjects(*)').eq('student_id', student_id).execute()
```
- **Table**: subject_students joined with subjects
- **Type**: SELECT with join
- **Returns**: Each enrollment row with the full subjects object nested

### `get_student_attendance(student_id)` — `db.py:86`
```python
supabase.table('attendance_logs').select('*, subjects(*)').eq('student_id', student_id).execute()
```
- **Table**: attendance_logs joined with subjects
- **Type**: SELECT with join
- **Returns**: All attendance records for the student with subject details

### `create_attendance(logs)` — `db.py:91`
```python
supabase.table('attendance_logs').insert(logs).execute()
```
- **Table**: attendance_logs
- **Type**: BULK INSERT (logs is a list of dicts)
- **Data per row**: `{student_id, subject_id, timestamp, is_present}`

### `get_attendance_for_teacher(teacher_id)` — `db.py:95`
```python
supabase.table('attendance_logs')
  .select("*, subjects!inner(*)")
  .eq('subjects.teacher_id', teacher_id)
  .execute()
```
- **Table**: attendance_logs with inner join on subjects
- **Type**: SELECT with filtered join
- **Note**: `subjects!inner(*)` means only return attendance_logs that have a matching subject owned by this teacher. Filters cross-teacher data correctly.

### Inline Supabase queries (in dialogs, not db.py)

`dialog_enroll.py` and `dialog_auto_enroll.py` both query `subjects` and `subject_students` directly without going through `db.py`. This bypasses the data layer.

`dialog_voice_attendance.py` queries `subject_students` with nested `students(*)` directly.

`teacher_screen.py` queries `subject_students` with nested `students(*)` directly in the face scan flow.

---

## Attendance Session Concept

There is no separate "sessions" table. A session is inferred by grouping `attendance_logs` rows with the same `timestamp`. When a teacher runs attendance, all rows inserted at that moment share one ISO timestamp string — this is how `get_teacher_subjects()` counts `total_classes` using `set(log['timestamp'] for log in attendance)`.
