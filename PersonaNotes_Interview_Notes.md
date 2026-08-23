# PersonaNotes — Interview Preparation Notes

## 1. Core Architecture

```text
Next.js frontend
      ↓
     Axios
      ↓
    FastAPI
      ↓
 ┌────┼─────────────┐
 ↓    ↓             ↓
Auth  Routers    Services
 ↓    ↓             ↓
JWT  Handlers    LLM/RAG
 ↓    ↓             ↓
PostgreSQL      Qdrant + Gemini
                    ↓
              Generated Notes
                    ↓
                 Feedback
                    ↓
              Style Profile
```

---

# 2. Authentication

## JWT + bcrypt

### Login

```text
Email + Password
       ↓
get_db()
       ↓
PostgreSQL → find User
       ↓
bcrypt.verify(password, stored_hash)
       ↓
Valid
       ↓
Create signed JWT
       ↓
JWT → client
```

- JWT expiration = 30 minutes.
- Current JWT `sub` = user's email.
- Current JWT is stored in `localStorage`.
- JWT is signed, not encrypted.

### Protected request

```text
Client
 ↓
Axios interceptor
 ↓
Authorization: Bearer JWT
 ↓
FastAPI
 ↓
get_current_user
 ↓
Verify JWT
 ↓
Extract sub/email
 ↓
get_db()
 ↓
PostgreSQL → User
 ↓
Handler
```

### Security improvement

Prefer an immutable `user.id` as JWT `sub` instead of email.

---

# 3. Password Hashing

**bcrypt**

- Slow password hashing algorithm.
- Uses salt.
- Designed to make brute-force attacks expensive.
- Verifies supplied password against stored hash.

Important distinction:

```text
bcrypt → password protection
JWT    → authenticated identity/session representation
```

---

# 4. FastAPI Dependencies

## `get_db`

```text
get_db()
   ↓
yield session
   ↓
handler uses session
   ↓
cleanup
```

## `get_current_user`

```text
JWT
 ↓
jose verifies signature
 ↓
extract sub
 ↓
get_db
 ↓
query PostgreSQL
 ↓
User object
```

---

# 5. Async / Event Loop

One event-loop thread can run many coroutines.

```text
Request A → await DB → yields
Request B → await DB → yields
Request C → await API → yields
```

This gives **concurrency**, not necessarily parallelism.

A blocking synchronous call can freeze the event-loop thread, so blocking LLM/feedback work is offloaded to a threadpool.

## AnyIO / Threadpool

FastAPI/Starlette `run_in_threadpool()` uses AnyIO internally:

```text
FastAPI
 ↓
Starlette
 ↓
AnyIO
 ↓
anyio.to_thread.run_sync
```

Default AnyIO thread limiter:

- 40 tokens per event loop/process.
- With `N` worker processes, capacity is roughly `40 × N`.
- Each process has its own limiter.

Important scaling issue: sync background tasks share the same limiter.

---

# 6. Middleware / Request Flow

Explicitly registered middleware:

**CORSMiddleware**

Exception handlers:

- `AppError`
- global `Exception`

Starlette's request flow is approximately:

```text
ServerErrorMiddleware
        ↓
CORSMiddleware
        ↓
ExceptionMiddleware
        ↓
Router
        ↓
Dependencies
        ↓
Handler
```

CORS can handle preflight `OPTIONS` requests before normal routing.

---

# 7. Axios

`frontend/src/lib/api.ts`

## Request interceptor

```text
Request
 ↓
Read JWT from localStorage
 ↓
Authorization: Bearer <token>
 ↓
Backend
```

## Response interceptor

On `401`:

```text
401
 ↓
remove token
 ↓
hard redirect to /login
```

Current implementation uses `window.location` for the redirect.

---

# 8. React Query

React Query manages **server state**.

Authentication has:

```text
loginMutation
registerMutation
userQuery
```

User query key:

```text
["user"]
```

Login:

```text
login
 ↓
store JWT in localStorage
 ↓
invalidate ["user"]
 ↓
refetch /users/me
```

Logout:

```text
remove JWT
 ↓
set ["user"] = null
```

