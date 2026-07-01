import re
import time
from unittest.mock import MagicMock, patch, AsyncMock, PropertyMock, call

import pytest


class TestTTlHelpers:
    def test_now_iso_format(self):
        from app.services.generator_session_service import GeneratorSessionService
        iso = GeneratorSessionService._now_iso()
        assert re.match(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", iso)

    def test_session_ttl_default(self):
        from app.services.generator_session_service import GeneratorSessionService
        ttl = GeneratorSessionService._session_ttl_seconds()
        assert ttl == 2.0

    def test_session_ttl_from_settings(self):
        from app.services.generator_session_service import GeneratorSessionService
        with patch("app.services.generator_session_service.settings") as mock_s:
            mock_s.GENERATOR_SESSION_CACHE_TTL_SECONDS = 10
            assert GeneratorSessionService._session_ttl_seconds() == 10.0

    def test_session_ttl_clamps_negative(self):
        from app.services.generator_session_service import GeneratorSessionService
        with patch("app.services.generator_session_service.settings") as mock_s:
            mock_s.GENERATOR_SESSION_CACHE_TTL_SECONDS = -5
            assert GeneratorSessionService._session_ttl_seconds() == 0.0

    def test_messages_ttl_default(self):
        from app.services.generator_session_service import GeneratorSessionService
        assert GeneratorSessionService._messages_ttl_seconds() == 1.0

    def test_list_ttl_default(self):
        from app.services.generator_session_service import GeneratorSessionService
        assert GeneratorSessionService._session_list_ttl_seconds() == 3.0

    def test_document_ttl_default(self):
        from app.services.generator_session_service import GeneratorSessionService
        assert GeneratorSessionService._latest_document_ttl_seconds() == 2.0

    def test_ttl_bad_value_returns_fallback(self):
        from app.services.generator_session_service import GeneratorSessionService
        with patch("app.services.generator_session_service.settings") as mock_s:
            del mock_s.GENERATOR_SESSION_CACHE_TTL_SECONDS
            assert GeneratorSessionService._session_ttl_seconds() == 2.0

    def test_clone(self):
        from app.services.generator_session_service import GeneratorSessionService
        original = {"a": [1, 2, {"b": 3}]}
        cloned = GeneratorSessionService._clone(original)
        assert cloned == original
        cloned["a"][2]["b"] = 99
        assert original["a"][2]["b"] == 3


class TestCacheHelpers:
    @pytest.mark.asyncio
    async def test_get_cached_found(self, svc):
        svc._session_cache["k1"] = (time.monotonic() + 60, {"id": "s1"})
        result = await svc._get_cached(svc._session_cache, "k1", 30)
        assert result == {"id": "s1"}

    @pytest.mark.asyncio
    async def test_get_cached_expired(self, svc):
        from app.services.generator_session_service import _CACHE_MISS
        svc._session_cache["k1"] = (time.monotonic() - 10, {"id": "s1"})
        result = await svc._get_cached(svc._session_cache, "k1", 30)
        assert result is _CACHE_MISS
        assert "k1" not in svc._session_cache

    @pytest.mark.asyncio
    async def test_get_cached_ttl_zero(self, svc):
        from app.services.generator_session_service import _CACHE_MISS
        svc._session_cache["k1"] = (time.monotonic() + 60, {"id": "s1"})
        result = await svc._get_cached(svc._session_cache, "k1", 0)
        assert result is _CACHE_MISS

    @pytest.mark.asyncio
    async def test_get_cached_missing(self, svc):
        from app.services.generator_session_service import _CACHE_MISS
        result = await svc._get_cached(svc._session_cache, "nonexistent", 30)
        assert result is _CACHE_MISS

    @pytest.mark.asyncio
    async def test_set_cached_stores_clone(self, svc):
        original = {"id": "s1"}
        await svc._set_cached(svc._session_cache, "k1", original, 60)
        cached = svc._session_cache.get("k1")
        assert cached is not None
        assert cached[1] == original
        cached[1]["id"] = "modified"
        assert original["id"] == "s1"

    @pytest.mark.asyncio
    async def test_set_cached_ttl_zero_removes(self, svc):
        svc._session_cache["k1"] = (123.0, "val")
        await svc._set_cached(svc._session_cache, "k1", "new", 0)
        assert "k1" not in svc._session_cache

    @pytest.mark.asyncio
    async def test_invalidate_session_caches(self, svc):
        svc._session_cache["sid1"] = (1.0, "v")
        svc._latest_document_cache["sid1"] = (1.0, "v")
        svc._messages_cache["sid1|50"] = (1.0, "v")
        svc._messages_cache["sid1|100"] = (1.0, "v")
        svc._messages_cache["other|50"] = (1.0, "v")
        await svc._invalidate_session_caches("sid1")
        assert "sid1" not in svc._session_cache
        assert "sid1" not in svc._latest_document_cache
        assert "sid1|50" not in svc._messages_cache
        assert "sid1|100" not in svc._messages_cache
        assert "other|50" in svc._messages_cache

    @pytest.mark.asyncio
    async def test_invalidate_session_lists(self, svc):
        svc._session_list_cache["k1"] = (1.0, "v")
        await svc._invalidate_session_lists()
        assert len(svc._session_list_cache) == 0

    @pytest.mark.asyncio
    async def test_reset_cache_for_tests(self, svc):
        svc._session_cache["a"] = (1.0, "v")
        svc._messages_cache["b"] = (1.0, "v")
        svc._session_list_cache["c"] = (1.0, "v")
        svc._latest_document_cache["d"] = (1.0, "v")
        await svc.reset_cache_for_tests()
        assert len(svc._session_cache) == 0
        assert len(svc._messages_cache) == 0
        assert len(svc._session_list_cache) == 0
        assert len(svc._latest_document_cache) == 0


class TestCreateSession:
    @pytest.mark.asyncio
    async def test_creates_session(self, svc):
        mock_client = MagicMock()
        mock_client.table.return_value.insert.return_value.execute.return_value = MagicMock()
        with patch("app.services.generator_session_service.get_supabase_client", return_value=mock_client):
            sid = await svc.create_session("user-1", "multi_doc", {"key": "val"})
        assert isinstance(sid, str) and len(sid) > 20

    @pytest.mark.asyncio
    async def test_creates_session_with_none_user(self, svc):
        mock_client = MagicMock()
        mock_client.table.return_value.insert.return_value.execute.return_value = MagicMock()
        with patch("app.services.generator_session_service.get_supabase_client", return_value=mock_client):
            sid = await svc.create_session(None, "single_doc", {})
        assert sid is not None

    @pytest.mark.asyncio
    async def test_supabase_none_raises(self, svc):
        with patch("app.services.generator_session_service.get_supabase_client", return_value=None):
            with pytest.raises(Exception, match="Supabase client unavailable"):
                await svc.create_session("u", "t", {})

    @pytest.mark.asyncio
    async def test_insert_api_error(self, svc):
        from postgrest import APIError
        mock_client = MagicMock()
        mock_client.table.return_value.insert.return_value.execute.side_effect = APIError({"message": "insert failed", "code": "PGRST204"})
        with patch("app.services.generator_session_service.get_supabase_client", return_value=mock_client):
            with pytest.raises(Exception, match="Failed to create session"):
                await svc.create_session("u", "t", {})

    @pytest.mark.asyncio
    async def test_insert_generic_error(self, svc):
        mock_client = MagicMock()
        mock_client.table.return_value.insert.return_value.execute.side_effect = RuntimeError("db down")
        with patch("app.services.generator_session_service.get_supabase_client", return_value=mock_client):
            with pytest.raises(Exception, match="Failed to create session"):
                await svc.create_session("u", "t", {})


class TestGetSession:
    @pytest.mark.asyncio
    async def test_returns_session(self, svc):
        mock_client = MagicMock()
        mock_q = MagicMock()
        mock_q.maybe_single.return_value.execute.return_value = MagicMock(data={"id": "sid1"})
        mock_client.table.return_value.select.return_value.eq.return_value = mock_q
        with patch("app.services.generator_session_service.get_supabase_client", return_value=mock_client):
            result = await svc.get_session("sid1")
        assert result == {"id": "sid1"}

    @pytest.mark.asyncio
    async def test_returns_none_when_missing(self, svc):
        mock_client = MagicMock()
        mock_q = MagicMock()
        mock_q.maybe_single.return_value.execute.return_value = MagicMock(data=None)
        mock_client.table.return_value.select.return_value.eq.return_value = mock_q
        with patch("app.services.generator_session_service.get_supabase_client", return_value=mock_client):
            result = await svc.get_session("sid1")
        assert result is None

    @pytest.mark.asyncio
    async def test_uses_cache(self, svc):
        svc._session_cache["sid1"] = (time.monotonic() + 60, {"id": "cached-sid1"})
        mock_client = MagicMock()
        with patch("app.services.generator_session_service.get_supabase_client", return_value=mock_client):
            result = await svc.get_session("sid1")
        assert result == {"id": "cached-sid1"}
        mock_client.table.assert_not_called()

    @pytest.mark.asyncio
    async def test_caches_after_fetch(self, svc):
        mock_client = MagicMock()
        mock_q = MagicMock()
        mock_q.maybe_single.return_value.execute.return_value = MagicMock(data={"id": "sid2"})
        mock_client.table.return_value.select.return_value.eq.return_value = mock_q
        with patch("app.services.generator_session_service.get_supabase_client", return_value=mock_client):
            result = await svc.get_session("sid2")
        assert result == {"id": "sid2"}
        assert "sid2" in svc._session_cache

    @pytest.mark.asyncio
    async def test_supabase_none_raises(self, svc):
        with patch("app.services.generator_session_service.get_supabase_client", return_value=None):
            with pytest.raises(Exception, match="Supabase client unavailable"):
                await svc.get_session("sid1")


class TestUpdateSession:
    @pytest.mark.asyncio
    async def test_updates_session(self, svc):
        mock_client = MagicMock()
        mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()
        svc._session_cache["sid1"] = (time.monotonic() + 60, {"id": "sid1"})
        with patch("app.services.generator_session_service.get_supabase_client", return_value=mock_client):
            await svc.update_session("sid1", status="completed", progress=100)
        assert "sid1" not in svc._session_cache
        assert "sid1" not in svc._latest_document_cache

    @pytest.mark.asyncio
    async def test_invalidates_lists(self, svc):
        mock_client = MagicMock()
        mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()
        svc._session_list_cache["user-1|50"] = (time.monotonic() + 60, [])
        with patch("app.services.generator_session_service.get_supabase_client", return_value=mock_client):
            await svc.update_session("sid1")
        assert len(svc._session_list_cache) == 0

    @pytest.mark.asyncio
    async def test_supabase_none_raises(self, svc):
        with patch("app.services.generator_session_service.get_supabase_client", return_value=None):
            with pytest.raises(Exception, match="Supabase client unavailable"):
                await svc.update_session("sid1")


class TestAddMessage:
    @pytest.mark.asyncio
    async def test_adds_message(self, svc):
        mock_client = MagicMock()
        mock_client.table.return_value.insert.return_value.execute.return_value = MagicMock()
        with patch("app.services.generator_session_service.get_supabase_client", return_value=mock_client):
            await svc.add_message("sid1", "user", "Hello")
        assert True

    @pytest.mark.asyncio
    async def test_invalidates_session_caches(self, svc):
        mock_client = MagicMock()
        mock_client.table.return_value.insert.return_value.execute.return_value = MagicMock()
        svc._session_cache["sid1"] = (time.monotonic() + 60, {})
        svc._messages_cache["sid1|50"] = (time.monotonic() + 60, [])
        with patch("app.services.generator_session_service.get_supabase_client", return_value=mock_client):
            await svc.add_message("sid1", "assistant", "Response")
        assert "sid1" not in svc._session_cache
        assert "sid1|50" not in svc._messages_cache

    @pytest.mark.asyncio
    async def test_token_count_zero_by_default(self, svc):
        mock_client = MagicMock()
        insert_mock = mock_client.table.return_value.insert
        with patch("app.services.generator_session_service.get_supabase_client", return_value=mock_client):
            await svc.add_message("sid1", "user", "Hi", token_count=0)
        insert_mock.assert_called_once()
        payload = insert_mock.call_args[0][0]
        assert payload["token_count"] == 0

    @pytest.mark.asyncio
    async def test_supabase_none_raises(self, svc):
        with patch("app.services.generator_session_service.get_supabase_client", return_value=None):
            with pytest.raises(Exception, match="Supabase client unavailable"):
                await svc.add_message("sid1", "user", "x")


class TestGetMessages:
    @pytest.mark.asyncio
    async def test_returns_messages(self, svc):
        mock_client = MagicMock()
        mock_exec = MagicMock()
        mock_exec.data = [{"role": "user", "content": "Hi"}]
        mock_client.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = mock_exec
        with patch("app.services.generator_session_service.get_supabase_client", return_value=mock_client):
            result = await svc.get_messages("sid1")
        assert result == [{"role": "user", "content": "Hi"}]

    @pytest.mark.asyncio
    async def test_empty_data_returns_empty_list(self, svc):
        mock_client = MagicMock()
        mock_exec = MagicMock()
        mock_exec.data = None
        mock_client.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = mock_exec
        with patch("app.services.generator_session_service.get_supabase_client", return_value=mock_client):
            result = await svc.get_messages("sid1")
        assert result == []

    @pytest.mark.asyncio
    async def test_uses_cache(self, svc):
        svc._messages_cache["sid1|50"] = (time.monotonic() + 60, [{"role": "assistant"}])
        mock_client = MagicMock()
        with patch("app.services.generator_session_service.get_supabase_client", return_value=mock_client):
            result = await svc.get_messages("sid1")
        assert result == [{"role": "assistant"}]
        mock_client.table.assert_not_called()

    @pytest.mark.asyncio
    async def test_caches_after_fetch(self, svc):
        mock_client = MagicMock()
        mock_exec = MagicMock()
        mock_exec.data = [{"role": "user"}]
        mock_client.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = mock_exec
        with patch("app.services.generator_session_service.get_supabase_client", return_value=mock_client):
            await svc.get_messages("sid1", limit=25)
        assert "sid1|25" in svc._messages_cache

    @pytest.mark.asyncio
    async def test_supabase_none_raises(self, svc):
        with patch("app.services.generator_session_service.get_supabase_client", return_value=None):
            with pytest.raises(Exception, match="Supabase client unavailable"):
                await svc.get_messages("sid1")


class TestListSessions:
    @pytest.mark.asyncio
    async def test_list_sessions(self, svc):
        mock_client = MagicMock()
        mock_exec = MagicMock()
        mock_exec.data = [{"id": "s1"}]
        mock_eq = MagicMock()
        mock_eq.order.return_value.limit.return_value.execute.return_value = mock_exec
        mock_client.table.return_value.select.return_value.eq.return_value = mock_eq
        with patch("app.services.generator_session_service.get_supabase_client", return_value=mock_client):
            result = await svc.list_sessions("user-1")
        assert result == [{"id": "s1"}]

    @pytest.mark.asyncio
    async def test_list_all_when_user_none(self, svc):
        mock_client = MagicMock()
        mock_exec = MagicMock()
        mock_exec.data = [{"id": "s1"}, {"id": "s2"}]
        mock_client.table.return_value.select.return_value.order.return_value.limit.return_value.execute.return_value = mock_exec
        with patch("app.services.generator_session_service.get_supabase_client", return_value=mock_client):
            result = await svc.list_sessions(None)
        assert result == [{"id": "s1"}, {"id": "s2"}]

    @pytest.mark.asyncio
    async def test_uses_cache(self, svc):
        svc._session_list_cache["user-1|50"] = (time.monotonic() + 60, [{"id": "cached"}])
        mock_client = MagicMock()
        with patch("app.services.generator_session_service.get_supabase_client", return_value=mock_client):
            result = await svc.list_sessions("user-1")
        assert result == [{"id": "cached"}]
        mock_client.table.assert_not_called()

    @pytest.mark.asyncio
    async def test_supabase_none_raises(self, svc):
        with patch("app.services.generator_session_service.get_supabase_client", return_value=None):
            with pytest.raises(Exception, match="Supabase client unavailable"):
                await svc.list_sessions("user-1")


class TestSaveDocumentVersion:
    @pytest.mark.asyncio
    async def test_saves_first_version(self, svc):
        mock_client = MagicMock()
        latest_exec = MagicMock()
        latest_exec.data = []
        insert_exec = MagicMock()
        mock_q = MagicMock()
        mock_q.order.return_value.limit.return_value.execute.return_value = latest_exec
        mock_client.table.return_value.select.return_value.eq.return_value = mock_q
        mock_client.table.return_value.insert.return_value.execute.return_value = insert_exec
        with patch("app.services.generator_session_service.get_supabase_client", return_value=mock_client):
            vnum = await svc.save_document_version("sid1", {"title": "Doc"}, "/path/docx")
        assert vnum == 1

    @pytest.mark.asyncio
    async def test_increments_version(self, svc):
        mock_client = MagicMock()
        latest_exec = MagicMock()
        latest_exec.data = [MagicMock(get=lambda k, d=None: 3)]
        insert_exec = MagicMock()
        mock_q = MagicMock()
        mock_q.order.return_value.limit.return_value.execute.return_value = latest_exec
        mock_client.table.return_value.select.return_value.eq.return_value = mock_q
        mock_client.table.return_value.insert.return_value.execute.return_value = insert_exec
        with patch("app.services.generator_session_service.get_supabase_client", return_value=mock_client):
            vnum = await svc.save_document_version("sid1", {"title": "Doc"}, "/path/docx")
        assert vnum == 4

    @pytest.mark.asyncio
    async def test_uses_provided_version(self, svc):
        mock_client = MagicMock()
        mock_client.table.return_value.insert.return_value.execute.return_value = MagicMock()
        with patch("app.services.generator_session_service.get_supabase_client", return_value=mock_client):
            vnum = await svc.save_document_version("sid1", {}, "", version=5)
        assert vnum == 5

    @pytest.mark.asyncio
    async def test_invalidates_caches(self, svc):
        mock_client = MagicMock()
        latest_exec = MagicMock()
        latest_exec.data = []
        insert_exec = MagicMock()
        mock_q = MagicMock()
        mock_q.order.return_value.limit.return_value.execute.return_value = latest_exec
        mock_client.table.return_value.select.return_value.eq.return_value = mock_q
        mock_client.table.return_value.insert.return_value.execute.return_value = insert_exec
        svc._session_cache["sid1"] = (time.monotonic() + 60, {})
        with patch("app.services.generator_session_service.get_supabase_client", return_value=mock_client):
            await svc.save_document_version("sid1", {}, "")
        assert "sid1" not in svc._session_cache

    @pytest.mark.asyncio
    async def test_supabase_none_raises(self, svc):
        with patch("app.services.generator_session_service.get_supabase_client", return_value=None):
            with pytest.raises(Exception, match="Supabase client unavailable"):
                await svc.save_document_version("sid1", {}, "")

    @pytest.mark.asyncio
    async def test_version_lookup_api_error(self, svc):
        from postgrest import APIError
        mock_client = MagicMock()
        mock_q = MagicMock()
        mock_q.order.return_value.limit.return_value.execute.side_effect = APIError({"message": "lookup failed", "code": "PGRST204"})
        mock_client.table.return_value.select.return_value.eq.return_value = mock_q
        with patch("app.services.generator_session_service.get_supabase_client", return_value=mock_client):
            with pytest.raises(Exception, match="Failed to get latest version"):
                await svc.save_document_version("sid1", {}, "")


class TestGetLatestDocument:
    @pytest.mark.asyncio
    async def test_returns_document(self, svc):
        mock_client = MagicMock()
        mock_q = MagicMock()
        mock_q.order.return_value.limit.return_value.maybe_single.return_value.execute.return_value = MagicMock(
            data={"id": "d1", "version_number": 3}
        )
        mock_client.table.return_value.select.return_value.eq.return_value = mock_q
        with patch("app.services.generator_session_service.get_supabase_client", return_value=mock_client):
            result = await svc.get_latest_document("sid1")
        assert result == {"id": "d1", "version_number": 3}

    @pytest.mark.asyncio
    async def test_returns_none_when_missing(self, svc):
        mock_client = MagicMock()
        mock_q = MagicMock()
        mock_q.order.return_value.limit.return_value.maybe_single.return_value.execute.return_value = MagicMock(
            data=None
        )
        mock_client.table.return_value.select.return_value.eq.return_value = mock_q
        with patch("app.services.generator_session_service.get_supabase_client", return_value=mock_client):
            result = await svc.get_latest_document("sid1")
        assert result is None

    @pytest.mark.asyncio
    async def test_uses_cache(self, svc):
        svc._latest_document_cache["sid1"] = (time.monotonic() + 60, {"cached": True})
        mock_client = MagicMock()
        with patch("app.services.generator_session_service.get_supabase_client", return_value=mock_client):
            result = await svc.get_latest_document("sid1")
        assert result == {"cached": True}
        mock_client.table.assert_not_called()

    @pytest.mark.asyncio
    async def test_caches_after_fetch(self, svc):
        mock_client = MagicMock()
        mock_q = MagicMock()
        mock_q.order.return_value.limit.return_value.maybe_single.return_value.execute.return_value = MagicMock(
            data={"version": 2}
        )
        mock_client.table.return_value.select.return_value.eq.return_value = mock_q
        with patch("app.services.generator_session_service.get_supabase_client", return_value=mock_client):
            await svc.get_latest_document("sid1")
        assert "sid1" in svc._latest_document_cache

    @pytest.mark.asyncio
    async def test_supabase_none_raises(self, svc):
        with patch("app.services.generator_session_service.get_supabase_client", return_value=None):
            with pytest.raises(Exception, match="Supabase client unavailable"):
                await svc.get_latest_document("sid1")


@pytest.fixture
def svc():
    from app.services.generator_session_service import GeneratorSessionService
    s = GeneratorSessionService()
    return s
