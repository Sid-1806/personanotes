# Personalized AI Notes Generator (PersonaNotes)

An AI-powered lecture note generator that learns your note-taking style from historical notes and generates personalized notes using Retrieval-Augmented Generation (RAG).

## Problem Statement
Generic AI summaries often fail to match the specific formatting, tone, and depth required by students and professionals. PersonaNotes solves this by analyzing your historical notes to automatically infer a personalized "Style Profile." When you upload new lectures, the application uses RAG to generate notes that look and feel like you wrote them yourself.

## Core Workflow
1. **Teach your style**: Import a few notes you wrote yourself. The system infers 16 style
   attributes (headings, bullet usage, tone, example density, table and diagram frequency, …),
   each with a confidence score. This runs *first* so your very first generated note already
   sounds like you.
2. **Organise by course**: Lectures and notes live inside courses, which scope search,
   questions and generation.
3. **Upload material**: PDFs, images, text or markdown — one file or a whole week. Scans and
   photos are read with OCR. Files are parsed, chunked per page, embedded with
   `sentence-transformers` and indexed in Qdrant.
4. **Generate**: Pick a preset — full notes, summary, key concepts, practice questions or a
   cheat sheet — and Gemini 2.5 Flash writes it from your retrieved material, in your style.
   Generation streams, and shows which sections it found before it starts writing.
5. **Read, ask and refine**: Notes render with GitHub-flavoured markdown, LaTeX maths,
   syntax-highlighted code and Mermaid diagrams, with a table of contents and expandable
   citations. Ask questions about a note, lecture or whole course and get cited answers.
6. **Continual learning**: Edit a note and save it. Your version is kept as the note's body
   (the original stays available for comparison), and the system learns what you changed —
   unless you've pinned that attribute by hand.

Every generation, revision and edit is a version you can compare and roll back, and
everything exports as markdown.

## Architecture
- **Backend**: FastAPI with Python 3.11
- **Database**: PostgreSQL (user data, courses, notes, style profiles) & Qdrant (vector embeddings)
- **AI Models**: Google Gemini 2.5 Flash (generation, OCR), SentenceTransformers `all-MiniLM-L6-v2` (embeddings, local)
- **Frontend**: Next.js 15 (React 19, TailwindCSS v4)
- **Optional**: Redis for response caching and per-user rate limiting — without it both fall
  back to an in-process backend, so the app still runs.

See [`docs/architecture.md`](docs/architecture.md) for the pipelines in detail, and
[`CONTEXT.md`](CONTEXT.md) for a working map of the repo.

## Setup Instructions

### Prerequisites
- Docker & Docker Compose
- Node.js 18+

### Production Deployment
PersonaNotes is fully containerized. To run the full stack (Frontend, Backend, Postgres, Qdrant):
```bash
docker-compose up -d --build
```
The application will be available at `http://localhost:3000`.

### Local Development Setup

**1. Backend**
Copy `.env.example` to `backend/.env` and add your Gemini API Key.
```bash
cd backend
python -m venv venv
# On Windows: .\venv\Scripts\activate
# On Mac/Linux: source venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

**2. Frontend**
```bash
cd frontend
npm install
npm run dev
```
Visit `http://localhost:3000` in your browser.

## Testing

```bash
cd backend && pytest          # 49 unit tests, no database required
cd frontend && npx tsc --noEmit && npm run build
```
