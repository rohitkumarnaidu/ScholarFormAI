

class TestDatabaseUnavailableError:
    def test_default_message(self):
        from app.exceptions import DatabaseUnavailableError
        err = DatabaseUnavailableError()
        assert str(err) == "Database is currently unavailable."

    def test_custom_message(self):
        from app.exceptions import DatabaseUnavailableError
        err = DatabaseUnavailableError("Custom message")
        assert str(err) == "Custom message"


class TestDocumentNotFoundError:
    def test_default_message(self):
        from app.exceptions import DocumentNotFoundError
        err = DocumentNotFoundError()
        assert str(err) == "Document not found."

    def test_with_doc_id(self):
        from app.exceptions import DocumentNotFoundError
        err = DocumentNotFoundError(doc_id="doc-123")
        assert str(err) == "Document not found: doc-123"
        assert err.doc_id == "doc-123"

    def test_no_doc_id(self):
        from app.exceptions import DocumentNotFoundError
        err = DocumentNotFoundError(doc_id=None)
        assert err.doc_id is None


class TestAuthenticationError:
    def test_default_message(self):
        from app.exceptions import AuthenticationError
        err = AuthenticationError()
        assert str(err) == "Authentication failed."

    def test_custom_message(self):
        from app.exceptions import AuthenticationError
        err = AuthenticationError("Invalid token")
        assert str(err) == "Invalid token"


class TestRateLimitExceededError:
    def test_default_message(self):
        from app.exceptions import RateLimitExceededError
        err = RateLimitExceededError()
        assert str(err) == "Rate limit exceeded. Please try again later."

    def test_custom_message(self):
        from app.exceptions import RateLimitExceededError
        err = RateLimitExceededError("Too many requests")
        assert str(err) == "Too many requests"


class TestFileStorageError:
    def test_default_message(self):
        from app.exceptions import FileStorageError
        err = FileStorageError()
        assert str(err) == "File storage operation failed."

    def test_custom_message(self):
        from app.exceptions import FileStorageError
        err = FileStorageError("Disk full")
        assert str(err) == "Disk full"


class TestExternalServiceError:
    def test_default_message(self):
        from app.exceptions import ExternalServiceError
        err = ExternalServiceError()
        assert str(err) == "External service call failed."
        assert err.service is None

    def test_with_service(self):
        from app.exceptions import ExternalServiceError
        err = ExternalServiceError(service="GROBID")
        assert "GROBID" in str(err)
        assert err.service == "GROBID"

    def test_with_service_and_message(self):
        from app.exceptions import ExternalServiceError
        err = ExternalServiceError(service="LLM", message="Timeout")
        assert "LLM" in str(err)

    def test_service_is_none_by_default(self):
        from app.exceptions import ExternalServiceError
        err = ExternalServiceError()
        assert err.service is None


class TestExceptionHierarchy:
    def test_all_inherit_from_exception(self):
        from app.exceptions import (
            DatabaseUnavailableError,
            DocumentNotFoundError,
            AuthenticationError,
            RateLimitExceededError,
            FileStorageError,
            ExternalServiceError,
        )
        assert issubclass(DatabaseUnavailableError, Exception)
        assert issubclass(DocumentNotFoundError, Exception)
        assert issubclass(AuthenticationError, Exception)
        assert issubclass(RateLimitExceededError, Exception)
        assert issubclass(FileStorageError, Exception)
        assert issubclass(ExternalServiceError, Exception)

    def test_can_catch_as_exception(self):
        from app.exceptions import DocumentNotFoundError
        try:
            raise DocumentNotFoundError("doc-1")
        except Exception as e:
            assert isinstance(e, DocumentNotFoundError)
