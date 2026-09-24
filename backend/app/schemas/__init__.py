from app.schemas.user import UserCreate, UserResponse
from app.schemas.lecture import LectureCreate, LectureResponse, LectureUpdate
from app.schemas.course import CourseCreate, CourseResponse, CourseUpdate
from app.schemas.note import (
    GenerateNotesRequest,
    GenerateNotesResponse,
    NoteDetailResponse,
    NoteListResponse,
    NoteSummary,
    NoteUpdateRequest,
)
from app.schemas.chat import ChatRequest, ChatResponse, ChatThreadDetail
from app.schemas.search import SearchResponse
from app.schemas.token import Token, TokenData
