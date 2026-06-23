# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.user import User
from app.utils.dependencies import get_optional_user


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def authenticated_user():
    user = User(id="user-123", email="user@example.com", role="authenticated")
    app.dependency_overrides[get_optional_user] = lambda: user
    yield user
    app.dependency_overrides.pop(get_optional_user, None)


def _mock_table_chain() -> MagicMock:
    table = MagicMock()
    table.select.return_value = table
    table.eq.return_value = table
    table.order.return_value = table
    table.insert.return_value = table
    table.update.return_value = table
    table.delete.return_value = table
    table.maybe_single.return_value = table
    return table


def test_list_custom_templates_requires_auth(client):
    response = client.get("/api/v1/templates/custom")
    assert response.status_code == 401
    payload = response.json()
    assert payload["data"] is None
    assert payload["error"]["code"] == "UNAUTHORIZED"
    assert payload["error"]["message"] == "Authentication required"


def test_custom_template_crud(client, authenticated_user):
    user_id = authenticated_user.id
    base_template = {
        "id": "tpl-1",
        "user_id": user_id,
        "name": "My Custom Template",
        "description": "test",
        "config": {"font_family": "Times New Roman", "font_size": 12},
        "created_at": "2026-02-26T10:00:00+00:00",
        "updated_at": "2026-02-26T10:00:00+00:00",
    }

    # Create
    create_table = _mock_table_chain()
    create_table.execute.return_value = SimpleNamespace(data=[base_template])
    create_sb = MagicMock()
    create_sb.table.return_value = create_table
    with patch("app.routers.v1.templates.get_supabase_client", return_value=create_sb):
        response = client.post(
            "/api/v1/templates/custom",
            json={"template": {"name": "My Custom Template", "settings": {"font_family": "Times New Roman"}}},
        )
    assert response.status_code == 200
    assert response.json()["data"]["template"]["name"] == "My Custom Template"

    # List
    list_table = _mock_table_chain()
    list_table.execute.return_value = SimpleNamespace(data=[base_template])
    list_sb = MagicMock()
    list_sb.table.return_value = list_table
    with patch("app.routers.v1.templates.get_supabase_client", return_value=list_sb):
        response = client.get("/api/v1/templates/custom")
    assert response.status_code == 200
    assert len(response.json()["data"]["templates"]) == 1

    # Update
    updated_template = dict(base_template)
    updated_template["name"] = "Updated Template"
    update_table = _mock_table_chain()
    update_table.execute.return_value = SimpleNamespace(data=[updated_template])
    update_sb = MagicMock()
    update_sb.table.return_value = update_table
    with patch("app.routers.v1.templates.get_supabase_client", return_value=update_sb):
        response = client.put(
            "/api/v1/templates/custom/tpl-1",
            json={"template": {"name": "Updated Template", "settings": {"font_family": "Cambria"}}},
        )
    assert response.status_code == 200
    assert response.json()["data"]["template"]["name"] == "Updated Template"

    # Delete
    delete_table = _mock_table_chain()
    delete_table.execute.side_effect = [
        SimpleNamespace(data={"id": "tpl-1"}),
        SimpleNamespace(data=[{"id": "tpl-1"}]),
    ]
    delete_sb = MagicMock()
    delete_sb.table.return_value = delete_table
    with patch("app.routers.v1.templates.get_supabase_client", return_value=delete_sb):
        response = client.delete("/api/v1/templates/custom/tpl-1")
    assert response.status_code == 200
    assert response.json()["data"]["status"] == "deleted"


def test_custom_template_validation(client, authenticated_user):
    sb = MagicMock()
    with patch("app.routers.v1.templates.get_supabase_client", return_value=sb):
        response = client.post(
            "/api/v1/templates/custom",
            json={"template": {"name": "Invalid Config", "settings": ["not", "an", "object"]}},
        )
    assert response.status_code == 422
    payload = response.json()
    assert payload["data"] is None
    assert payload["error"]["code"] == "INVALID_TEMPLATE_PAYLOAD"
    assert "config" in payload["error"]["message"].lower()


def test_list_builtin_templates_response_shape(client):
    response = client.get("/api/v1/templates")
    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload.get("data"), dict)
    assert isinstance(payload["data"].get("templates"), list)


def test_csl_search_uses_q_and_returns_results(client):
    mocked_results = [{"slug": "nature", "title": "Nature"}]
    with patch("app.routers.v1.templates.search_styles", new=AsyncMock(return_value=mocked_results)) as mocked_search:
        response = client.get("/api/v1/templates/csl/search?q=nature")

    assert response.status_code == 200
    assert response.json()["data"] == {"query": "nature", "results": mocked_results}
    mocked_search.assert_awaited_once_with("nature")


def test_csl_fetch_by_style_id_uses_get(client):
    mocked_style = {"slug": "ieee", "source": "local", "content": "<style />"}
    with patch("app.routers.v1.templates.fetch_style", new=AsyncMock(return_value=mocked_style)) as mocked_fetch:
        response = client.get("/api/v1/templates/csl/ieee")

    assert response.status_code == 200
    assert response.json()["data"] == mocked_style
    mocked_fetch.assert_awaited_once_with("ieee")
