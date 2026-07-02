# Voice Recognition Pipeline

**File**: `src/pipelines/voice_pipeline.py`

The voice pipeline identifies who is speaking in an audio recording. It is used for voice-based attendance: a teacher records the class saying "I am present" and the system identifies each speaker.

---

## The ML Stack

```
Raw Audio Bytes
       │
       ▼
librosa.load()             ← Decode audio, resample to 16kHz mono
       │
       ▼
librosa.effects.split()    ← Find voice segments (voice activity detection)
       │   (only in bulk mode)
       ▼
resemblyzer.preprocess_wav ← Normalize amplitude, trim silence
       │
       ▼
VoiceEncoder.embed_utterance() ← GE2E model → 256-dim speaker embedding
       │
       ▼
Cosine Similarity           ← Compare against stored embeddings
       │
       ▼
Threshold (0.65)            ← Accept or reject match
```

---

## Function: `load_voice_encoder()`

**Line**: 9  
**Decorator**: `@st.cache_resource`

**What it loads**: `VoiceEncoder()` from resemblyzer — this is a pre-trained GE2E (Generalized End-to-End) model. It was trained on thousands of speakers to produce embeddings where the same person's voice is close in vector space and different people's voices are far apart.

**Why cache**: The GE2E model is a neural network that takes time to load from disk.

---

## Function: `get_voice_embedding(audio_bytes)`

**Line**: 13  
**Called from**: `student_screen.py` during registration

**Input**: `audio_bytes` — raw bytes from `st.audio_input().read()`

**Steps**:
1. `librosa.load(io.BytesIO(audio_bytes), sr=16000)` — decodes audio (any format), forces 16kHz sample rate and mono
2. `preprocess_wav(audio)` — resemblyzer's normalization function: trims silence, normalizes amplitude
3. `encoder.embed_utterance(wav)` — runs the GE2E network, produces a 256-dim numpy array
4. `.tolist()` — converts to Python list for JSON storage in Supabase

**Output**: `List[float]` (256 values) or `None` on error

**Error handling**: Entire function is wrapped in try/except. If audio is too short, corrupt, or wrong format — returns `None` and shows `st.error()`

---

## Function: `identify_speaker(new_embedding, candidates_dict, threshold=0.65)`

**Line**: 26  
**Called from**: `process_bulk_audio()` for each audio segment

**Input**:
- `new_embedding`: 256-dim list/array from a voice segment
- `candidates_dict`: `{student_id: voice_embedding}` for all enrolled students who have voice profiles
- `threshold`: minimum cosine similarity to accept a match (default 0.65)

**Algorithm**:
1. Loop through all candidates
2. For each: `np.dot(new_embedding, stored_embedding)` — cosine similarity
   - This works correctly ONLY if both vectors are unit-normalized. GE2E embeddings from resemblyzer are L2-normalized by default, so dot product = cosine similarity.
3. Track the best (highest) similarity and its student_id
4. If best score ≥ 0.65 → return that student_id
5. If best score < 0.65 → return None (no match)

**Returns**: `(student_id | None, score)`

**Why cosine similarity**: Speaker embeddings represent direction in high-dimensional space, not magnitude. Two recordings of the same person should point in the same direction even if loudness varies.

---

## Function: `process_bulk_audio(audio_bytes, candidates_dict, threshold=0.65)`

**Line**: 47  
**Called from**: `dialog_voice_attendance.py`

**Input**:
- `audio_bytes`: full classroom audio recording
- `candidates_dict`: `{student_id: voice_embedding}` for enrolled students

**Steps**:
1. Loads audio at 16kHz
2. `librosa.effects.split(audio, top_db=30)` — Voice Activity Detection (VAD). Returns list of `(start_sample, end_sample)` tuples where audio is at least 30dB above silence.
3. For each segment:
   - Skip if shorter than 0.5 seconds (`< sr * 0.5` samples)
   - Preprocess and embed
   - Call `identify_speaker()` against all candidates
   - If match found and score is better than previous match for that student → store it
4. Returns `{student_id: best_score}` for all identified speakers

**Why keep only the best score per student**: A student might say multiple phrases. Only the highest-confidence match is kept.

**Returns**: `{student_id: float}` — only includes students who were positively identified

**Error handling**: Wrapped in try/except, returns empty dict on failure

---

## How Enrollment and Identification Connect

**Enrollment** (student_screen.py):
```
st.audio_input() → .read() → get_voice_embedding() → .tolist() → Supabase students.voice_embedding
```

**Identification** (dialog_voice_attendance.py):
```
Supabase subject_students → students.voice_embedding (for enrolled students)
→ candidates_dict = {student_id: voice_embedding}
→ st.audio_input() → .read() → process_bulk_audio(audio_bytes, candidates_dict)
→ {student_id: score}
```

---

## Key Design Choices

**Single enrollment utterance**: Each student provides one voice sample during registration. Production systems typically use multiple utterances to average the embedding.

**Threshold 0.65**: This is a judgment call. Too high → false negatives (students not recognized). Too low → false positives (wrong student matched). 0.65 is a reasonable starting point for clean audio.

**VAD minimum 0.5 seconds**: Filters out background noise bursts, keyboard clicks, or very short utterances that can't produce reliable embeddings.

**Voice attendance is optional**: `voice_embedding` in the students table is nullable. `candidates_dict` in the voice dialog only includes students who have a voice embedding. Students without voice profiles can never be identified by voice.
