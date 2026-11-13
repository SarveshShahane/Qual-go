import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.app import app
from app.database.sql.db import Base, get_db
from app.database.sql.models.user import User
from app.services.auth import create_access_token, hash_password
from app.services.csrf import generate_csrf_token


class TestCourseRoutes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        cls.session_maker = async_sessionmaker(
            bind=cls.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

        async def init_db():
            async with cls.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

        import asyncio
        asyncio.run(init_db())

        async def override_get_db():
            async with cls.session_maker() as session:
                yield session

        app.dependency_overrides[get_db] = override_get_db
        cls.client = TestClient(app)

        # Seed user
        async def seed_user():
            async with cls.session_maker() as session:
                user = User(
                    id=1,
                    username="quantum_researcher",
                    email="researcher@qual.dev",
                    password=hash_password("SuperSecret123!"),
                )
                session.add(user)
                await session.commit()

        asyncio.run(seed_user())

        cls.valid_token = create_access_token(user_id=1, email="researcher@qual.dev")
        cls.auth_headers = {"Authorization": f"Bearer {cls.valid_token}"}
        cls.csrf_token = generate_csrf_token()
        cls.all_headers = {
            "Authorization": f"Bearer {cls.valid_token}",
            "X-CSRF-Token": cls.csrf_token,
        }

    @classmethod
    def tearDownClass(cls):
        app.dependency_overrides.clear()
        import asyncio
        asyncio.run(cls.engine.dispose())

    # -------------------------------------------------------------
    # CSRF & Auth Guard Tests
    # -------------------------------------------------------------
    def test_csrf_token_endpoint(self):
        res = self.client.get("/api/v1/auth/csrf-token")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["success"])
        self.assertIn("csrf_token", data)
        self.assertIn("csrf_token", res.cookies)
        self.assertIn("x-csrf-token", res.headers)

    def test_auth_required_without_token_returns_401(self):
        res = self.client.get("/api/v1/modules")
        self.assertEqual(res.status_code, 401)
        data = res.json()
        self.assertFalse(data["success"])
        self.assertIn("error", data)

    def test_state_changing_without_csrf_returns_403(self):
        # Missing X-CSRF-Token on POST
        res = self.client.post(
            "/api/v1/modules",
            json={"moduleName": "Advanced Quantum Algorithms"},
            headers=self.auth_headers,
        )
        self.assertEqual(res.status_code, 403)
        data = res.json()
        self.assertFalse(data["success"])
        self.assertIn("CSRF", data["message"])

    def test_state_changing_with_invalid_csrf_returns_403(self):
        headers = {
            **self.auth_headers,
            "X-CSRF-Token": "invalid.csrf.token",
        }
        res = self.client.post(
            "/api/v1/modules",
            json={"moduleName": "Advanced Quantum Algorithms"},
            headers=headers,
        )
        self.assertEqual(res.status_code, 403)

    # -------------------------------------------------------------
    # Full Course Lifecycle (4.1 to 4.10)
    # -------------------------------------------------------------
    def test_full_course_api_lifecycle(self):
        # 4.6 Create Module
        create_mod_res = self.client.post(
            "/api/v1/modules",
            json={"moduleName": "Basics of Quantum Computing"},
            headers=self.all_headers,
        )
        self.assertEqual(create_mod_res.status_code, 201)
        mod_data = create_mod_res.json()
        self.assertTrue(mod_data["success"])
        mod_id = mod_data["id"]
        self.assertTrue(mod_id.startswith("mod_"))

        # 4.1 List All Modules
        list_res = self.client.get("/api/v1/modules", headers=self.auth_headers)
        self.assertEqual(list_res.status_code, 200)
        list_data = list_res.json()
        self.assertTrue(list_data["success"])
        self.assertTrue(any(m["id"] == mod_id for m in list_data["modules"]))

        # 4.7 Create Chapter
        create_chap_res = self.client.post(
            f"/api/v1/modules/{mod_id}",
            json={"chapterName": "Basic Syntax"},
            headers=self.all_headers,
        )
        self.assertEqual(create_chap_res.status_code, 201)
        chap_data = create_chap_res.json()
        self.assertTrue(chap_data["success"])
        chap_id = chap_data["id"]
        self.assertTrue(chap_id.startswith("chap_"))

        # 4.3 List Chapters in Module
        chap_list_res = self.client.get(f"/api/v1/modules/{mod_id}/chapters", headers=self.auth_headers)
        self.assertEqual(chap_list_res.status_code, 200)
        chap_list_data = chap_list_res.json()
        self.assertTrue(chap_list_data["success"])
        self.assertEqual(chap_list_data["chapters"][0]["id"], chap_id)
        self.assertEqual(chap_list_data["chapters"][0]["name"], "Basic Syntax")

        # 4.8 Create Topic
        create_top_res = self.client.post(
            f"/api/v1/modules/{mod_id}/{chap_id}",
            json={
                "topicName": "Qubits",
                "content": "# Qubits content",
            },
            headers=self.all_headers,
        )
        self.assertEqual(create_top_res.status_code, 201)
        top_data = create_top_res.json()
        self.assertTrue(top_data["success"])
        top_id = top_data["id"]
        self.assertTrue(top_id.startswith("top_"))

        # 4.2 Get Module Details
        details_res = self.client.get(f"/api/v1/modules/{mod_id}", headers=self.auth_headers)
        self.assertEqual(details_res.status_code, 200)
        details_data = details_res.json()
        self.assertTrue(details_data["success"])
        self.assertEqual(details_data["module"]["id"], mod_id)
        self.assertEqual(details_data["module"]["total_topics"], 1)
        self.assertEqual(details_data["module"]["completed_topics"], 0)
        self.assertEqual(len(details_data["module"]["chapters"]), 1)

        # 4.4 Get Chapter Topics & Progress
        chap_topics_res = self.client.get(f"/api/v1/modules/{mod_id}/{chap_id}", headers=self.auth_headers)
        self.assertEqual(chap_topics_res.status_code, 200)
        chap_topics_data = chap_topics_res.json()
        self.assertTrue(chap_topics_data["success"])
        self.assertEqual(chap_topics_data["chapter_id"], chap_id)
        self.assertEqual(chap_topics_data["total_topics"], 1)
        self.assertEqual(chap_topics_data["completed_topics"], 0)
        self.assertEqual(chap_topics_data["topics"][0]["name"], "Qubits")
        self.assertFalse(chap_topics_data["topics"][0]["completed"])

        # 4.5 Get Topic Content
        content_res = self.client.get(f"/api/v1/modules/{mod_id}/{chap_id}/{top_id}", headers=self.auth_headers)
        self.assertEqual(content_res.status_code, 200)
        content_data = content_res.json()
        self.assertTrue(content_data["success"])
        self.assertEqual(content_data["content"], "# Qubits content")

        # Mark Progress
        prog_res = self.client.post(
            f"/api/v1/modules/{mod_id}/{chap_id}/{top_id}/progress?completed=true",
            headers=self.all_headers,
        )
        self.assertEqual(prog_res.status_code, 200)

        # Verify progress reflected
        chap_topics_after = self.client.get(f"/api/v1/modules/{mod_id}/{chap_id}", headers=self.auth_headers).json()
        self.assertEqual(chap_topics_after["completed_topics"], 1)
        self.assertTrue(chap_topics_after["topics"][0]["completed"])

        # 4.9 Update Resource (Module, Chapter, and Topic)
        # Update topic
        patch_top_res = self.client.patch(
            f"/api/v1/modules/{mod_id}/{chap_id}/{top_id}",
            json={"name": "Qubits & Superposition", "content": "# Updated Qubits"},
            headers=self.all_headers,
        )
        self.assertEqual(patch_top_res.status_code, 200)
        self.assertTrue(patch_top_res.json()["success"])
        self.assertEqual(patch_top_res.json()["message"], "Resource updated successfully")

        # Update chapter
        patch_chap_res = self.client.patch(
            f"/api/v1/modules/{mod_id}/{chap_id}",
            json={"name": "Basic Quantum Syntax"},
            headers=self.all_headers,
        )
        self.assertEqual(patch_chap_res.status_code, 200)
        self.assertTrue(patch_chap_res.json()["success"])

        # Update module
        patch_mod_res = self.client.patch(
            f"/api/v1/modules/{mod_id}",
            json={"name": "Advanced Quantum Computing"},
            headers=self.all_headers,
        )
        self.assertEqual(patch_mod_res.status_code, 200)
        self.assertTrue(patch_mod_res.json()["success"])

        # 4.10 Delete Resource (Delete topic, chapter, module)
        del_top_res = self.client.delete(f"/api/v1/modules/{mod_id}/{chap_id}/{top_id}", headers=self.all_headers)
        self.assertEqual(del_top_res.status_code, 200)
        self.assertEqual(del_top_res.json()["message"], "Resource deleted successfully")

        del_chap_res = self.client.delete(f"/api/v1/modules/{mod_id}/{chap_id}", headers=self.all_headers)
        self.assertEqual(del_chap_res.status_code, 200)
        self.assertEqual(del_chap_res.json()["message"], "Resource deleted successfully")

        del_mod_res = self.client.delete(f"/api/v1/modules/{mod_id}", headers=self.all_headers)
        self.assertEqual(del_mod_res.status_code, 200)
        self.assertEqual(del_mod_res.json()["message"], "Resource deleted successfully")

    # -------------------------------------------------------------
    # Validation and Error Handling Tests
    # -------------------------------------------------------------
    def test_validation_errors_return_400(self):
        # Empty module name
        res = self.client.post(
            "/api/v1/modules",
            json={"moduleName": "   "},
            headers=self.all_headers,
        )
        self.assertEqual(res.status_code, 400)
        data = res.json()
        self.assertFalse(data["success"])
        self.assertEqual(data["error"], "Invalid request payload")

        # Path traversal in contentPath
        res = self.client.post(
            "/api/v1/modules/mod_test/chap_test",
            json={
                "topicName": "Test",
                "contentPath": "../../etc/passwd",
            },
            headers=self.all_headers,
        )
        self.assertEqual(res.status_code, 400)
        data = res.json()
        self.assertFalse(data["success"])
        self.assertEqual(data["error"], "Invalid request payload")

    def test_not_found_errors_return_404(self):
        # Nonexistent module
        res = self.client.get("/api/v1/modules/mod_nonexistent", headers=self.auth_headers)
        self.assertEqual(res.status_code, 404)
        data = res.json()
        self.assertFalse(data["success"])
        self.assertEqual(data["error"], "Module not found")

        # Nonexistent chapter
        res = self.client.get("/api/v1/modules/mod_nonexistent/chap_nonexistent", headers=self.auth_headers)
        self.assertEqual(res.status_code, 404)
        data = res.json()
        self.assertFalse(data["success"])
        self.assertEqual(data["error"], "Chapter not found")


if __name__ == "__main__":
    unittest.main()
