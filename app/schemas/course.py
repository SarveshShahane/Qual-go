from pydantic import BaseModel, Field, field_validator, model_validator


class CreateModuleRequest(BaseModel):
    moduleName: str = Field(..., min_length=1, max_length=255, examples=["Advanced Quantum Algorithms"])

    @field_validator("moduleName")
    @classmethod
    def validate_module_name(cls, v: str) -> str:
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("moduleName cannot be empty or whitespace only")
        return trimmed


class CreateChapterRequest(BaseModel):
    chapterName: str = Field(..., min_length=1, max_length=255, examples=["XYZ Algorithm"])

    @field_validator("chapterName")
    @classmethod
    def validate_chapter_name(cls, v: str) -> str:
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("chapterName cannot be empty or whitespace only")
        return trimmed


class CreateTopicRequest(BaseModel):
    topicName: str = Field(..., min_length=1, max_length=255, examples=["Algorithm Intuition"])
    contentPath: str | None = Field(None, max_length=512, examples=["/content/qubits/qubits.md"])
    content: str | None = Field(None, examples=["# Markdown content here"])
    questionType: str | None = Field(None, max_length=50, examples=["code", "mcq"])

    @field_validator("topicName")
    @classmethod
    def validate_topic_name(cls, v: str) -> str:
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("topicName cannot be empty or whitespace only")
        return trimmed

    @field_validator("contentPath")
    @classmethod
    def validate_content_path(cls, v: str | None) -> str | None:
        if v is not None:
            trimmed = v.strip()
            # Guard against directory traversal attacks
            if ".." in trimmed:
                raise ValueError("Path traversal ('..') is not permitted in contentPath")
            return trimmed
        return None


class UpdateResourceRequest(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255, examples=["Updated Resource Name"])
    content: str | None = Field(None, examples=["Updated Markdown Content (Optional)"])
    questionType: str | None = Field(None, max_length=50, examples=["code", "mcq"])

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str | None) -> str | None:
        if v is not None:
            trimmed = v.strip()
            if not trimmed:
                raise ValueError("name cannot be empty or whitespace only")
            return trimmed
        return None

    @model_validator(mode="after")
    def validate_at_least_one_field(self) -> "UpdateResourceRequest":
        if self.name is None and self.content is None and self.questionType is None:
            raise ValueError("At least one of 'name', 'content' or 'questionType' must be provided for update")
        return self


# Response Models
class ModuleListItem(BaseModel):
    id: str
    name: str
    total_chapters: int
    completed_chapters: int


class ListModulesResponse(BaseModel):
    success: bool = True
    modules: list[ModuleListItem]


class ChapterSummary(BaseModel):
    id: str
    name: str


class ModuleDetail(BaseModel):
    id: str
    name: str
    total_topics: int
    completed_topics: int
    chapters: list[ChapterSummary]


class GetModuleDetailsResponse(BaseModel):
    success: bool = True
    module: ModuleDetail


class ListChaptersResponse(BaseModel):
    success: bool = True
    chapters: list[ChapterSummary]


class TopicProgressItem(BaseModel):
    id: str
    name: str
    completed: bool
    question_type: str | None = None


class GetChapterTopicsResponse(BaseModel):
    success: bool = True
    chapter_id: str
    total_topics: int
    completed_topics: int
    topics: list[TopicProgressItem]


class GetTopicContentResponse(BaseModel):
    success: bool = True
    content: str
    question_type: str | None = None


class CreatedResourceResponse(BaseModel):
    success: bool = True
    id: str


class MessageResponse(BaseModel):
    success: bool = True
    message: str
