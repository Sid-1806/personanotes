# Architecture Overview

PersonaNotes leverages a multi-pipeline architecture:

## 1. RAG & Knowledge Pipeline
- **Parsing**: PDFs are uploaded and text is extracted.
- **Chunking**: Text is split into semantically coherent segments.
- **Embedding**: SentenceTransformers (MiniLM-L6-v2) vectorizes the chunks.
- **Storage**: Vectors are indexed in Qdrant.

## 2. Style Learning & Feedback Pipeline
When a user edits a generated note:
1. The **Diff Engine** compares the AI output with the User Edit.
2. The **Feature Extractor** computes deterministic metrics (e.g., example density, list usage).
3. The **Style Updater** merges these deltas with the existing `StyleProfile` and increments the version.
4. The **Evaluation Engine** generates a `Personalization Score` that is tracked on the Evaluation Dashboard.

## 3. Knowledge Workspace
A polymorphic DTO aggregates `Lectures`, `GeneratedNotes`, and `HistoricalNotes` into a unified interface, supporting collections, tags, and semantic search queries routed through Qdrant.
