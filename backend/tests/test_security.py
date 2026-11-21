import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.core.security import hash_password, verify_password


def test_password_hash_uses_argon2_and_verifies_only_correct_password():
    password = "secure-example-password"
    password_hash = hash_password(password)

    assert password_hash.startswith("$argon2id$")
    assert password_hash != password
    assert verify_password(password, password_hash)
    assert not verify_password("incorrect-password", password_hash)
    assert not verify_password(password, "not-a-valid-hash")


def test_settings_reject_placeholder_jwt_secret():
    with pytest.raises(ValidationError, match="generated secret"):
        Settings(
            database_url="sqlite+pysqlite:///:memory:",
            secret_key="replace_with_a_generated_secret",
        )


def test_production_settings_reject_placeholder_database_password():
    with pytest.raises(ValidationError, match="generated DB_PASSWORD"):
        Settings(
            app_env="production",
            database_url="sqlite+pysqlite:///:memory:",
            db_password="replace_with_a_generated_password",
            redis_url="redis://localhost:6379/0",
            resume_encryption_key="a" * 48,
            secret_key="generated-test-signing-secret-with-enough-entropy",
        )


def test_production_settings_reject_placeholder_resume_encryption_key():
    with pytest.raises(ValidationError, match="RESUME_ENCRYPTION_KEY must be generated"):
        Settings(
            app_env="production",
            database_url="sqlite+pysqlite:///:memory:",
            db_password="generated-test-database-password",
            redis_url="redis://localhost:6379/0",
            resume_encryption_key="replace_with_a_generated_resume_encryption_key",
            secret_key="generated-test-signing-secret-with-enough-entropy",
        )
