from enum import Enum
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field

from app.schemas.quantum import CanonicalCircuit, SimulationResponse


class TutoringMode(str, Enum):
    EXPLAIN = "explain"
    HINT = "hint"
    SOCRATIC = "socratic"
    DEBUG = "debug"
    GENERATE = "generate"


class UserLevel(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class AIDiagnosticSeverity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class AIDiagnosticCategory(str, Enum):
    SYNTAX = "syntax"
    QUANTUM_CONCEPT = "quantum_concept"
    HARDWARE_LIMIT = "hardware_limit"
    LOGIC_MISMATCH = "logic_mismatch"


class AIDiagnostic(BaseModel):
    severity: AIDiagnosticSeverity = AIDiagnosticSeverity.ERROR
    category: AIDiagnosticCategory = AIDiagnosticCategory.QUANTUM_CONCEPT
    line: Optional[int] = None
    problem: str
    cause: str
    suggested_fix: str
    corrected_snippet: Optional[str] = None


class AIHint(BaseModel):
    level: int = Field(default=1, ge=1, le=4)
    label: str = "Concept Clue"
    content: str


class AIRecommendation(BaseModel):
    id: str
    title: str
    reason: str
    target_module: str
    target_chapter: Optional[str] = None
    difficulty: str = "Beginner"
    priority: int = 1


class AISourceReference(BaseModel):
    module_id: str
    module_name: str
    chapter_id: Optional[str] = None
    chapter_name: Optional[str] = None
    snippet: str


class TopicMastery(BaseModel):
    topic_id: str
    topic_name: str
    score: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    status: Literal["needs_review", "learning", "mastered"] = "learning"


class LearnerProfile(BaseModel):
    user_id: Optional[int] = None
    completed_topics: List[str] = Field(default_factory=list)
    weak_topics: List[str] = Field(default_factory=list)
    strong_topics: List[str] = Field(default_factory=list)
    recent_mistakes: List[str] = Field(default_factory=list)
    assessment_scores: Dict[str, float] = Field(default_factory=dict)
    hint_dependency_score: float = 0.0


class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str


class TutorContext(BaseModel):
    model_config = {"extra": "allow"}

    user_level: UserLevel = UserLevel.BEGINNER
    current_module: Optional[str] = None
    current_chapter: Optional[str] = None
    current_topic: Optional[str] = None
    circuit: Optional[Any] = None
    code: Optional[str] = None
    selected_code: Optional[str] = None
    error_message: Optional[str] = None
    simulation_result: Optional[Any] = None
    completed_topics: Optional[List[str]] = Field(default_factory=list)
    recent_mistakes: Optional[List[str]] = Field(default_factory=list)
    current_challenge_id: Optional[str] = None
    hint_level: int = 1
    tutoring_mode: TutoringMode = TutoringMode.EXPLAIN


class TutorChatRequest(BaseModel):
    model_config = {"extra": "allow"}

    prompt: str
    context: Optional[TutorContext] = None
    history: Optional[List[ChatMessage]] = Field(default_factory=list)


class ExplainRequest(BaseModel):
    model_config = {"extra": "allow"}

    concept: Optional[str] = None
    context: Optional[TutorContext] = None


class GenerateCodeRequest(BaseModel):
    model_config = {"extra": "allow"}

    prompt: str
    target_framework: str = "qiskit"
    context: Optional[TutorContext] = None


class GenerateCircuitRequest(BaseModel):
    model_config = {"extra": "allow"}

    prompt: str
    context: Optional[TutorContext] = None


class DebugRequest(BaseModel):
    model_config = {"extra": "allow"}

    code: Optional[str] = None
    circuit: Optional[Any] = None
    error_message: Optional[str] = None
    simulation_result: Optional[Any] = None
    context: Optional[TutorContext] = None


class HintRequest(BaseModel):
    challenge_id: Optional[str] = None
    hint_level: int = 1
    context: Optional[TutorContext] = None


class RecommendationRequest(BaseModel):
    profile: Optional[LearnerProfile] = None
    context: Optional[TutorContext] = None


class AIResponse(BaseModel):
    type: Literal[
        "explanation",
        "code",
        "debug",
        "hint",
        "recommendation",
        "circuit",
        "socratic",
    ]
    message: str
    code: Optional[str] = None
    language: Optional[str] = "python"
    circuit: Optional[CanonicalCircuit] = None
    diagnostics: Optional[List[AIDiagnostic]] = None
    recommendations: Optional[List[AIRecommendation]] = None
    hints: Optional[List[AIHint]] = None
    sources: Optional[List[AISourceReference]] = None
    suggested_followups: Optional[List[str]] = Field(default_factory=list)
    mastery_update: Optional[TopicMastery] = None
    provider: str = "groq"
    model: str = "llama-3.3-70b-versatile"
