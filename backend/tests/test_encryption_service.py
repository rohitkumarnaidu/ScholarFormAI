from unittest.mock import MagicMock, patch, PropertyMock

import pytest

_FERNET_KEY = "9i6456Do-kfa42dcxz4XtNAQxhtv8JsCPAa8mf_uEkY="


class TestEncryptionService:
    def test_generate_key(self):
        from app.services.encryption_service import EncryptionService
        key = EncryptionService.generate_key()
        assert isinstance(key, str) and len(key) > 20

    def test_encrypt_then_decrypt(self):
        from app.services.encryption_service import EncryptionService
        svc = EncryptionService(key=_FERNET_KEY)
        plaintext = "sk-abc123secret"
        encrypted = svc.encrypt(plaintext)
        assert encrypted != plaintext
        decrypted = svc.decrypt(encrypted)
        assert decrypted == plaintext

    def test_encrypt_empty_raises(self):
        from app.services.encryption_service import EncryptionService
        svc = EncryptionService(key=_FERNET_KEY)
        with pytest.raises(ValueError, match="empty"):
            svc.encrypt("")

    def test_decrypt_empty_raises(self):
        from app.services.encryption_service import EncryptionService
        svc = EncryptionService(key=_FERNET_KEY)
        with pytest.raises(ValueError, match="empty"):
            svc.decrypt("")

    def test_decrypt_invalid_token_raises(self):
        from app.services.encryption_service import EncryptionService
        svc = EncryptionService(key=_FERNET_KEY)
        with pytest.raises(ValueError):
            svc.decrypt("not-a-valid-token")

    def test_uses_env_key(self):
        from app.services.encryption_service import EncryptionService
        with patch.dict("os.environ", {"ENCRYPTION_KEY": _FERNET_KEY}):
            svc = EncryptionService(key=None)
            result = svc.encrypt("test")
            assert svc.decrypt(result) == "test"

    def test_fernet_property(self):
        from app.services.encryption_service import EncryptionService
        from cryptography.fernet import Fernet
        svc = EncryptionService(key=_FERNET_KEY)
        assert isinstance(svc.fernet, Fernet)


    def test_auto_generated_key_when_env_not_set(self):
        from app.services.encryption_service import EncryptionService
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(RuntimeError, match="ENCRYPTION_KEY"):
                EncryptionService(key=None)

    def test_encrypt_decrypt_roundtrip_various(self):
        from app.services.encryption_service import EncryptionService
        svc = EncryptionService(key=_FERNET_KEY)
        for val in ["a", "test with spaces", "sk-abc123!@#$%", "0" * 1000]:
            assert svc.decrypt(svc.encrypt(val)) == val


class TestGetEncryptionService:
    def test_returns_singleton(self):
        from app.services.encryption_service import get_encryption_service
        with patch.dict("os.environ", {"ENCRYPTION_KEY": _FERNET_KEY}):
            from app.services.encryption_service import get_encryption_service as gs
            # Clear module cache to force fresh singleton
            import app.services.encryption_service as es_mod
            es_mod._encryption_service = None
            s1 = gs()
            s2 = gs()
            assert s1 is s2

    def test_uses_env_key_when_no_arg(self):
        from app.services.encryption_service import EncryptionService
        with patch.dict("os.environ", {"ENCRYPTION_KEY": _FERNET_KEY}):
            svc = EncryptionService()
            assert svc.decrypt(svc.encrypt("hello")) == "hello"
