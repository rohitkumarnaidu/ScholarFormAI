# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from urllib.parse import urlparse, parse_qsl

from app.services.document_service import DocumentService


def test_signed_download_verification():
    secret = "test-secret"
    file_path = "/tmp/test.docx"
    file_url = "http://testserver/api/v1/documents/123/download?format=docx"

    signed = DocumentService.generate_signed_download_url(
        file_url=file_url,
        file_path=file_path,
        secret=secret,
        expires_in_seconds=3600,
    )
    parsed = urlparse(signed["url"])
    query = dict(parse_qsl(parsed.query))

    assert DocumentService.verify_signed_download(
        file_path=file_path,
        token=query["token"],
        expires=int(query["expires"]),
        secret=secret,
        download_format="docx",
    )


def test_signed_download_expiry():
    secret = "test-secret"
    file_path = "/tmp/test.docx"
    assert not DocumentService.verify_signed_download(
        file_path=file_path,
        token="invalid",
        expires=1,
        secret=secret,
    )


def test_signed_download_token_is_bound_to_requested_format():
    secret = "test-secret"
    file_path = "/tmp/test.docx"
    file_url = "http://testserver/api/v1/documents/123/download?format=docx"

    signed = DocumentService.generate_signed_download_url(
        file_url=file_url,
        file_path=file_path,
        secret=secret,
        expires_in_seconds=3600,
        download_format="docx",
    )
    parsed = urlparse(signed["url"])
    query = dict(parse_qsl(parsed.query))

    assert DocumentService.verify_signed_download(
        file_path=file_path,
        token=query["token"],
        expires=int(query["expires"]),
        secret=secret,
        download_format="docx",
    )
    assert not DocumentService.verify_signed_download(
        file_path=file_path,
        token=query["token"],
        expires=int(query["expires"]),
        secret=secret,
        download_format="pdf",
    )