React Query provides:

- caching
- refetching
- invalidation
- mutations

Important distinction:

> JWT in localStorage is the authentication token; React Query caches the derived server-side User object.

---

# 9. RAG

RAG = Retrieval-Augmented Generation.

```text
User query
 ↓
Embedding
 ↓
Retrieve relevant stored text
 ↓
Put retrieved text into prompt
 ↓
LLM
 ↓
Grounded answer
```

**The LLM receives text, not vectors.**

---

# 10. Lecture Ingestion

Exact pipeline:

```text
upload_lecture
      ↓
save_lecture
      ↓
process_lecture_background
      ↓
parse_document
      ↓
get_text_chunks
      ↓
generate_embeddings
      ↓
store_lecture_chunks
      ↓
Qdrant
```

Chunking:

- `RecursiveCharacterTextSplitter`
- Chunk size: 1000 characters
- Overlap: 100 characters

Embeddings:

- `all-MiniLM-L6-v2`
- 384 dimensions

Qdrant payload:

```json
{
  "user_id": "...",
  "lecture_id": "...",
  "text": "..."
}
```

---

# 11. Embeddings

Embedding model maps text into a vector.

```text
Text
 ↓
all-MiniLM-L6-v2
 ↓
384-dimensional vector
```

The **same model** is used for both:

1. Lecture/chunk embeddings.
2. Query embeddings.

Both must live in the same vector space for meaningful similarity comparison.

---

# 12. Semantic Search

Semantic search asks:

> Which stored text has similar meaning to the query?

Know these retrieval approaches:

### Keyword / lexical

Exact word-based matching.

### TF-IDF

Weights terms according to importance/frequency.

### BM25

Probabilistic lexical retrieval.

### Vector / semantic search

Uses embeddings and vector similarity.

### Hybrid search

Combines lexical and vector retrieval.

```text
BM25 + Vector Search
        ↓
Combined ranking
```

---

# 13. Qdrant Retrieval

Current generation flow:

```text
User prompt
 ↓
all-MiniLM-L6-v2
 ↓
384-dimensional query vector
 ↓
Qdrant
 ↓
user_id filter
 ↓
ANN search
 ↓
cosine similarity
 ↓
top 5
 ↓
chunk TEXT
 ↓
Gemini
```

Qdrant returns chunk text directly from its payload.

There is **no PostgreSQL lookup after retrieval** for the actual chunk text.

---

# 14. Cosine Similarity

Formula:

\[
\cos(\theta)=
\frac{A\cdot B}
{\|A\|\|B\|}
\]

It measures the angle between two vectors.

```text
Smaller angle
     ↓
Higher cosine similarity
     ↓
More similar
```

Intuition:

```text
0°   → cosine ≈ 1
90°  → cosine = 0
180° → cosine ≈ -1
```

The important conceptual point:

> Cosine similarity is the **similarity/distance metric**, not the search algorithm.

---

# 15. ANN / HNSW

ANN = Approximate Nearest Neighbor.

## Exact / Flat search

```text
Query
 ↓
Compare against every vector
 ↓
Rank everything
```

Exact, but expensive at scale.

## ANN

```text
Query
 ↓
Use index to find promising candidates
 ↓
Top-k
```

Much faster, but approximate.

## HNSW

HNSW = Hierarchical Navigable Small World.

It is a graph-based ANN index.

Important distinction:

```text
ANN       → retrieval/search approach
HNSW      → index/search structure
Cosine    → similarity metric
```

---

# 16. Vector Index Alternatives

## Flat / Brute Force

Exact search.

**Pros:** exact result.  
**Cons:** expensive at scale.

## HNSW

Graph-based ANN.

**Pros:** strong speed/recall.  
**Cons:** memory-heavy.

## IVF

Clusters vectors and searches selected clusters.

**Pros:** reduces search space.  
**Cons:** recall/speed depends on how many clusters are probed.

## IVF + PQ

```text
IVF → reduce search space
PQ  → compress vectors
```

Useful for large collections and memory reduction.

## PQ

Compresses vectors.

**Pros:** memory efficient.  
**Cons:** approximate representation can reduce recall.

