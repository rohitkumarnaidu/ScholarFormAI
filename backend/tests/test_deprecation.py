from unittest.mock import AsyncMock, MagicMock, patch


class TestBuildDeprecationHeaders:
    def test_build_with_successor(self):
        from app.routers.deprecation import build_deprecation_headers
        headers = build_deprecation_headers("/api/v2/keys")
        assert headers["Deprecation"] == "true"
        assert "Sunset" in headers
        assert "successor-version" in headers["Link"]
        assert "/api/v2/keys" in headers["Link"]

    def test_build_without_successor(self):
        from app.routers.deprecation import build_deprecation_headers
        headers = build_deprecation_headers(None)
        assert headers["Deprecation"] == "true"
        assert "Link" not in headers

    def test_deprecation_date_constant(self):
        from app.routers.deprecation import DEPRECATION_DATE
        assert DEPRECATION_DATE == "2026-05-01"


class TestNormalizePath:
    def test_strips_trailing_slash(self):
        from app.routers.deprecation import normalize_path
        assert normalize_path("/api/v1/keys/") == "/api/v1/keys"

    def test_keeps_path_without_trailing_slash(self):
        from app.routers.deprecation import normalize_path
        assert normalize_path("/api/v1/keys") == "/api/v1/keys"

    def test_keeps_root(self):
        from app.routers.deprecation import normalize_path
        assert normalize_path("/") == "/"


class TestDeprecatedRoute:
    def test_successor_path_from_map(self):
        from app.routers.deprecation import DeprecatedRoute
        route = DeprecatedRoute.__new__(DeprecatedRoute)
        route.successor_map = {"/v1/old": "/v2/new"}
        route.path_format = "/v1/old"
        route.path = "/v1/old"
        assert route._successor_path() == "/v2/new"

    def test_successor_path_no_match(self):
        from app.routers.deprecation import DeprecatedRoute
        route = DeprecatedRoute.__new__(DeprecatedRoute)
        route.successor_map = {"/v1/other": "/v2/new"}
        route.path_format = "/v1/old"
        route.path = "/v1/old"
        assert route._successor_path() is None

    def test_successor_path_empty_map(self):
        from app.routers.deprecation import DeprecatedRoute
        route = DeprecatedRoute.__new__(DeprecatedRoute)
        route.successor_map = {}
        route.path_format = "/v1/old"
        route.path = "/v1/old"
        assert route._successor_path() is None

    def test_successor_path_uses_normalized(self):
        from app.routers.deprecation import DeprecatedRoute
        route = DeprecatedRoute.__new__(DeprecatedRoute)
        route.successor_map = {"/v1/old/": "/v2/new"}
        route.path_format = "/v1/old/"
        route.path = "/v1/old/"
        assert route._successor_path() == "/v2/new"

    def test_get_route_handler_returns_callable(self):
        from app.routers.deprecation import DeprecatedRoute

        async def dummy_handler(request):
            resp = MagicMock()
            resp.headers = {}
            return resp

        route = DeprecatedRoute.__new__(DeprecatedRoute)
        route.successor_map = {}
        route.path_format = "/v1/test"
        route.path = "/v1/test"

        with patch.object(DeprecatedRoute, "get_route_handler") as mock_super:
            mock_super.return_value = dummy_handler
            handler = route.get_route_handler()
            assert handler is dummy_handler

    def test_deprecation_headers_added_to_response(self):
        from app.routers.deprecation import build_deprecation_headers, DeprecatedRoute

        mock_response = MagicMock()
        mock_response.headers = {}

        mock_original = AsyncMock(return_value=mock_response)
        route = DeprecatedRoute.__new__(DeprecatedRoute)
        route.successor_map = {"/v1/old": "/v2/new"}
        route.path_format = "/v1/old"
        route.path = "/v1/old"

        headers = build_deprecation_headers(route._successor_path())
        mock_response.headers.update(headers)
        assert mock_response.headers.get("Deprecation") == "true"
        assert "Sunset" in mock_response.headers
        assert "successor-version" in mock_response.headers["Link"]

    def test_http_exception_gets_headers(self):
        from app.routers.deprecation import build_deprecation_headers, DeprecatedRoute
        from fastapi import HTTPException

        route = DeprecatedRoute.__new__(DeprecatedRoute)
        route.successor_map = {"/v1/old": "/v2/new"}
        route.path_format = "/v1/old"
        route.path = "/v1/old"

        headers = build_deprecation_headers(route._successor_path())

        orig_exc = HTTPException(404, "not found")
        merged_headers = {**(orig_exc.headers or {}), **headers}
        assert merged_headers["Deprecation"] == "true"
        combined_exc = HTTPException(404, "not found", headers=merged_headers)
        assert combined_exc.headers["Deprecation"] == "true"
        assert "Sunset" in combined_exc.headers
