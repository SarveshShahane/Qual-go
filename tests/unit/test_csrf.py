import time
import unittest
from unittest.mock import MagicMock

from app.exceptions.auth import CSRFValidationException
from app.services.csrf import generate_csrf_token, validate_csrf_token, verify_csrf_token


class TestCSRFService(unittest.TestCase):
    def test_generate_csrf_token_structure(self):
        token = generate_csrf_token()
        self.assertIsInstance(token, str)
        parts = token.split(".")
        self.assertEqual(len(parts), 3)

        rand_hex, timestamp_str, sig = parts
        self.assertEqual(len(rand_hex), 32)
        self.assertTrue(timestamp_str.isdigit())
        self.assertEqual(len(sig), 64)

    def test_validate_csrf_token_valid(self):
        token = generate_csrf_token()
        self.assertTrue(validate_csrf_token(token))

    def test_validate_csrf_token_invalid_inputs(self):
        self.assertFalse(validate_csrf_token(None))
        self.assertFalse(validate_csrf_token(""))
        self.assertFalse(validate_csrf_token("invalid-token"))
        self.assertFalse(validate_csrf_token("a.b"))
        self.assertFalse(validate_csrf_token("a.b.c.d"))
        self.assertFalse(validate_csrf_token("a.notanint.sig"))

    def test_validate_csrf_token_tampered_signature(self):
        token = generate_csrf_token()
        parts = token.split(".")
        tampered = f"{parts[0]}.{parts[1]}.{'0' * 64}"
        self.assertFalse(validate_csrf_token(tampered))

    def test_validate_csrf_token_expired(self):
        past_time = int(time.time()) - 100000
        rand_hex = "0123456789abcdef0123456789abcdef"
        import hashlib, hmac
        from app.config.config import settings
        key = settings.JWT_SECRET_KEY.encode("utf-8")
        msg = f"{rand_hex}:{past_time}".encode("utf-8")
        sig = hmac.new(key, msg, hashlib.sha256).hexdigest()
        expired_token = f"{rand_hex}.{past_time}.{sig}"
        self.assertFalse(validate_csrf_token(expired_token))

    def test_validate_csrf_token_different_key(self):
        token = generate_csrf_token(secret_key="secret-key-1")
        self.assertFalse(validate_csrf_token(token, secret_key="secret-key-2"))
        self.assertTrue(validate_csrf_token(token, secret_key="secret-key-1"))


class TestVerifyCSRFDependency(unittest.IsolatedAsyncioTestCase):
    async def test_safe_methods_bypass_csrf(self):
        for method in ["GET", "HEAD", "OPTIONS"]:
            request = MagicMock()
            request.method = method
            # Should not raise exception
            await verify_csrf_token(request)

    async def test_state_changing_methods_missing_token_raises_403(self):
        for method in ["POST", "PUT", "PATCH", "DELETE"]:
            request = MagicMock()
            request.method = method
            request.headers = {}
            with self.assertRaises(CSRFValidationException) as ctx:
                await verify_csrf_token(request)
            self.assertEqual(ctx.exception.status_code, 403)
            self.assertIn("Missing CSRF token", ctx.exception.message)

    async def test_state_changing_methods_invalid_token_raises_403(self):
        request = MagicMock()
        request.method = "POST"
        request.headers = {"X-CSRF-Token": "invalid.token.signature"}
        with self.assertRaises(CSRFValidationException) as ctx:
            await verify_csrf_token(request)
        self.assertEqual(ctx.exception.status_code, 403)
        self.assertIn("Invalid or expired CSRF token", ctx.exception.message)

    async def test_state_changing_methods_valid_token_passes(self):
        valid_token = generate_csrf_token()
        for header_name in ["X-CSRF-Token", "x-csrf-token", "X-XSRF-TOKEN", "x-xsrf-token"]:
            request = MagicMock()
            request.method = "POST"
            request.headers = {header_name: valid_token}
            # Should not raise exception
            await verify_csrf_token(request)


class TestCSRFEndpoints(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from fastapi.testclient import TestClient
        from app.app import app
        cls.client = TestClient(app)

    def test_csrf_endpoints(self):
        for path in ["/csrf-token", "/api/v1/csrf-token", "/auth/csrf-token", "/api/v1/auth/csrf-token"]:
            res = self.client.get(path)
            self.assertEqual(res.status_code, 200, f"Failed for path {path}")
            data = res.json()
            self.assertTrue(data.get("success"))
            self.assertIn("csrf_token", data)
            token = data["csrf_token"]
            self.assertTrue(validate_csrf_token(token))
            self.assertEqual(res.headers.get("x-csrf-token"), token)
            self.assertIn("csrf_token", res.cookies)


if __name__ == "__main__":
    unittest.main()
