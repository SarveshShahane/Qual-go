import unittest
from unittest.mock import AsyncMock, MagicMock, patch
import uuid
from datetime import datetime, timezone
import jwt
from pydantic import ValidationError

from app.config.config import settings
from app.database.sql.models.refresh_token import RefreshToken
from app.database.sql.models.user import User as UserModel
from app.exceptions.auth import (
    BaseAuthException,
    InvalidCredentialsException,
    UserAlreadyExistException,
    UserNotFoundException,
)
from app.schemas.auth import LoginRequestPayload, RegisterRequestPayload
from app.services.auth import (
    AuthService,
    create_access_token,
    create_refresh_token,
    hash_password,
    hash_token,
    revoke_refresh_token,
    verify_password,
)


class TestPasswordHashing(unittest.TestCase):
    def test_hash_password_returns_bcrypt_hash(self):
        password = "SecurePassword123!"
        hashed = hash_password(password)

        self.assertIsInstance(hashed, str)
        self.assertTrue(hashed.startswith("$2b$"))
        self.assertNotEqual(password, hashed)

    def test_hash_password_generates_unique_salts(self):
        password = "IdenticalPassword123!"
        hash1 = hash_password(password)
        hash2 = hash_password(password)

        self.assertNotEqual(hash1, hash2)
        self.assertTrue(verify_password(password, hash1))
        self.assertTrue(verify_password(password, hash2))

    def test_verify_password_success(self):
        password = "MySuperSecretPassword@2026"
        hashed = hash_password(password)

        self.assertTrue(verify_password(password, hashed))

    def test_verify_password_failure(self):
        password = "CorrectPassword123!"
        wrong_password = "WrongPassword123!"
        hashed = hash_password(password)

        self.assertFalse(verify_password(wrong_password, hashed))
        self.assertFalse(verify_password("", hashed))


class TestTokenHashing(unittest.TestCase):
    def test_hash_token_sha256_format(self):
        sample_token = "some-random-refresh-token-value"
        token_hash = hash_token(sample_token)

        self.assertIsInstance(token_hash, str)
        self.assertEqual(len(token_hash), 64) 
        self.assertTrue(all(c in "0123456789abcdef" for c in token_hash))

    def test_hash_token_is_deterministic(self):
        sample_token = "deterministic-token-12345"
        hash1 = hash_token(sample_token)
        hash2 = hash_token(sample_token)

        self.assertEqual(hash1, hash2)

    def test_hash_token_different_inputs_produce_different_hashes(self):
        hash1 = hash_token("token_alpha")
        hash2 = hash_token("token_beta")

        self.assertNotEqual(hash1, hash2)


class TestTokenCreation(unittest.TestCase):
    def test_create_access_token_payload(self):
        user_id = 42
        email = "quantum_dev@egreenquanta.org"

        token = create_access_token(user_id=user_id, email=email)
        self.assertIsInstance(token, str)

        decoded = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )

        self.assertEqual(decoded["user_id"], user_id)
        self.assertEqual(decoded["email"], email)
        self.assertEqual(decoded["type"], "access")
        self.assertIn("iat", decoded)
        self.assertIn("exp", decoded)
        self.assertGreater(decoded["exp"], decoded["iat"])

    def test_create_refresh_token_payload_and_metadata(self):
        user_id = 101

        token, jti, expire = create_refresh_token(user_id=user_id)

        self.assertIsInstance(token, str)
        self.assertIsInstance(jti, str)
        self.assertIsInstance(expire, datetime)

        parsed_uuid = uuid.UUID(jti)
        self.assertEqual(str(parsed_uuid), jti)

        decoded = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )

        self.assertEqual(decoded["user_id"], user_id)
        self.assertEqual(decoded["jti"], jti)
        self.assertEqual(decoded["type"], "refresh")
        self.assertIn("iat", decoded)
        self.assertIn("exp", decoded)
        self.assertGreater(decoded["exp"], decoded["iat"])


