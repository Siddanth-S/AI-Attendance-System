# Face Recognition Pipeline

**File**: `src/pipelines/face_pipeline.py`

This pipeline does two distinct things:
1. **Embedding extraction** — convert a raw image into a 128-number vector that represents a face
2. **Identity prediction** — given a new face vector, figure out which student it belongs to

---

## The ML Stack

```
Raw Image (numpy array, RGB)
       │
       ▼
dlib HOG Detector          ← Finds face bounding boxes in the image
       │
       ▼
dlib Shape Predictor       ← Finds 68 facial landmark points (eyes, nose, mouth, jawline)
       │
       ▼
dlib Face Recognition Net  ← Deep neural network → 128-dimensional embedding vector
       │
       ▼
scikit-learn SVC           ← Classifies embedding → student_id
       │
       ▼
Euclidean Distance Check   ← Rejects poor matches (distance > 0.6)
```

---

## Function: `load_dlib_models()`

**Line**: 13  
**Decorator**: `@st.cache_resource` — runs ONCE per server process. Results are cached in memory permanently (until cache is cleared).

**What it loads**:
- `dlib.get_frontal_face_detector()` — pre-built HOG + SVM face detector
- `dlib.shape_predictor(...)` — 68-point facial landmark detector. Model file path comes from `face_recognition_models` package
- `dlib.face_recognition_model_v1(...)` — ResNet-based model that produces 128-dim embeddings

**Why cache**: dlib model files are large (~100MB total). Loading them on every Streamlit re-render would take 2-5 seconds and make the app unusable.

**Returns**: `(detector, sp, facerec)` — three dlib model objects

---

## Function: `get_face_embeddings(image_np)`

**Line**: 27  
**Called from**: `student_screen.py` (registration), `face_pipeline.predict_attendance()`

**Input**: `image_np` — RGB numpy array (H × W × 3)

**Steps**:
1. Loads the three dlib models via `load_dlib_models()`
2. `detector(image_np, 1)` — detects face rectangles. The `1` means upsample once (better at small faces)
3. For each detected face rectangle:
   - `sp(image_np, face)` — computes 68 landmark coordinates
   - `facerec.compute_face_descriptor(image_np, shape, 1)` — the `1` is `num_jitters`: averages the embedding over 1 random jitter for stability
   - Converts dlib vector → numpy array
4. Returns list of 128-dim numpy arrays (one per detected face)

**Output**: `List[np.ndarray]` — each array has shape `(128,)`

**Edge cases**:
- Zero faces → returns empty list
- Multiple faces → returns one embedding per face
- The embedding is deterministic given the same image and jitter count

**Why 128 dimensions**: This is the output size of dlib's ResNet face model. It's a projection into a space where the same person's faces cluster together and different people's faces are far apart (metric learning).

---

## Function: `get_trained_model()`

**Line**: 41  
**Decorator**: `@st.cache_resource` — cached until `st.cache_resource.clear()` is called

**What it does**: Fetches all students from Supabase and trains an SVC on their face embeddings.

**Steps**:
1. Calls `get_all_students()` from `db.py` — returns ALL students with embeddings
2. Builds `X` (list of 128-dim arrays) and `y` (list of student_ids)
3. Filters out students with no face embedding
4. Creates `SVC(kernel='linear', probability=True, class_weight='balanced')`
   - `linear` kernel: works well in high-dimensional spaces (128 dims), fast
   - `probability=True`: enables probability estimates (not actually used in predict, but set)
   - `class_weight='balanced'`: handles class imbalance (some students may have more photos)
5. `clf.fit(X, y)` — trains the classifier
6. Returns `{'clf': clf, 'X': X, 'y': y}`

**Returns**:
- `None` — no students in database
- `0` — students exist but none have face embeddings
- `dict` — `{'clf': SVC, 'X': list, 'y': list}`

**Critical design decision**: The SVC is retrained from scratch every time a new student registers. There's no incremental learning. For a class of 50 students this is fine (sub-second training).

---

## Function: `train_classifier()`

**Line**: 70  
**Called from**: `student_screen.py` after successful student registration

**What it does**:
1. `st.cache_resource.clear()` — **clears ALL cached resources** (both dlib models AND the trained SVC)
2. Calls `get_trained_model()` which re-fetches students and retrains

**Side effect**: Clearing ALL cache means dlib models also need to reload next time `get_face_embeddings` is called. This is a performance hit.

**Returns**: `bool` — whether training succeeded

---

## Function: `predict_attendance(class_image_np)`

**Line**: 75  
**Called from**: `teacher_screen.py` (face scan tab), `student_screen.py` (face login)

**Input**: `class_image_np` — RGB numpy array of the classroom photo

**Steps**:
1. `get_face_embeddings(class_image_np)` — get list of embeddings for all faces in image
2. `get_trained_model()` — get trained SVC (from cache if available)
3. If no model: return early with `({}, [], num_faces)`
4. For each face encoding:
   - **If 2+ students enrolled**: `clf.predict([encoding])` → predicted student_id
   - **If only 1 student**: skip SVC, directly assign that one student_id
     - Reason: SVC needs at least 2 classes. With 1 student, any face is them.
   - Get the actual stored embedding of the predicted student: `X_train[y_train.index(predicted_id)]`
   - Compute Euclidean distance: `np.linalg.norm(student_embedding - encoding)`
   - **Threshold check**: if distance ≤ 0.6 → mark present
   - The threshold 0.6 means: accept the SVC's guess only if the face is actually close in embedding space

**Output**: `(detected_student, all_students, num_faces)`
- `detected_student`: `{student_id: True}` for confirmed matches
- `all_students`: sorted list of all known student_ids
- `num_faces`: how many faces were detected in the image

**Why the double check (SVC + distance)**:
SVC tells you the closest class, but doesn't tell you if the face is actually close enough. A face that belongs to no enrolled student would still get assigned to someone. The Euclidean distance check rejects faces that are too far from ANY known student.

---

## Embedding Storage Format

Face embeddings are stored in Supabase as JSON arrays:
- Registered as: `encodings[0].tolist()` — converts numpy array to Python list
- Retrieved as: Python list (JSON-parsed by Supabase client)
- Converted back: `np.array(embedding)` in `get_trained_model()`

---

## Why This Works at Small Scale

At ~30 students per class with one embedding per student, this approach is fast and accurate. At scale (thousands of students), you'd need:
- A vector database (Pinecone, pgvector) instead of storing in regular columns
- Approximate nearest neighbor search instead of SVC
- Storing multiple embeddings per student (different lighting, angles)
