from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse

from app.database.sql.models.user import User
from app.exceptions.course import (
    ChapterNotFoundException,
    ModuleNotFoundException,
    TopicNotFoundException,
)
from app.repositories.course_repository import CourseRepository, get_course_repository
from app.schemas.course import (
    CreateChapterRequest,
    CreateModuleRequest,
    CreateTopicRequest,
    UpdateResourceRequest,
)
from app.services.auth import get_current_user
from app.services.csrf import verify_csrf_token

router = APIRouter(prefix="/modules", tags=["Modules", "Courses"])


# ---------------------------------------------------------
# 4.1 List All Modules
# ---------------------------------------------------------
@router.get("", status_code=status.HTTP_200_OK)
@router.get("/", status_code=status.HTTP_200_OK, include_in_schema=False)
async def list_modules(
    current_user: User = Depends(get_current_user),
    repo: CourseRepository = Depends(get_course_repository),
):
    modules = await repo.get_modules_with_progress(current_user.id)
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "success": True,
            "modules": modules,
        },
    )


# ---------------------------------------------------------
# 4.6 Create Module (State-changing: requires CSRF)
# ---------------------------------------------------------
@router.post("", status_code=status.HTTP_201_CREATED)
@router.post("/", status_code=status.HTTP_201_CREATED, include_in_schema=False)
async def create_module(
    payload: CreateModuleRequest,
    current_user: User = Depends(get_current_user),
    _csrf: None = Depends(verify_csrf_token),
    repo: CourseRepository = Depends(get_course_repository),
):
    module = await repo.create_module(name=payload.moduleName)
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            "success": True,
            "id": module.id,
        },
    )


# ---------------------------------------------------------
# 4.3 List Chapters in Module
# Note: Defined BEFORE /:id/:chapter to avoid route conflict
# ---------------------------------------------------------
@router.get("/{id}/chapters", status_code=status.HTTP_200_OK)
async def list_chapters(
    id: str,
    current_user: User = Depends(get_current_user),
    repo: CourseRepository = Depends(get_course_repository),
):
    chapters = await repo.get_chapters_by_module(id)
    if chapters is None:
        raise ModuleNotFoundException()

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "success": True,
            "chapters": chapters,
        },
    )


# ---------------------------------------------------------
# 4.2 Get Module Details
# ---------------------------------------------------------
@router.get("/{id}", status_code=status.HTTP_200_OK)
async def get_module_details(
    id: str,
    current_user: User = Depends(get_current_user),
    repo: CourseRepository = Depends(get_course_repository),
):
    module_details = await repo.get_module_details(id, current_user.id)
    if module_details is None:
        raise ModuleNotFoundException()

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "success": True,
            "module": module_details,
        },
    )


# ---------------------------------------------------------
# 4.7 Create Chapter (State-changing: requires CSRF)
# ---------------------------------------------------------
@router.post("/{id}", status_code=status.HTTP_201_CREATED)
async def create_chapter(
    id: str,
    payload: CreateChapterRequest,
    current_user: User = Depends(get_current_user),
    _csrf: None = Depends(verify_csrf_token),
    repo: CourseRepository = Depends(get_course_repository),
):
    chapter = await repo.create_chapter(module_id=id, name=payload.chapterName)
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            "success": True,
            "id": chapter.id,
        },
    )


# ---------------------------------------------------------
# 4.5 Get Topic Content
# ---------------------------------------------------------
@router.get("/{id}/{chapter}/{topic}", status_code=status.HTTP_200_OK)
async def get_topic_content(
    id: str,
    chapter: str,
    topic: str,
    current_user: User = Depends(get_current_user),
    repo: CourseRepository = Depends(get_course_repository),
):
    topic_data = await repo.get_topic_details_with_content(module_id=id, chapter_id=chapter, topic_id=topic)
    if topic_data is None:
        raise TopicNotFoundException()

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "success": True,
            "content": topic_data["content"],
            "question_type": topic_data["question_type"],
        },
    )


# ---------------------------------------------------------
# 4.4 Get Chapter Topics & Progress
# ---------------------------------------------------------
@router.get("/{id}/{chapter}", status_code=status.HTTP_200_OK)
async def get_chapter_topics(
    id: str,
    chapter: str,
    current_user: User = Depends(get_current_user),
    repo: CourseRepository = Depends(get_course_repository),
):
    chapter_data = await repo.get_chapter_topics_with_progress(
        module_id=id,
        chapter_id=chapter,
        user_id=current_user.id,
    )
    if chapter_data is None:
        raise ChapterNotFoundException()

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "success": True,
            "chapter_id": chapter_data["chapter_id"],
            "total_topics": chapter_data["total_topics"],
            "completed_topics": chapter_data["completed_topics"],
            "topics": chapter_data["topics"],
        },
    )


