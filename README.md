# Personalized AI Notes Generator (PersonaNotes)

An AI-powered lecture note generator that learns your note-taking style from historical notes and generates personalized notes using Retrieval-Augmented Generation (RAG).

## Problem Statement
Generic AI summaries often fail to match the specific formatting, tone, and depth required by students and professionals. PersonaNotes solves this by analyzing your historical notes to automatically infer a personalized "Style Profile." When you upload new lectures, the application uses RAG to generate notes that look and feel like you wrote them yourself.

## Core Workflow
1. **Upload**: Users upload lecture PDFs.
2. **Knowledge Pipeline**: Lectures are parsed, chunked, embedded via `sentence-transformers`, and indexed in a Qdrant vector database.
3. **Style Inference**: Users import historical notes. The system extracts style preferences (e.g., bullet usage, tone, verbosity) and saves them to a Style Profile.
4. **Generation**: The Gemini 2.5 Flash LLM uses RAG (retrieving the most relevant chunks of the lecture) alongside the user's active Style Profile to generate personalized notes.
5. **Continual Learning**: Users can edit the generated notes in the built-in Markdown editor. The system analyzes the edits to further refine the Style Profile.

## Architecture
- **Backend**: FastAPI with Python 3.11
- **Database**: PostgreSQL (User data, metadata, style profiles) & Qdrant (Vector embeddings)
- **AI Models**: Google Gemini (Generation), SentenceTransformers `all-MiniLM-L6-v2` (Embeddings)
- **Frontend**: Next.js 15 (React, TailwindCSS)

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
