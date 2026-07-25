import pytest


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "alive"
    assert "version" in data


def test_list_styles(client):
    response = client.get("/api/v1/styles")
    assert response.status_code == 200
    styles = response.json()
    assert isinstance(styles, list)
    assert len(styles) > 0
    assert styles[0]["id"] is not None


def test_get_style(client):
    response = client.get("/api/v1/styles/apa")
    assert response.status_code == 200
    style = response.json()
    assert style["id"] == "apa"
    assert style["name"] == "APA 7th Edition"


def test_get_style_not_found(client):
    response = client.get("/api/v1/styles/nonexistent")
    assert response.status_code == 404


def test_validate_manuscript(client, sample_manuscript):
    response = client.post("/api/v1/validate", json={
        "manuscript": sample_manuscript.model_dump(),
        "style_id": "apa",
    })
    assert response.status_code == 200
    data = response.json()
    assert "valid" in data
    assert "errors" in data
    assert "warnings" in data


def test_validate_missing_title(client):
    manuscript = {
        "title": "",
        "authors": [],
        "sections": [],
    }
    response = client.post("/api/v1/validate", json={
        "manuscript": manuscript,
        "style_id": "apa",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is False
    assert any(e["code"] == "MISSING_TITLE" for e in data["errors"])


def test_format_manuscript(client, sample_manuscript):
    response = client.post("/api/v1/format", json={
        "manuscript": sample_manuscript.model_dump(),
        "style_id": "apa",
    })
    assert response.status_code == 200
    data = response.json()
    assert "download_url" in data
    assert data["style_applied"] == "apa"


def test_format_invalid_style(client, sample_manuscript):
    response = client.post("/api/v1/format", json={
        "manuscript": sample_manuscript.model_dump(),
        "style_id": "nonexistent",
    })
    assert response.status_code == 404


def test_preview_manuscript(client, sample_manuscript):
    response = client.post("/api/v1/preview", json={
        "manuscript": sample_manuscript.model_dump(),
        "style_id": "mla",
    })
    assert response.status_code == 200
    data = response.json()
    assert "html" in data
    assert data["style_applied"] == "mla"


def test_all_styles_have_names(client):
    response = client.get("/api/v1/styles")
    styles = response.json()
    for style in styles:
        assert "name" in style
        assert "id" in style
        assert "description" in style