## DiskANN

Graph-based ANN designed for very large collections and SSD/disk-oriented storage.

### Interview priority

Know deeply:

1. Flat
2. HNSW
3. IVF

Know conceptually:

4. IVF + PQ
5. PQ
6. DiskANN

---

# 17. Qdrant Configuration

Current collection:

```text
vector size = 384
distance = COSINE
```

No explicit HNSW configuration, so Qdrant defaults apply:

```text
m = 16
ef_construct = 100
full_scan_threshold ≈ 10000
```

There is currently no payload index on `user_id`.

---

# 18. LLM Service / Prompt Assembly

Core flow:

```text
search_qdrant()
      ↓
retrieve chunks

generate_notes()
      ↓
assemble prompt
      ↓
Gemini
```

Gemini receives:

```text
System instructions
+
User style profile
+
Retrieved lecture text
+
User prompt
```

---

# 19. Style Profile — 16 Attributes

The 16 attributes:

1. `heading_style`
2. `section_order`
3. `bullet_style`
4. `average_sentence_length`
5. `average_paragraph_length`
6. `heading_depth`
7. `bullet_frequency`
8. `diagram_frequency`
9. `table_frequency`
10. `code_block_frequency`
11. `example_density`
12. `summary_position`
13. `keyword_highlighting`
14. `tone`
15. `preferred_sections`
16. `formatting_preferences`

Each uses:

```text
FeatureValue
├── value
├── confidence
├── reason
└── last_updated
```

There is also `source_contributions`, which is additional data rather than a FeatureValue.

---

# 20. Why Confidence?

The profile should not blindly rely on one document.

Example:

```text
Document 1
few bullets
 ↓
weak evidence

Document 2
many bullets
 ↓
new evidence

Document 3
many bullets
 ↓
stronger evidence
```

Confidence represents the strength of the current evidence.

The profile evolves over time.

---

# 21. Gemini → Flat → Nested

Style analysis:

```text
Document
 ↓
Gemini
 ↓
Flat attributes
 ↓
_profile_from_flat()
 ↓
StyleProfileSchema
```

Gemini can produce a simple flat representation, which is then wrapped into the application's structured schema.

---

# 22. `summarize_style_for_prompt`

The complete internal style profile is not sent directly to Gemini.

It produces a compact representation:

```text
StyleProfile
 ↓
summarize_style_for_prompt()
 ↓
compact style JSON
 ↓
Gemini prompt
```

It drops:

- confidence
- reason
- timestamp
- source contributions
- empty fields
- fields with confidence ≤ 0.5

It inserts a **USER STYLE PROFILE JSON** block between system instructions and retrieved excerpts.

---

# 23. Feedback / Learning Pipeline

```text
Generated note
      +
User edited note
      ↓
feature_extractor
      ↓
deterministic metrics
      ↓
diff_engine
      ↓
thresholded differences
      ↓
feedback updater
      ↓
confidence-weighted update
      ↓
StyleProfile
```

Subjective tone feedback uses Gemini.

Structural features are deterministic/regex-based.

---

# 24. Thresholded Diffs

Small changes shouldn't automatically change the user's learned style.

Conceptually:

```text
difference
 ↓
threshold
 ↓
significant?
 ├── NO  → ignore
 └── YES → update profile
```

Example:

```text
Generated = 10 bullets
Edited    = 11 bullets
```

May not be strong evidence.

But:

```text
Generated = 3 bullets
Edited    = 12 bullets
```

is stronger evidence.

---

# 25. Style Update Math

There are **three update schemes**.

## A. `merge_profiles`

Numeric:

\[
(old+new)/2
\]

Categorical:

```text
prefer new
```

Lists:

```text
union
```

## B. Feedback updater

```text
new =
value + delta × 0.2 × (1 - confidence + 0.1)
```

## C. Historical merger

Uses the weighted numeric update and then forces:

```text
confidence += 0.3
```

### Problems

- Three different update schemes affect the same fields.
- Frequency deltas are per-1000-words.
- Baselines may be raw or unspecified counts.

This is a unit-consistency problem.

---

