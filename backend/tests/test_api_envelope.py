from datetime import UTC, datetime

import pytest
from pydantic import ValidationError


class TestAPIError:
    def test_required_fields(self):
        from app.schemas.api_envelope import APIError
        err = APIError(code="NOT_FOUND", message="Not found")
        assert err.code == "NOT_FOUND"
        assert err.message == "Not found"
        assert err.details is None

    def test_with_details(self):
        from app.schemas.api_envelope import APIError
        err = APIError(code="ERR", message="msg", details={"field": "value"})
        assert err.details == {"field": "value"}

    def test_missing_required_fields(self):
        from app.schemas.api_envelope import APIError
        with pytest.raises(ValidationError):
            APIError()


class TestAPIResponse:
    def test_required_fields(self):
        from app.schemas.api_envelope import APIResponse
        resp = APIResponse(request_id="req-1")
        assert resp.data is None
        assert resp.error is None
        assert resp.request_id == "req-1"
        assert isinstance(resp.timestamp, datetime)

    def test_with_data(self):
        from app.schemas.api_envelope import APIResponse
        resp = APIResponse(data={"key": "val"}, request_id="req-1")
        assert resp.data == {"key": "val"}

    def test_with_error(self):
        from app.schemas.api_envelope import APIError, APIResponse
        err = APIError(code="ERR", message="msg")
        resp = APIResponse(error=err, request_id="req-1")
        assert resp.error.code == "ERR"

    def test_timestamp_is_utc(self):
        from app.schemas.api_envelope import APIResponse
        resp = APIResponse(request_id="req-1")
        assert resp.timestamp.tzinfo is not None
        assert resp.timestamp.tzinfo == UTC

    def test_missing_request_id_raises(self):
        from app.schemas.api_envelope import APIResponse
        with pytest.raises(ValidationError):
            APIResponse()


class TestSuccessResponse:
    def test_returns_api_response_with_data(self):
        from app.schemas.api_envelope import success_response
        resp = success_response({"result": "ok"}, "req-1")
        assert resp.data == {"result": "ok"}
        assert resp.error is None
        assert resp.request_id == "req-1"

    def test_returns_api_response_with_none_data(self):
        from app.schemas.api_envelope import success_response
        resp = success_response(None, "req-1")
        assert resp.data is None


class TestErrorResponse:
    def test_returns_api_response_with_error(self):
        from app.schemas.api_envelope import error_response
        resp = error_response("ERR_CODE", "Error message", "req-1")
        assert resp.data is None
        assert resp.error.code == "ERR_CODE"
        assert resp.error.message == "Error message"
        assert resp.request_id == "req-1"

    def test_with_details(self):
        from app.schemas.api_envelope import error_response
        resp = error_response("ERR", "msg", "req-1", details={"field": "val"})
        assert resp.error.details == {"field": "val"}
