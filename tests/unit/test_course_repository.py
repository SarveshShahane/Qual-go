import unittest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database.sql.db import Base
from app.database.sql.models.course import Chapter, Module, Topic, UserTopicProgress
from app.database.sql.models.user import User
from app.exceptions.course import (
    ChapterNotFoundException,
    ModuleNotFoundException,
    TopicNotFoundException,
)
from app.repositories.course_repository import CourseRepository


class TestCourseRepository(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        self.session_maker = async_sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        self.session = self.session_maker()
        self.repo = CourseRepository(self.session)

        # Create a test user
        self.test_user = User(
            id=1,
            username="test_student",
            email="student@qual.dev",
            password="hashedpassword123",
        )
        self.session.add(self.test_user)
        await self.session.commit()

    async def asyncTearDown(self):
        await self.session.close()
        await self.engine.dispose()

    async def test_create_and_get_module(self):
        mod = await self.repo.create_module(name="Basics of Quantum Computing", module_id="mod_123")
        self.assertEqual(mod.id, "mod_123")
        self.assertEqual(mod.name, "Basics of Quantum Computing")

        modules = await self.repo.get_modules_with_progress(self.test_user.id)
        self.assertEqual(len(modules), 1)
        self.assertEqual(modules[0]["id"], "mod_123")
        self.assertEqual(modules[0]["name"], "Basics of Quantum Computing")
        self.assertEqual(modules[0]["total_chapters"], 0)
        self.assertEqual(modules[0]["completed_chapters"], 0)

    async def test_create_chapter_success_and_invalid_module(self):
        await self.repo.create_module(name="Module 1", module_id="mod_1")
        chap = await self.repo.create_chapter(module_id="mod_1", name="Chapter 1", chapter_id="chap_1")
        self.assertEqual(chap.id, "chap_1")
        self.assertEqual(chap.module_id, "mod_1")

        # Invalid module
        with self.assertRaises(ModuleNotFoundException):
            await self.repo.create_chapter(module_id="non_existent", name="Chapter X")

    async def test_create_topic_success_and_invalid_chapter(self):
        await self.repo.create_module(name="Module 1", module_id="mod_1")
        await self.repo.create_chapter(module_id="mod_1", name="Chapter 1", chapter_id="chap_1")

        top = await self.repo.create_topic(
            module_id="mod_1",
            chapter_id="chap_1",
            name="Qubits",
            content="# Qubits content",
            topic_id="top_1",
        )
        self.assertEqual(top.id, "top_1")
        self.assertEqual(top.content, "# Qubits content")

        # Invalid chapter
        with self.assertRaises(ChapterNotFoundException):
            await self.repo.create_topic(
                module_id="mod_1",
                chapter_id="non_existent_chap",
                name="Topic X",
            )

    async def test_progress_calculation_modules_and_chapters(self):
        # 1 module, 2 chapters, chapter 1 has 2 topics, chapter 2 has 1 topic
        await self.repo.create_module(name="Quantum Algorithms", module_id="mod_algo")
        await self.repo.create_chapter(module_id="mod_algo", name="Grover", chapter_id="chap_grover")
        await self.repo.create_chapter(module_id="mod_algo", name="Shor", chapter_id="chap_shor")

        await self.repo.create_topic(
            module_id="mod_algo",
            chapter_id="chap_grover",
            name="Oracle",
            topic_id="top_oracle",
        )
        await self.repo.create_topic(
            module_id="mod_algo",
            chapter_id="chap_grover",
            name="Diffuser",
            topic_id="top_diffuser",
        )
        await self.repo.create_topic(
            module_id="mod_algo",
            chapter_id="chap_shor",
            name="QFT",
            topic_id="top_qft",
        )

        # Before any completions
        modules_progress = await self.repo.get_modules_with_progress(self.test_user.id)
        self.assertEqual(modules_progress[0]["total_chapters"], 2)
        self.assertEqual(modules_progress[0]["completed_chapters"], 0)

        details = await self.repo.get_module_details("mod_algo", self.test_user.id)
        self.assertEqual(details["total_topics"], 3)
        self.assertEqual(details["completed_topics"], 0)
        self.assertEqual(len(details["chapters"]), 2)

        # Complete one topic in Grover
        await self.repo.set_topic_progress(self.test_user.id, "top_oracle", completed=True)

        modules_progress = await self.repo.get_modules_with_progress(self.test_user.id)
        self.assertEqual(modules_progress[0]["completed_chapters"], 0)  # Chapter not fully completed yet

        details = await self.repo.get_module_details("mod_algo", self.test_user.id)
        self.assertEqual(details["completed_topics"], 1)

        # Complete second topic in Grover -> Grover chapter is now complete
        await self.repo.set_topic_progress(self.test_user.id, "top_diffuser", completed=True)

        modules_progress = await self.repo.get_modules_with_progress(self.test_user.id)
        self.assertEqual(modules_progress[0]["completed_chapters"], 1)

        # Check chapter topics progress
        chap_topics = await self.repo.get_chapter_topics_with_progress("mod_algo", "chap_grover", self.test_user.id)
        self.assertEqual(chap_topics["total_topics"], 2)
        self.assertEqual(chap_topics["completed_topics"], 2)
        self.assertTrue(all(t["completed"] for t in chap_topics["topics"]))

    async def test_get_chapters_by_module(self):
        await self.repo.create_module(name="Mod A", module_id="mod_a")
        await self.repo.create_chapter(module_id="mod_a", name="Chap 1", chapter_id="c1")
        await self.repo.create_chapter(module_id="mod_a", name="Chap 2", chapter_id="c2")

        chapters = await self.repo.get_chapters_by_module("mod_a")
        self.assertEqual(len(chapters), 2)
        self.assertEqual([c["id"] for c in chapters], ["c1", "c2"])

        # Not found module
        self.assertIsNone(await self.repo.get_chapters_by_module("non_existent"))

    async def test_get_topic_content(self):
        await self.repo.create_module(name="Mod", module_id="mod_c")
        await self.repo.create_chapter(module_id="mod_c", name="Chap", chapter_id="chap_c")
        await self.repo.create_topic(
            module_id="mod_c",
            chapter_id="chap_c",
            name="Topic",
            content="# Direct Markdown",
            topic_id="top_c",
        )

        content = await self.repo.get_topic_content("mod_c", "chap_c", "top_c")
        self.assertEqual(content, "# Direct Markdown")

        # Non-existent topic
        self.assertIsNone(await self.repo.get_topic_content("mod_c", "chap_c", "invalid_topic"))

    async def test_update_resources(self):
        await self.repo.create_module(name="Initial Mod", module_id="m1")
        await self.repo.create_chapter(module_id="m1", name="Initial Chap", chapter_id="c1")
        await self.repo.create_topic(
            module_id="m1",
            chapter_id="c1",
            name="Initial Top",
            content="Old Content",
            topic_id="t1",
        )

        # Update module
        await self.repo.update_resource(module_id="m1", name="Updated Mod")
        mod_details = await self.repo.get_module_details("m1", self.test_user.id)
        self.assertEqual(mod_details["name"], "Updated Mod")

        # Update chapter
        await self.repo.update_resource(module_id="m1", chapter_id="c1", name="Updated Chap")
        chapters = await self.repo.get_chapters_by_module("m1")
        self.assertEqual(chapters[0]["name"], "Updated Chap")

        # Update topic
        await self.repo.update_resource(
            module_id="m1",
            chapter_id="c1",
            topic_id="t1",
            name="Updated Top",
            content="New Content",
        )
        content = await self.repo.get_topic_content("m1", "c1", "t1")
        self.assertEqual(content, "New Content")

    async def test_delete_resources_with_cascade(self):
        await self.repo.create_module(name="Delete Mod", module_id="del_m")
        await self.repo.create_chapter(module_id="del_m", name="Delete Chap", chapter_id="del_c")
        await self.repo.create_topic(
            module_id="del_m",
            chapter_id="del_c",
            name="Delete Top",
            content="Content",
            topic_id="del_t",
        )

        # Delete topic
        res = await self.repo.delete_resource(module_id="del_m", chapter_id="del_c", topic_id="del_t")
        self.assertTrue(res)
        self.assertIsNone(await self.repo.get_topic_content("del_m", "del_c", "del_t"))

        # Re-create topic, then delete chapter
        await self.repo.create_topic(
            module_id="del_m",
            chapter_id="del_c",
            name="Delete Top 2",
            topic_id="del_t2",
        )
        res = await self.repo.delete_resource(module_id="del_m", chapter_id="del_c")
        self.assertTrue(res)
        self.assertIsNone(await self.repo.get_chapter_topics_with_progress("del_m", "del_c", self.test_user.id))

        # Delete module
        res = await self.repo.delete_resource(module_id="del_m")
        self.assertTrue(res)
        self.assertIsNone(await self.repo.get_module_details("del_m", self.test_user.id))


if __name__ == "__main__":
    unittest.main()
