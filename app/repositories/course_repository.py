import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from fastapi import Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.sql.db import get_db
from app.database.sql.models.course import Chapter, Module, Topic, UserTopicProgress
from app.exceptions.course import (
    ChapterNotFoundException,
    InvalidResourceException,
    ModuleNotFoundException,
    TopicNotFoundException,
)


class CourseRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_modules_with_progress(self, user_id: int) -> list[dict]:
        """
        Retrieves all modules with total_chapters and completed_chapters for user_id.
        A chapter is considered completed if it has topics and all its topics are completed.
        """
        stmt = (
            select(Module)
            .options(
                selectinload(Module.chapters).selectinload(Chapter.topics).selectinload(Topic.progresses)
            )
            .order_by(Module.order, Module.created_at)
        )
        result = await self.db.execute(stmt)
        modules = result.scalars().all()

        modules_data = []
        for mod in modules:
            total_chapters = len(mod.chapters)
            completed_chapters = 0

            for chap in mod.chapters:
                topics = chap.topics
                if not topics:
                    continue

                all_completed = True
                for top in topics:
                    user_prog = next(
                        (p for p in top.progresses if p.user_id == user_id and p.completed),
                        None,
                    )
                    if not user_prog:
                        all_completed = False
                        break

                if all_completed:
                    completed_chapters += 1

            modules_data.append(
                {
                    "id": mod.id,
                    "name": mod.name,
                    "total_chapters": total_chapters,
                    "completed_chapters": completed_chapters,
                }
            )

        return modules_data

    async def get_module_details(self, module_id: str, user_id: int) -> dict | None:
        """
        Retrieves details for a module, total_topics, completed_topics, and chapters list.
        """
        stmt = (
            select(Module)
            .where(Module.id == module_id)
            .options(
                selectinload(Module.chapters).selectinload(Chapter.topics).selectinload(Topic.progresses)
            )
        )
        result = await self.db.execute(stmt)
        module = result.scalar_one_or_none()
        if not module:
            return None

        total_topics = 0
        completed_topics = 0
        chapters_data = []

        for chap in module.chapters:
            chapters_data.append(
                {
                    "id": chap.id,
                    "name": chap.name,
                }
            )
            for top in chap.topics:
                total_topics += 1
                user_prog = next(
                    (p for p in top.progresses if p.user_id == user_id and p.completed),
                    None,
                )
                if user_prog:
                    completed_topics += 1

        return {
            "id": module.id,
            "name": module.name,
            "total_topics": total_topics,
            "completed_topics": completed_topics,
            "chapters": chapters_data,
        }

    async def get_chapters_by_module(self, module_id: str) -> list[dict] | None:
        """
        Retrieves all chapters in a module. Returns None if module does not exist.
        """
        mod_stmt = select(Module).where(Module.id == module_id)
        mod_res = await self.db.execute(mod_stmt)
        if not mod_res.scalar_one_or_none():
            return None

        stmt = select(Chapter).where(Chapter.module_id == module_id).order_by(Chapter.order, Chapter.created_at)
        result = await self.db.execute(stmt)
        chapters = result.scalars().all()

        return [{"id": c.id, "name": c.name} for c in chapters]

    async def get_chapter_topics_with_progress(
        self,
        module_id: str,
        chapter_id: str,
        user_id: int,
    ) -> dict | None:
        """
        Retrieves topics contained within a chapter along with topic completion metrics.
        Returns None if chapter does not exist in module.
        """
        stmt = (
            select(Chapter)
            .where(Chapter.id == chapter_id, Chapter.module_id == module_id)
            .options(selectinload(Chapter.topics).selectinload(Topic.progresses))
        )
        result = await self.db.execute(stmt)
        chapter = result.scalar_one_or_none()
        if not chapter:
            return None

        total_topics = len(chapter.topics)
        completed_topics = 0
        topics_data = []

        for top in chapter.topics:
            user_prog = next(
                (p for p in top.progresses if p.user_id == user_id and p.completed),
                None,
            )
            is_completed = bool(user_prog and user_prog.completed)
            if is_completed:
                completed_topics += 1

            topics_data.append(
                {
                    "id": top.id,
                    "name": top.name,
                    "completed": is_completed,
                    "question_type": top.question_type or "code",
                }
            )

        return {
            "chapter_id": chapter.id,
            "total_topics": total_topics,
            "completed_topics": completed_topics,
            "topics": topics_data,
        }

    async def get_topic_details_with_content(
        self,
        module_id: str,
        chapter_id: str,
        topic_id: str,
    ) -> dict | None:
        """
        Retrieves markdown content and metadata (including question_type) for a topic.
        Returns None if topic is not found.
        """
        stmt = (
            select(Topic)
            .join(Chapter, Topic.chapter_id == Chapter.id)
            .where(
                Topic.id == topic_id,
                Topic.chapter_id == chapter_id,
                Chapter.module_id == module_id,
            )
        )
        result = await self.db.execute(stmt)
        topic = result.scalar_one_or_none()
        if not topic:
            return None

        content = topic.content or ""
        if topic.content_path:
            clean_path = topic.content_path.lstrip("/\\")
            possible_paths = [
                Path(topic.content_path),
                Path.cwd() / clean_path,
                Path.cwd().parent / clean_path,
            ]
            for p in possible_paths:
                try:
                    if p.is_file():
                        content = p.read_text(encoding="utf-8")
                        break
                except Exception:
                    pass

        return {
            "id": topic.id,
            "name": topic.name,
            "content": content,
            "question_type": topic.question_type or "code",
        }

    async def get_topic_content(
        self,
        module_id: str,
        chapter_id: str,
        topic_id: str,
    ) -> str | None:
        """
        Retrieves markdown content for topic. Reads from content_path if valid and present.
        Returns None if topic is not found.
        """
        data = await self.get_topic_details_with_content(module_id, chapter_id, topic_id)
        if data is None:
            return None
        return data["content"]

    async def create_module(
        self,
        name: str,
        module_id: str | None = None,
        order: int = 0,
    ) -> Module:
        mod_id = module_id or f"mod_{uuid.uuid4().hex[:6]}"
        module = Module(id=mod_id, name=name, order=order)
        self.db.add(module)
        await self.db.commit()
        await self.db.refresh(module)
        return module

    async def create_chapter(
        self,
        module_id: str,
        name: str,
        chapter_id: str | None = None,
        order: int = 0,
    ) -> Chapter:
        mod_stmt = select(Module).where(Module.id == module_id)
        res = await self.db.execute(mod_stmt)
        if not res.scalar_one_or_none():
            raise ModuleNotFoundException()

        chap_id = chapter_id or f"chap_{uuid.uuid4().hex[:6]}"
        chapter = Chapter(id=chap_id, module_id=module_id, name=name, order=order)
        self.db.add(chapter)
        await self.db.commit()
        await self.db.refresh(chapter)
        return chapter

    async def create_topic(
        self,
        module_id: str,
        chapter_id: str,
        name: str,
        content: str = "",
        content_path: str | None = None,
        topic_id: str | None = None,
        order: int = 0,
        question_type: str | None = "code",
    ) -> Topic:
        chap_stmt = select(Chapter).where(Chapter.id == chapter_id, Chapter.module_id == module_id)
        res = await self.db.execute(chap_stmt)
        if not res.scalar_one_or_none():
            raise ChapterNotFoundException()

        top_id = topic_id or f"top_{uuid.uuid4().hex[:6]}"
        topic = Topic(
            id=top_id,
            chapter_id=chapter_id,
            name=name,
            content=content,
            content_path=content_path,
            order=order,
            question_type=question_type or "code",
        )
        self.db.add(topic)
        await self.db.commit()
        await self.db.refresh(topic)
        return topic

    async def update_resource(
        self,
        module_id: str,
        chapter_id: str | None = None,
        topic_id: str | None = None,
        name: str | None = None,
        content: str | None = None,
        question_type: str | None = None,
    ) -> bool:
        if topic_id:
            stmt = (
                select(Topic)
                .join(Chapter, Topic.chapter_id == Chapter.id)
                .where(
                    Topic.id == topic_id,
                    Topic.chapter_id == chapter_id,
                    Chapter.module_id == module_id,
                )
            )
            res = await self.db.execute(stmt)
            topic = res.scalar_one_or_none()
            if not topic:
                raise TopicNotFoundException()

            if name is not None:
                topic.name = name
            if content is not None:
                topic.content = content
            if question_type is not None:
                topic.question_type = question_type
            await self.db.commit()
            return True

        elif chapter_id:
            stmt = select(Chapter).where(Chapter.id == chapter_id, Chapter.module_id == module_id)
            res = await self.db.execute(stmt)
            chapter = res.scalar_one_or_none()
            if not chapter:
                raise ChapterNotFoundException()

            if name is not None:
                chapter.name = name
            await self.db.commit()
            return True

        else:
            stmt = select(Module).where(Module.id == module_id)
            res = await self.db.execute(stmt)
            module = res.scalar_one_or_none()
            if not module:
                raise ModuleNotFoundException()

            if name is not None:
                module.name = name
            await self.db.commit()
            return True

    async def delete_resource(
        self,
        module_id: str,
        chapter_id: str | None = None,
        topic_id: str | None = None,
    ) -> bool:
        if topic_id:
            stmt = (
                select(Topic)
                .join(Chapter, Topic.chapter_id == Chapter.id)
                .where(
                    Topic.id == topic_id,
                    Topic.chapter_id == chapter_id,
                    Chapter.module_id == module_id,
                )
            )
            res = await self.db.execute(stmt)
            topic = res.scalar_one_or_none()
            if not topic:
                raise TopicNotFoundException()

            await self.db.delete(topic)
            await self.db.commit()
            return True

        elif chapter_id:
            stmt = select(Chapter).where(Chapter.id == chapter_id, Chapter.module_id == module_id)
            res = await self.db.execute(stmt)
            chapter = res.scalar_one_or_none()
            if not chapter:
                raise ChapterNotFoundException()

            await self.db.delete(chapter)
            await self.db.commit()
            return True

        else:
            stmt = select(Module).where(Module.id == module_id)
            res = await self.db.execute(stmt)
            module = res.scalar_one_or_none()
            if not module:
                raise ModuleNotFoundException()

            await self.db.delete(module)
            await self.db.commit()
            return True

    async def set_topic_progress(
        self,
        user_id: int,
        topic_id: str,
        completed: bool = True,
    ) -> UserTopicProgress:
        stmt = select(UserTopicProgress).where(
            UserTopicProgress.user_id == user_id,
            UserTopicProgress.topic_id == topic_id,
        )
        res = await self.db.execute(stmt)
        progress = res.scalar_one_or_none()

        now = datetime.now(timezone.utc)
        if progress:
            progress.completed = completed
            progress.completed_at = now if completed else None
        else:
            progress = UserTopicProgress(
                user_id=user_id,
                topic_id=topic_id,
                completed=completed,
                completed_at=now if completed else None,
            )
            self.db.add(progress)

        await self.db.commit()
        await self.db.refresh(progress)
        return progress


def get_course_repository(db: AsyncSession = Depends(get_db)) -> CourseRepository:
    return CourseRepository(db)