# 26. Profile Convergence

Current weight:

\[
0.2(1-confidence+0.1)
\]

At confidence = 1:

\[
weight = 0.02
\]

Therefore the weight never becomes zero.

So even a high-confidence profile can continue drifting.

Potential principled approaches:

- Freeze above a confidence threshold.
- Confidence decay.
- Bayesian/running-mean approach.

---

# 27. Evaluation — Now Wired

Current flow:

```text
submit_note_feedback
       ↓
evaluate_generation()
       ↓
evaluate_all_metrics()
       ↓
compute_overall_score()
       ↓
StyleFeedback.feedback_json["evaluation"]
       ↓
Dashboard
```

Evaluation is now connected.

It is used for:

- measurement
- observability
- personalization score/trend

It **does not feed the result back into profile updating**.

---

# 28. Evaluation Metrics

Current evaluation is mainly **structural similarity**.

It measures things such as:

- heading depth
- formatting/code/tables
- word-count proxy
- sentence length
- example presence
- character-level `SequenceMatcher` edit distance

Edit distance has weight:

```text
0.30
```

### Important limitation

It does **not** measure:

- semantic quality
- factual correctness
- educational usefulness

Also:

> Edit distance can confuse content changes with style changes.

---

# 29. Evaluation Caveat — Feedback Bias

Learning/evaluation depends on explicit user edits.

There are currently no implicit signals such as:

- dwell time
- accept/reject
- used-as-is

Therefore:

```text
User edits
 ↓
StyleFeedback
 ↓
Evaluation
```

But:

```text
User doesn't edit
 ↓
No StyleFeedback
 ↓
No evaluation trend
```

So the evaluation primarily reflects users who actively provide feedback.

Potential improvements:

- implicit feedback signals
- periodic explicit preference collection

---

# 30. PostgreSQL / JSONB

PostgreSQL is the relational database.

JSONB is used for flexible nested data such as style profiles.

Benefits:

- flexible structure
- nested data
- indexable JSON
- avoids creating a separate relational column for every style feature

---

# 31. SQLAlchemy Async / asyncpg

Architecture:

```text
Python
 ↓
SQLAlchemy ORM
 ↓
asyncpg
 ↓
PostgreSQL
```

SQLAlchemy:

> Maps Python classes to relational tables.

asyncpg:

> Async PostgreSQL driver.

`expire_on_commit=False` prevents ORM attributes from expiring after commit and requiring an implicit database reload.

This fixed the project's `MissingGreenlet` issue.

---

# 32. 9-Table Data Model

| Table | Purpose |
|---|---|
| `users` | Users |
| `lectures` | Uploaded lectures |
| `style_profiles` | Current style profile |
| `style_profile_versions` | Profile history/versions |
| `generated_notes` | Generated notes |
| `edited_notes` | User corrections |
| `style_feedback` | Feedback/evaluation |
| `historical_notes` | Imported historical notes |
| `background_tasks` | Currently unused |

`style_profiles.user_id` is UNIQUE → one profile per user.

Most models use raw foreign keys/manual queries; `Lecture` defines ORM relationships.

---

# 33. Docker

Four services:

```text
PostgreSQL
Qdrant
FastAPI backend
Next.js frontend
```

Current configuration:

- PostgreSQL 15-alpine: host `5433` → container `5432`
- Qdrant: `6333` / `6334`
- Backend: `8000`
- Frontend: `3000`

Current limitations:

- single-stage/root images
- single Uvicorn process
- `depends_on` doesn't guarantee readiness
- local volumes
- no healthchecks
- no horizontal scaling configuration

---

# 34. Main Project Problems / Flags

## 1. Cross-tenant retrieval — FIXED

Originally retrieval lacked `user_id` filtering.

Potential problem:

```text
User A
 ↓
Qdrant
 ↓
User B's chunks
```

Fixed by filtering Qdrant retrieval using:

```text
user_id == current_user.id
```

This is a strong **"found and fixed"** interview story.

---

## 2. Non-durable ingestion

`BackgroundTasks` is in-process.

If the server restarts during embedding:

```text
PostgreSQL:
Lecture exists

Qdrant:
Vectors don't exist
```