class TestRevokeRefreshToken(unittest.IsolatedAsyncioTestCase):
    async def test_revoke_refresh_token_success(self):
        token_str = "valid-active-refresh-token"
        expected_hash = hash_token(token_str)

        mock_db_token = MagicMock(spec=RefreshToken)
        mock_db_token.token_hash = expected_hash
        mock_db_token.revoked_at = None

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_db_token

        mock_session = AsyncMock()
        mock_session.execute.return_value = mock_result

        success = await revoke_refresh_token(mock_session, token_str)

        self.assertTrue(success)
        self.assertIsNotNone(mock_db_token.revoked_at)
        mock_session.commit.assert_awaited_once()

    async def test_revoke_refresh_token_not_found(self):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None

        mock_session = AsyncMock()
        mock_session.execute.return_value = mock_result

        success = await revoke_refresh_token(mock_session, "non-existent-token")

        self.assertFalse(success)
        mock_session.commit.assert_not_awaited()


class TestAuthServiceRegister(unittest.IsolatedAsyncioTestCase):
    async def test_register_new_user_success(self):
        payload = RegisterRequestPayload(
            username="quantum_user",
            email="new_user@qual.dev",
            password="StrongPassword123!",
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None  

        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        mock_session.execute.return_value = mock_result

        service = AuthService(mock_session)
        new_user = await service.register(payload)

        self.assertIsInstance(new_user, UserModel)
        self.assertEqual(new_user.username, payload.username)
        self.assertEqual(new_user.email, payload.email)
        self.assertTrue(verify_password(payload.password, new_user.password))

        mock_session.add.assert_called_once_with(new_user)
        mock_session.commit.assert_awaited_once()
        mock_session.refresh.assert_awaited_once_with(new_user)

    async def test_register_duplicate_user_raises_exception(self):
        payload = RegisterRequestPayload(
            username="existing_user",
            email="duplicate@qual.dev",
            password="StrongPassword123!",
        )

        existing_user = UserModel(
            id=1,
            username="existing_user",
            email="duplicate@qual.dev",
            password=hash_password("AlreadySet123!"),
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_user

        mock_session = AsyncMock()
        mock_session.execute.return_value = mock_result

        service = AuthService(mock_session)

        with self.assertRaises(UserAlreadyExistException):
            await service.register(payload)

        mock_session.add.assert_not_called()
        mock_session.commit.assert_not_awaited()


class TestAuthServiceLogin(unittest.IsolatedAsyncioTestCase):
    async def test_login_success(self):
        password = "CorrectPassword123!"
        user = UserModel(
            id=7,
            username="dr_quanta",
            email="quanta@egreenquanta.org",
            password=hash_password(password),
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = user

        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        mock_session.execute.return_value = mock_result

        service = AuthService(mock_session)
        payload = LoginRequestPayload(
            email="quanta@egreenquanta.org",
            password=password,
        )

        access_token, refresh_token, authenticated_user = await service.login(payload)

        self.assertEqual(authenticated_user.id, user.id)
        self.assertEqual(authenticated_user.email, user.email)
        self.assertIsInstance(access_token, str)
        self.assertIsInstance(refresh_token, str)

        mock_session.add.assert_called_once()
        saved_refresh_token = mock_session.add.call_args[0][0]
        self.assertIsInstance(saved_refresh_token, RefreshToken)
        self.assertEqual(saved_refresh_token.user_id, user.id)
        self.assertEqual(saved_refresh_token.token_hash, hash_token(refresh_token))
        mock_session.commit.assert_awaited_once()

    async def test_login_user_not_found(self):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None

        mock_session = AsyncMock()
        mock_session.execute.return_value = mock_result

        service = AuthService(mock_session)
        payload = LoginRequestPayload(
            email="notfound@qual.dev",
            password="Password123!",
        )

        with self.assertRaises(InvalidCredentialsException):
            await service.login(payload)

        mock_session.commit.assert_not_awaited()

    async def test_login_wrong_password(self):
        user = UserModel(
            id=12,
            username="alice",
            email="alice@qual.dev",
            password=hash_password("HerRealPassword123!"),
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = user

        mock_session = AsyncMock()
        mock_session.execute.return_value = mock_result

        service = AuthService(mock_session)
        payload = LoginRequestPayload(
            email="alice@qual.dev",
            password="WrongPassword999!",
        )

        with self.assertRaises(InvalidCredentialsException):
            await service.login(payload)

        mock_session.commit.assert_not_awaited()


class TestAuthServiceLogout(unittest.IsolatedAsyncioTestCase):
    async def test_logout_with_token_calls_revoke(self):
        mock_session = AsyncMock()
        service = AuthService(mock_session)

        with patch("app.services.auth.revoke_refresh_token", new_callable=AsyncMock) as mock_revoke:
            mock_revoke.return_value = True

            result = await service.logout("some-refresh-token")
            self.assertTrue(result)
            mock_revoke.assert_awaited_once_with(mock_session, "some-refresh-token")

    async def test_logout_without_token_returns_false(self):
        mock_session = AsyncMock()
        service = AuthService(mock_session)

        with patch("app.services.auth.revoke_refresh_token", new_callable=AsyncMock) as mock_revoke:
            result = await service.logout(None)
            self.assertFalse(result)
            mock_revoke.assert_not_awaited()


class TestAuthServiceRefreshTokens(unittest.IsolatedAsyncioTestCase):
    async def test_refresh_tokens_missing_token_raises(self):
        mock_session = AsyncMock()
        service = AuthService(mock_session)
        with self.assertRaises(InvalidCredentialsException):
            await service.refresh_tokens(None)

    async def test_refresh_tokens_invalid_jwt_raises(self):
        mock_session = AsyncMock()
        service = AuthService(mock_session)
        with self.assertRaises(InvalidCredentialsException):
            await service.refresh_tokens("not-a-valid-jwt")

    async def test_refresh_tokens_success(self):
        user_id = 99
        email = "refresh_user@qual.dev"
        token, jti, expire = create_refresh_token(user_id=user_id)

        user = UserModel(id=user_id, username="refresh_user", email=email, password="hash")
        db_token = RefreshToken(
            id=1,
            user_id=user_id,
            jti=jti,
            token_hash=hash_token(token),
            expires_at=expire,
            revoked_at=None,
        )

        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        # Mock finding the refresh token, then finding the user
        result1 = MagicMock()
        result1.scalar_one_or_none.return_value = db_token
        result2 = MagicMock()
        result2.scalar_one_or_none.return_value = user
        mock_session.execute.side_effect = [result1, result2]

        service = AuthService(mock_session)
        new_access, new_refresh, returned_user = await service.refresh_tokens(token)

        self.assertIsInstance(new_access, str)
        self.assertIsInstance(new_refresh, str)
        self.assertEqual(returned_user.id, user_id)
        self.assertIsNotNone(db_token.revoked_at)
        mock_session.commit.assert_awaited()


class TestAuthSchemas(unittest.TestCase):
    def test_register_payload_valid(self):
        payload = RegisterRequestPayload(
            username="quantum_pro",
            email="valid@example.com",
            password="SecurePassword123!",
        )
        self.assertEqual(payload.username, "quantum_pro")
        self.assertEqual(payload.email, "valid@example.com")

    def test_register_payload_invalid_email(self):
        with self.assertRaises(ValidationError):
            RegisterRequestPayload(
                username="valid_user",
                email="not-an-email",
                password="SecurePassword123!",
            )

    def test_register_payload_password_too_short(self):
        with self.assertRaises(ValidationError):
            RegisterRequestPayload(
                username="valid_user",
                email="valid@example.com",
                password="short",
            )

    def test_register_payload_username_too_short(self):
        with self.assertRaises(ValidationError):
            RegisterRequestPayload(
                username="ab",
                email="valid@example.com",
                password="SecurePassword123!",
            )

    def test_login_payload_valid(self):
        payload = LoginRequestPayload(
            email="student@egreenquanta.org",
            password="ValidPassword123!",
        )
        self.assertEqual(payload.email, "student@egreenquanta.org")


class TestAuthExceptions(unittest.TestCase):
    def test_auth_exception_status_codes(self):
        exc_duplicate = UserAlreadyExistException()
        self.assertEqual(exc_duplicate.status, 409)
        self.assertIn("already exists", exc_duplicate.message)

        exc_invalid = InvalidCredentialsException()
        self.assertEqual(exc_invalid.status, 401)
        self.assertIn("Invalid email or password", exc_invalid.message)

        exc_not_found = UserNotFoundException()
        self.assertEqual(exc_not_found.status, 404)
        self.assertIn("User not found", exc_not_found.message)


if __name__ == "__main__":
    unittest.main()