/** Shared API types. */

export type IngestionStatus = "pending" | "processing" | "ready" | "failed";

export type NoteType =
  | "full"
  | "summary"
  | "key_concepts"
  | "practice"
  | "cheatsheet"
  | "custom"
  | "saved_answer";

export type Scope = "note" | "lecture" | "course" | "all";

export interface User {
  id: number;
  name: string;
  email: string;
  created_at: string;
}

export interface Course {
  id: number;
  name: string;
  code: string | null;
  color: string;
  archived: boolean;
  created_at: string;
  lecture_count: number;
  note_count: number;
  ready_lecture_count: number;
  processing_lecture_count: number;
  failed_lecture_count: number;
  last_activity_at: string | null;
}

export interface Lecture {
  id: number;
  user_id: number;
  filename: string;
  filetype: string;
  uploaded_at: string;
  course_id: number | null;
  course_name: string | null;
  title: string | null;
  ingestion_status: IngestionStatus;
  error_message: string | null;
  chunk_count: number;
  page_count: number;
  note_count: number;
}

export interface LectureText {
  id: number;
  page_count: number;
  chunk_count: number;
  text: string;
  truncated: boolean;
}

export interface Excerpt {
  lecture_id: number | null;
  lecture_title: string | null;
  note_id: number | null;
  note_title: string | null;
  page: number | null;
  score: number | null;
  kind: string | null;
  text: string;
}

export interface Grounding {
  chunks_used: number;
  lecture_ids: number[];
  top_score: number | null;
  excerpts: Excerpt[];
}

export interface NoteSummary {
  id: number;
  title: string | null;
  note_type: NoteType;
  lecture_id: number | null;
  lecture_title: string | null;
  course_id: number | null;
  course_name: string | null;
  parent_note_id: number | null;
  has_edits: boolean;
  excerpt: string;
  word_count: number;
  created_at: string;
  updated_at: string | null;
}

export interface NoteList {
  items: NoteSummary[];
  total: number;
  limit: number;
  offset: number;
}

export interface NoteDetail {
  id: number;
  title: string | null;
  note_type: NoteType;
  prompt: string | null;
  lecture_id: number | null;
  lecture_title: string | null;
  course_id: number | null;
  course_name: string | null;
  parent_note_id: number | null;
  root_note_id: number | null;
  original_markdown: string;
  edited_markdown: string | null;
  has_edits: boolean;
  grounding: Grounding;
  version_count: number;
  created_at: string;
  updated_at: string | null;
}

export interface NoteVersion {
  id: number;
  kind: "generated" | "refined" | "edited";
  note_id: number;
  label: string;
  title: string | null;
  word_count: number;
  created_at: string;
  is_current: boolean;
}

export interface NoteVersions {
  root_note_id: number;
  versions: NoteVersion[];
}

export interface NoteDiff {
  from_label: string;
  to_label: string;
  from_markdown: string;
  to_markdown: string;
  stats: Record<string, number>;
}

export interface GenerateResponse {
  id: number;
  title: string | null;
  notes: string;
  note_type: NoteType;
  lecture_id: number | null;
  course_id: number | null;
  parent_note_id: number | null;
  chunks_used: number;
  lecture_ids: number[];
  grounding: Grounding;
  created_at: string | null;
}

export interface GenerateArgs {
  prompt: string;
  lecture_id?: number | null;
  course_id?: number | null;
  note_type?: NoteType;
  style_overrides?: Record<string, string> | null;
  no_cache?: boolean;
}

export interface FeedbackResponse {
  updated_features: string[];
  personalization_score: number | null;
  summary: string[];
}

export interface FeatureDetail {
  value: string | number | boolean | string[] | Record<string, unknown>;
  reason: string;
  confidence: number;
  observations?: number;
  pinned?: boolean;
  last_updated?: string | null;
}

export type StyleProfileDetail = Record<string, FeatureDetail>;

export interface StyleVersion {
  version: number;
  created_at: string;
  profile_json: Record<string, unknown>;
}

export interface LearningProgress {
  style_profile_version: number;
  total_imported_notes: number;
  generated_notes: number;
  edited_notes: number;
  feedback_sessions: number;
  average_score: number;
}

export interface StyleDashboard {
  current_profile: StyleProfileDetail;
  sources: Record<string, number>;
  versions: StyleVersion[];
  learning_progress: LearningProgress;
}

export interface StyleProgress {
  measured: boolean;
  points: { score: number; created_at: string }[];
  current_score?: number;
  trend?: number;
  insights: string[];
  benchmark: {
    overall_improvement: number;
    largest_improvements: unknown[];
    largest_regressions: unknown[];
  };
}

export interface HistoricalSource {
  id: number;
  title: string;
  filename: string;
  source: string;
  analysis_status: string;
  contribution_weight: number;
  created_at: string;
}

export interface SearchExcerpt {
  text: string;
  page: number | null;
  score: number | null;
}

export interface SearchGroup {
  kind: "lecture" | "note";
  source_id: number;
  title: string;
  course_id: number | null;
  course_name: string | null;
  lecture_id: number | null;
  best_score: number | null;
  excerpts: SearchExcerpt[];
}

export interface SearchResults {
  query: string;
  scope: "all" | "lectures" | "notes";
  groups: SearchGroup[];
  total_hits: number;
  degraded: boolean;
}

export interface JumpMatch {
  kind: "lecture" | "note" | "course";
  id: number;
  title: string;
  subtitle: string | null;
  created_at: string | null;
}

export interface Citation {
  lecture_id: number | null;
  lecture_title: string | null;
  note_id: number | null;
  note_title: string | null;
  page: number | null;
  score: number | null;
  kind: string | null;
  text: string;
}

export interface ChatMessage {
  id: number;
  role: "user" | "assistant";
  content: string;
  citations: Citation[];
  created_at: string;
}

export interface ChatThreadSummary {
  id: number;
  title: string;
  scope: Scope;
  course_id: number | null;
  lecture_id: number | null;
  note_id: number | null;
  message_count: number;
  created_at: string;
  updated_at: string | null;
}

export interface ChatThreadDetail extends ChatThreadSummary {
  messages: ChatMessage[];
}

export interface DashboardSummary {
  recent_lectures: {
    id: number;
    filename: string;
    title: string | null;
    course_id: number | null;
    uploaded_at: string;
    status: IngestionStatus;
    error_message: string | null;
    chunk_count: number;
  }[];
  recent_notes: {
    id: number;
    title: string | null;
    note_type: NoteType;
    lecture_id: number | null;
    lecture_filename: string | null;
    course_id: number | null;
    course_name: string | null;
    created_at: string;
  }[];
  style_summary: Record<string, string | number>;
  learning_progress: LearningProgress;
  personalization_metrics: {
    current_score: number;
    trend: number;
    measured: boolean;
    feedback_sessions: number;
    insights: string[];
  };
  onboarding: {
    has_style: boolean;
    has_course: boolean;
    has_lecture: boolean;
    has_note: boolean;
    complete: boolean;
  };
  needs_attention: {
    type: "lecture_failed" | "lecture_without_notes";
    lecture_id: number;
    course_id: number | null;
    title: string;
    detail: string;
  }[];
  weak_topics: {
    note_id: number;
    title: string;
    course_id: number | null;
    score: number;
  }[];
  activity_feed: { type: string; title: string; timestamp: string }[];
}
