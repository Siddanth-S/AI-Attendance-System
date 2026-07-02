# Function Call Graph

## Complete Dependency Map

```
app.py::main()
├── home_screen()
│   ├── style_background_home()
│   ├── style_base_layout()
│   ├── header_home()
│   └── footer_home()
│
├── teacher_screen()
│   ├── style_background_dashboard()
│   ├── style_base_layout()
│   ├── teacher_dashboard()
│   │   ├── header_dashboard()
│   │   ├── teacher_tab_take_attendance()
│   │   │   ├── get_teacher_subjects(teacher_id)       → db.py → Supabase
│   │   │   ├── add_photos_dialog()                    → dialog_add_photo.py
│   │   │   ├── predict_attendance(img_np)             → face_pipeline.py
│   │   │   │   ├── get_face_embeddings()
│   │   │   │   │   └── load_dlib_models()             [cached]
│   │   │   │   └── get_trained_model()                [cached]
│   │   │   │       └── get_all_students()             → db.py → Supabase
│   │   │   ├── supabase.table('subject_students')...  → Supabase [inline]
│   │   │   ├── attendance_result_dialog(df, logs)     → dialog_attendance_results.py
│   │   │   │   └── create_attendance(logs)            → db.py → Supabase
│   │   │   └── voice_attendance_dialog(subject_id)    → dialog_voice_attendance.py
│   │   │       ├── supabase.table(...)...             → Supabase [inline]
│   │   │       ├── process_bulk_audio()               → voice_pipeline.py
│   │   │       │   ├── load_voice_encoder()           [cached]
│   │   │       │   └── identify_speaker()
│   │   │       └── show_attendance_result(df, logs)
│   │   │           └── create_attendance(logs)        → db.py → Supabase
│   │   ├── teacher_tab_manage_subjects()
│   │   │   ├── get_teacher_subjects(teacher_id)       → db.py → Supabase
│   │   │   ├── create_subject_dialog(teacher_id)      → dialog_create_subject.py
│   │   │   │   └── create_subject()                   → db.py → Supabase
│   │   │   ├── subject_card(...)                      → subject_card.py
│   │   │   └── share_subject_dialog()                 → dialog_share_subject.py
│   │   │       └── segno.make()                       [QR generation]
│   │   ├── teacher_tab_attendance_records()
│   │   │   └── get_attendance_for_teacher()           → db.py → Supabase
│   │   └── footer_dashboard()
│   ├── teacher_screen_login()
│   │   ├── login_teacher()
│   │   │   └── teacher_login()                        → db.py → Supabase
│   │   │       └── check_pass()                       [bcrypt]
│   │   └── footer_dashboard()
│   └── teacher_screen_register()
│       ├── register_teacher()
│       │   ├── check_teacher_exists()                 → db.py → Supabase
│       │   └── create_teacher()                       → db.py → Supabase
│       │       └── hash_pass()                        [bcrypt]
│       └── footer_dashboard()
│
└── student_screen()
    ├── student_dashboard()
    │   ├── header_dashboard()
    │   ├── get_student_subjects(student_id)           → db.py → Supabase
    │   ├── get_student_attendance(student_id)         → db.py → Supabase
    │   ├── enroll_dialog()                            → dialog_enroll.py
    │   │   ├── supabase.table('subjects')...          → Supabase [inline]
    │   │   ├── supabase.table('subject_students')...  → Supabase [inline]
    │   │   └── enroll_student_to_subject()            → db.py → Supabase
    │   ├── subject_card(...)                          → subject_card.py
    │   ├── unenroll_student_to_subject()              → db.py → Supabase
    │   └── footer_dashboard()
    ├── predict_attendance(img_np)                     → face_pipeline.py (login mode)
    │   ├── get_face_embeddings()
    │   │   └── load_dlib_models()                     [cached]
    │   └── get_trained_model()                        [cached]
    │       └── get_all_students()                     → db.py → Supabase
    ├── get_all_students()                             → db.py → Supabase (post-login lookup)
    ├── get_face_embeddings(img_np)                    → face_pipeline.py (register mode)
    ├── get_voice_embedding(audio_bytes)               → voice_pipeline.py (register mode)
    │   └── load_voice_encoder()                       [cached]
    ├── create_student(name, face_emb, voice_emb)      → db.py → Supabase
    ├── train_classifier()                             → face_pipeline.py
    │   └── get_trained_model()                        → db.py → Supabase
    └── footer_dashboard()

app.py::main() [after screen render]
└── auto_enroll_dialog(join_code)                     → dialog_auto_enroll.py
    ├── supabase.table('subjects')...                  → Supabase [inline]
    ├── supabase.table('subject_students')...          → Supabase [inline]
    └── enroll_student_to_subject()                    → db.py → Supabase
```

---

## Database Function Map

Which `db.py` functions hit which Supabase tables:

| db.py Function | Table | Operation |
|---|---|---|
| `check_teacher_exists` | teachers | SELECT |
| `create_teacher` | teachers | INSERT |
| `teacher_login` | teachers | SELECT |
| `get_all_students` | students | SELECT ALL |
| `create_student` | students | INSERT |
| `create_subject` | subjects | INSERT |
| `get_teacher_subjects` | subjects + subject_students + attendance_logs | SELECT (join) |
| `enroll_student_to_subject` | subject_students | INSERT |
| `unenroll_student_to_subject` | subject_students | DELETE |
| `get_student_subjects` | subject_students + subjects | SELECT (join) |
| `get_student_attendance` | attendance_logs + subjects | SELECT (join) |
| `create_attendance` | attendance_logs | BULK INSERT |
| `get_attendance_for_teacher` | attendance_logs + subjects | SELECT (inner join) |

---

## Cached Resources Map

These are loaded once and live in memory until cleared:

| Function | What's Cached | Cleared When |
|---|---|---|
| `load_dlib_models()` | 3 dlib model objects (~100MB) | `train_classifier()` calls `st.cache_resource.clear()` |
| `get_trained_model()` | Trained SVC + X + y arrays | Same as above |
| `load_voice_encoder()` | GE2E VoiceEncoder neural net | Same as above |

Note: `train_classifier()` uses `st.cache_resource.clear()` which wipes ALL cached resources, including the dlib models. This is a side effect — after registration, the first face scan will be slower because dlib models must reload.