# ---------------------------------------------------------
# 4.8 Create Topic (State-changing: requires CSRF)
# ---------------------------------------------------------
@router.post("/{id}/{chapter}", status_code=status.HTTP_201_CREATED)
@router.post("/{id}/{chapter}/", status_code=status.HTTP_201_CREATED, include_in_schema=False)
async def create_topic(
    id: str,
    chapter: str,
    payload: CreateTopicRequest,
    current_user: User = Depends(get_current_user),
    _csrf: None = Depends(verify_csrf_token),
    repo: CourseRepository = Depends(get_course_repository),
):
    topic = await repo.create_topic(
        module_id=id,
        chapter_id=chapter,
        name=payload.topicName,
        content=payload.content or "",
        content_path=payload.contentPath,
        question_type=payload.questionType or "code",
    )
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            "success": True,
            "id": topic.id,
        },
    )


# ---------------------------------------------------------
# 4.9 Update Resource (Module, Chapter, or Topic)
# ---------------------------------------------------------
@router.patch("/{id}/{chapter}/{topic}", status_code=status.HTTP_200_OK)
async def update_topic_resource(
    id: str,
    chapter: str,
    topic: str,
    payload: UpdateResourceRequest,
    current_user: User = Depends(get_current_user),
    _csrf: None = Depends(verify_csrf_token),
    repo: CourseRepository = Depends(get_course_repository),
):
    await repo.update_resource(
        module_id=id,
        chapter_id=chapter,
        topic_id=topic,
        name=payload.name,
        content=payload.content,
        question_type=payload.questionType,
    )
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "success": True,
            "message": "Resource updated successfully",
        },
    )


@router.patch("/{id}/{chapter}", status_code=status.HTTP_200_OK)
async def update_chapter_resource(
    id: str,
    chapter: str,
    payload: UpdateResourceRequest,
    current_user: User = Depends(get_current_user),
    _csrf: None = Depends(verify_csrf_token),
    repo: CourseRepository = Depends(get_course_repository),
):
    await repo.update_resource(
        module_id=id,
        chapter_id=chapter,
        topic_id=None,
        name=payload.name,
        content=payload.content,
    )
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "success": True,
            "message": "Resource updated successfully",
        },
    )


@router.patch("/{id}", status_code=status.HTTP_200_OK)
async def update_module_resource(
    id: str,
    payload: UpdateResourceRequest,
    current_user: User = Depends(get_current_user),
    _csrf: None = Depends(verify_csrf_token),
    repo: CourseRepository = Depends(get_course_repository),
):
    await repo.update_resource(
        module_id=id,
        chapter_id=None,
        topic_id=None,
        name=payload.name,
        content=payload.content,
    )
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "success": True,
            "message": "Resource updated successfully",
        },
    )


# ---------------------------------------------------------
# 4.10 Delete Resource (Module, Chapter, or Topic)
# ---------------------------------------------------------
@router.delete("/{id}/{chapter}/{topic}", status_code=status.HTTP_200_OK)
async def delete_topic_resource(
    id: str,
    chapter: str,
    topic: str,
    current_user: User = Depends(get_current_user),
    _csrf: None = Depends(verify_csrf_token),
    repo: CourseRepository = Depends(get_course_repository),
):
    await repo.delete_resource(
        module_id=id,
        chapter_id=chapter,
        topic_id=topic,
    )
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "success": True,
            "message": "Resource deleted successfully",
        },
    )


@router.delete("/{id}/{chapter}", status_code=status.HTTP_200_OK)
async def delete_chapter_resource(
    id: str,
    chapter: str,
    current_user: User = Depends(get_current_user),
    _csrf: None = Depends(verify_csrf_token),
    repo: CourseRepository = Depends(get_course_repository),
):
    await repo.delete_resource(
        module_id=id,
        chapter_id=chapter,
        topic_id=None,
    )
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "success": True,
            "message": "Resource deleted successfully",
        },
    )


@router.delete("/{id}", status_code=status.HTTP_200_OK)
async def delete_module_resource(
    id: str,
    current_user: User = Depends(get_current_user),
    _csrf: None = Depends(verify_csrf_token),
    repo: CourseRepository = Depends(get_course_repository),
):
    await repo.delete_resource(
        module_id=id,
        chapter_id=None,
        topic_id=None,
    )
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "success": True,
            "message": "Resource deleted successfully",
        },
    )


# ---------------------------------------------------------
# Topic Progress (User topic completion)
# ---------------------------------------------------------
@router.post("/{id}/{chapter}/{topic}/progress", status_code=status.HTTP_200_OK)
async def update_topic_progress(
    id: str,
    chapter: str,
    topic: str,
    completed: bool = True,
    current_user: User = Depends(get_current_user),
    _csrf: None = Depends(verify_csrf_token),
    repo: CourseRepository = Depends(get_course_repository),
):
    content = await repo.get_topic_content(module_id=id, chapter_id=chapter, topic_id=topic)
    if content is None:
        raise TopicNotFoundException()

    await repo.set_topic_progress(user_id=current_user.id, topic_id=topic, completed=completed)
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "success": True,
            "message": "Topic progress updated successfully",
        },
    )
