# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

from types import SimpleNamespace

from app.pipeline.services.grobid_client import GROBIDClient


def test_grobid_client_uses_hard_timeout_from_settings(monkeypatch):
    monkeypatch.setattr("app.pipeline.services.grobid_client.settings.GROBID_TIMEOUT", 120, raising=False)
    monkeypatch.setattr("app.pipeline.services.grobid_client.settings.GROBID_MAX_RETRIES", 2, raising=False)

    local_client = GROBIDClient(base_url="http://localhost:8070")
    remote_client = GROBIDClient(base_url="https://example-grobid.hf.space")

    # Local timeout remains strict; remote hosted endpoint gets a higher cap for cold starts.
    assert local_client.timeout == 30
    assert remote_client.timeout == 90
    assert local_client.max_retries == 2
    assert remote_client.max_retries == 2


def test_grobid_client_is_available_handles_request_errors(monkeypatch):
    client = GROBIDClient(base_url="http://grobid.local:8070")

    def failing_request(*args, **kwargs):
        raise RuntimeError("network down")

    monkeypatch.setattr("app.pipeline.services.grobid_client.requests.request", failing_request)
    assert client.is_available() is False


def test_grobid_client_request_sets_timeout_tuple(monkeypatch):
    client = GROBIDClient(base_url="http://grobid.local:8070")
    captured = {}

    def fake_request(method, url, **kwargs):
        captured["timeout"] = kwargs.get("timeout")
        return SimpleNamespace(status_code=200, text="<tei></tei>")

    monkeypatch.setattr("app.pipeline.services.grobid_client.requests.request", fake_request)
    response = client._request("GET", "http://grobid.local:8070/api/isalive")

    assert response.status_code == 200
    assert isinstance(captured["timeout"], tuple)


def test_grobid_client_prefers_url_list_over_single(monkeypatch):
    monkeypatch.setattr(
        "app.pipeline.services.grobid_client.settings.get_grobid_urls",
        lambda: ["https://primary-grobid.example", "https://shadow-grobid.example"],
        raising=False,
    )

    client = GROBIDClient()
    assert client.base_urls[0] == "https://primary-grobid.example"
    assert client.base_urls[1] == "https://shadow-grobid.example"


def test_grobid_client_failover_to_shadow_on_transient_error(monkeypatch, tmp_path):
    monkeypatch.setattr("app.pipeline.services.grobid_client.settings.GROBID_MAX_RETRIES", 1, raising=False)
    monkeypatch.setattr("app.pipeline.services.grobid_client.settings.GROBID_TIMEOUT", 15, raising=False)
    monkeypatch.setattr(
        "app.pipeline.services.grobid_client.settings.get_grobid_urls",
        lambda: ["https://primary-grobid.example", "https://shadow-grobid.example"],
        raising=False,
    )
    monkeypatch.setattr(
        "app.pipeline.services.grobid_client.settings.get_service_health_path",
        lambda _name: "/api/isalive",
        raising=False,
    )
    monkeypatch.setattr("app.pipeline.services.grobid_client.time.sleep", lambda _seconds: None)

    primary_xml_failure = SimpleNamespace(status_code=502, text="")
    shadow_xml_success = SimpleNamespace(
        status_code=200,
        text="<TEI xmlns='http://www.tei-c.org/ns/1.0'><teiHeader/></TEI>",
    )

    def fake_request(method, url, **kwargs):
        if url.startswith("https://primary-grobid.example"):
            return primary_xml_failure
        if url.startswith("https://shadow-grobid.example"):
            return shadow_xml_success
        return SimpleNamespace(status_code=500, text="")

    monkeypatch.setattr("app.pipeline.services.grobid_client.requests.request", fake_request)

    sample_pdf = tmp_path / "sample.pdf"
    sample_pdf.write_bytes(b"%PDF-1.4\n%test")

    client = GROBIDClient()
    metadata = client.process_header_document(str(sample_pdf))

    assert metadata["source"] == "grobid"
    assert client.base_url == "https://shadow-grobid.example"


def test_grobid_client_backoff_is_bounded():
    client = GROBIDClient(base_url="http://localhost:8070")
    assert client._retry_backoff_seconds(1) == 1.0
    assert client._retry_backoff_seconds(2) == 2.0
    assert client._retry_backoff_seconds(6) == 8.0


def test_grobid_client_prioritizes_recent_last_good_endpoint(monkeypatch):
    monkeypatch.setattr(
        "app.pipeline.services.grobid_client.settings.get_grobid_urls",
        lambda: ["https://primary-grobid.example", "https://shadow-grobid.example"],
        raising=False,
    )
    client = GROBIDClient()
    client._mark_last_good_base_url("https://shadow-grobid.example", reason="test")
    ordered = client._ordered_base_urls()
    assert ordered[0] == "https://shadow-grobid.example"