No durable retry/status mechanism currently.

Production improvement:

```text
Upload
 ↓
Durable Queue
 ↓
Worker
 ↓
Embedding
 ↓
Qdrant
```

Track:

```text
PENDING
PROCESSING
COMPLETED
FAILED
```

with retries/backoff/dead-letter handling.

---

## 3. Vector model migration

Changing the embedding model/dimension isn't automatically detected.

Current initialization only checks collection name.

Better:

- versioned collection names
- dimension/model validation
- re-embedding/backfill

---

## 4. Vector idempotency

Current vectors use random UUIDs.

Reprocessing a lecture creates new vectors and can duplicate data.

Better:

```text
lecture_id + chunk_index
```

as deterministic IDs, combined with delete-before-reindex or upsert.

---

## 5. Style math inconsistency

Problems:

- mixed units
- three update schemes
- same fields can be modified using different policies

Better:

> Define one canonical representation and one update mechanism.

---

## 6. Profile never truly converges

The update weight remains non-zero.

Therefore the profile can drift forever.

---

## 7. Evaluation gap

Previously unwired; **now connected**.

Remaining caveat:

> Current evaluation measures structural personalization, not semantic quality.

---

# 35. Security Problems

Current gaps:

### JWT

- Email as JWT `sub`
- localStorage token storage
- no token revocation

### Authentication

- User enumeration via login timing
- No rate limiting

### Error handling

- Global exception handler exposes `str(exc)`

### File handling

- Historical importer has filename path-traversal risk
- Lecture upload filenames are randomized and safer

### Secrets

- Demo `SECRET_KEY` in Docker Compose

### CORS

- Explicit origins are configured.
- `allow_credentials=True` is unnecessary for bearer-token authentication.

### Authorization

The project currently correctly scopes:

- PostgreSQL queries by user ID
- Qdrant retrieval by `user_id`

### Prompt injection

Retrieved text is untrusted and enters LLM context.

The blast radius is limited because the LLM has no exposed tools, but the issue should still be considered.

---

# 36. Security Improvements

## JWT subject

Current:

```json
{
  "sub": "user@email.com"
}
```

Better:

```json
{
  "sub": "immutable-user-id"
}
```

Then `get_current_user()` queries by ID.

## JWT storage

Current:

```text
localStorage
```

Risk:

> XSS can access the token.

Production alternative:

```text
HttpOnly
Secure
SameSite cookie
```

with appropriate CSRF protection.

## Exception handling

Client:

```text
Generic error + request ID
```

Server:

```text
Full exception + request ID in logs
```

---

# 37. Scaling Problems

### Local uploads

Multiple replicas:

```text
Load Balancer
   ├── Server 1 → local file
   └── Server 2 → cannot see Server 1's file
```

Use object/shared storage.

### Embedding model per worker

Each process may load its own copy of the model → increased memory usage.

### Threadpool exhaustion

The default AnyIO limiter is ~40 tokens/process.

Concurrent Gemini calls can occupy the pool and delay unrelated sync work.

### Gemini

Current concerns:

- no rate limiting
- no backoff
- no circuit breaker

### Database

No explicit SQLAlchemy pool sizing configured.

### Caching

No caching currently.

Potential caches must account for personalization/user/style-profile versions so one user's result isn't incorrectly reused for another.

---

# 38. Dead / Placeholder Code

Currently identified:

- `background_tasks` table unused
- `LLMServiceError` unused
- `FileProcessingError` unused
- `AdvancedEditor` unused
- duplicated evaluation metric logic
- `benchmark.compute_benchmark` unused

Do **not** blindly delete these. Some may be intended scaffolding.

---

# 39. Alembic — Critical Issue

`migrations/env.py` currently imports only:

```text
User
Lecture
```

during migration metadata setup.

The other 7 models may therefore be absent from `Base.metadata`.

Danger:

```text
alembic revision --autogenerate
```

could incorrectly propose dropping existing tables.

Fix:

> Import all models before assigning `target_metadata = Base.metadata`.

This should be treated as a serious migration footgun.

---

