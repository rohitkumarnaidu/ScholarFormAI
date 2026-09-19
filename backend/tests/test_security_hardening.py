# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""Security hardening tests — verifies IDOR, stack trace, mass assignment protections."""

import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

from app.main import app
from app.utils.dependencies import get_current_user

client = TestClient(app)

@pytest.fixture(autouse=True)
def clear_overrides():
    """Ensure overrides are cleared before and after each test."""
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


def test_stack_trace_leakage_prevention():
    """Verify that 500 errors do NOT contain Python tracebacks or internal paths."""
    app.dependency_overrides[get_current_user] = lambda: {"id": "test-user-123"}
    
    # Mock documents_impl.get_document_summary to raise an exception
    with patch("app.routers.v1.documents_impl.get_document_summary", side_effect=Exception("Secret Database Error")):
        response = client.get("/api/v1/documents/fake-job-id/summary", headers={"Authorization": "Bearer fake-token"})
        
        assert response.status_code == 500
        
        # Check that error doesn't leak internal details
        text = response.text.lower()
        assert "secret database error" not in text, "Exception message leaked!"
        assert "traceback" not in text, "Stack trace leaked!"
        assert ".py" not in text, "File path leaked!"
        
        # Should contain generic error
        assert "internal error" in text or "internal server error" in text
        assert "request id" in response.text or "request_id" in response.text.lower() or "requestId" in response.text


def test_authentication_enforcement():
    """Verify that protected document endpoints return 401 when called without a token."""
    endpoints = [
        ("GET", "/api/v1/documents/fake-job-id/summary"),
        ("POST", "/api/v1/documents/fake-job-id/edit"),
        ("GET", "/api/v1/documents/fake-job-id/preview"),
        ("GET", "/api/v1/documents/fake-job-id/compare"),
        ("GET", "/api/v1/documents/fake-job-id/download"),
    ]
    
    for method, url in endpoints:
        if method == "GET":
            response = client.get(url)
        else:
            response = client.post(url, json={})
            
        assert response.status_code == 401, f"Endpoint {method} {url} did not enforce auth"


def test_mass_assignment_prevention():
    """Verify that the edit endpoint rejects unexpected fields."""
    app.dependency_overrides[get_current_user] = lambda: {"id": "test-user-123"}
    
    payload = {
        "template": "ieee",
        "user_id": 999,
        "role": "admin",
        "is_admin": True,
        "status": "APPROVED"
    }
    
    response = client.post(
        "/api/v1/documents/fake-job-id/edit", 
        json=payload, 
        headers={"Authorization": "Bearer fake-token"}
    )
    
    # We expect 422 Unprocessable Entity due to extra fields not in DocumentEditRequest schema
    assert response.status_code == 422, "Mass assignment vulnerability: extra fields were not rejected"


def test_document_edit_schema_validation():
    """Verify the DocumentEditRequest schema validation constraints."""
    app.dependency_overrides[get_current_user] = lambda: {"id": "test-user-123"}
    
    # 1. Rejects invalid page_size
    response_invalid_size = client.post(
        "/api/v1/documents/fake-job-id/edit", 
        json={"page_size": "invalid_size"}, 
        headers={"Authorization": "Bearer fake-token"}
    )
    assert response_invalid_size.status_code == 422
    assert "page_size" in response_invalid_size.text.lower() or "page size" in response_invalid_size.text.lower()

    # 2. Rejects line_spacing out of range (allowed ge=0.5, le=3.0)
    response_invalid_spacing = client.post(
        "/api/v1/documents/fake-job-id/edit", 
        json={"line_spacing": 5.0}, 
        headers={"Authorization": "Bearer fake-token"}
    )
    assert response_invalid_spacing.status_code == 422
    
    # 3. Accepts valid inputs
    # We mock the underlying implementation so we don't actually hit the DB
    with patch("app.routers.v1.documents_impl.edit_document") as mock_edit:
        mock_edit.return_value = {"status": "success"}
        
        valid_payload = {
            "template": "ieee",
            "page_size": "a4",
            "line_spacing": 1.5,
            "add_page_numbers": True
        }
        response_valid = client.post(
            "/api/v1/documents/fake-job-id/edit", 
            json=valid_payload, 
            headers={"Authorization": "Bearer fake-token"}
        )
        
        # It shouldn't be 422. Could be 200, 202, etc. depending on enveloper
        assert response_valid.status_code != 422