# 40. RAG Quality Improvements

Current:

```text
Dense vector search
+
Qdrant
+
HNSW/ANN
+
cosine
+
top 5
+
user_id filter
```

Know these improvement techniques:

### Better chunking

- chunk size tuning
- overlap tuning
- recursive chunking
- semantic chunking
- parent-child chunks

### Better embeddings

Use stronger/domain-specific embedding models.

### Hybrid retrieval

```text
BM25 + Vector Search
```

### Re-ranking

```text
Vector search
 ↓
Top 20 candidates
 ↓
Re-ranker
 ↓
Top 5
```

### Query rewriting

Rewrite the user's query into a better retrieval query.

### Multi-query retrieval

Generate multiple query variations.

### Context compression

Remove irrelevant retrieved context before sending it to Gemini.

### Top-k tuning

Compare top-5, top-10, top-20, etc.

### Evaluation

Measure:

- retrieval recall/precision
- groundedness
- semantic quality
- human preference
- task performance

---

# 41. Technology Fundamentals Checklist

## 1. Async / Event Loop

One thread runs coroutines; `await` on I/O yields control.

## 2. RAG

Embed query → retrieve text → put text in prompt → LLM.

## 3. Embeddings

Text → N-dimensional vector.

PersonaNotes:

```text
384 dimensions
```

## 4. ANN / HNSW

Efficient approximate nearest-neighbor retrieval.

## 5. PostgreSQL / JSONB

Relational DB + flexible nested JSON.

## 6. SQLAlchemy / asyncpg

ORM + async PostgreSQL driver.

## 7. JWT / bcrypt

Signed authentication token + password hashing.

## 8. Pydantic

Runtime validation + typed API/config models.

## 9. React Query

Server-state cache/refetch/invalidation.

## 10. Next.js App Router

File-based routing; current project is heavily client-side.

---

# 42. Interview Follow-Up Framework

For every technology, be prepared to answer:

### What?
What does it do?

### Why?
Why did you use it?

### Alternative?
What else could you use?

### Trade-off?
What do you gain/lose?

### Failure?
What happens if it breaks?

### Scale?
What happens with 100× traffic?

### Security?
Could it introduce a vulnerability?

### Improvement?
What would you change for production?

### Project-specific?
Where exactly is it used in your code?

---

# 43. Highest-Priority Interview Topics

## Tier 1 — Know extremely well

1. Complete RAG pipeline
2. Qdrant + embeddings + cosine + HNSW
3. 16-attribute style profile
4. Feedback/update mathematics
5. Evaluation + limitations
6. JWT/authentication flow
7. Async/event loop/threadpool
8. 9-table database model

## Tier 2

9. React Query
10. Axios
11. Middleware
12. Docker
13. Security gaps
14. Durable ingestion
15. Scaling architecture

## Tier 3

16. IVF/PQ/DiskANN
17. Alembic internals
18. Dead-code cleanup
19. Advanced RAG improvements

---

# 44. Important "Found & Fixed" Stories

## Cross-tenant RAG bug

> Retrieval originally lacked user filtering, which could allow cross-user chunks to be retrieved. I identified the issue and added a `user_id` filter to Qdrant retrieval.

## `MissingGreenlet`

> `expire_on_commit=True` caused ORM attributes to expire after commit. Accessing them triggered an implicit database reload in an async context, resulting in `MissingGreenlet`. I fixed it using `expire_on_commit=False`.

These are particularly valuable interview stories because they demonstrate debugging rather than just implementation.

---

# 45. Honest Evaluation Caveats

Keep these ready:

### Caveat 1 — Structural ≠ semantic

> "Our current evaluation measures structural similarity such as headings, sentence length, formatting, and edit distance. It doesn't prove semantic quality, factual correctness, or educational usefulness."

Future improvements:

- semantic similarity
- groundedness
- task-level evaluation
- human preference evaluation

### Caveat 2 — Feedback-dependent

> "Our learning signal currently comes from explicit user edits, so users who don't edit their notes provide little direct personalization signal."

Potential improvements:

- implicit feedback
- accept/reject signals
- dwell time
- periodic explicit preferences
