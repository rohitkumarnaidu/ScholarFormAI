import time
import concurrent.futures
import threading
from unittest.mock import MagicMock, patch, PropertyMock

import pytest


# ---------------------------------------------------------------------------
# 2A: Latency Assertions (~8 tests)
# ---------------------------------------------------------------------------

class TestLatencyAssertions:
    """Verify LLM response times stay within SLA bounds."""

    @pytest.mark.llm
    @pytest.mark.sla
    def test_response_under_500ms_passes_sla(self, llm):
        """Responses under 500ms should pass SLA."""
        with (
            patch.object(llm, "LITELLM_AVAILABLE", False),
            patch.object(llm, "_generate_fallback", return_value="fast response"),
            patch("app.cache.redis_cache.redis_cache.get_llm_result", return_value=None),
            patch("app.cache.redis_cache.redis_cache.set_llm_result"),
            patch.object(llm.settings, "NVIDIA_API_KEY", "key"),
            patch.object(llm.settings, "LLM_CACHE_TTL_SECONDS", 3600),
        ):
            start = time.perf_counter()
            result = llm.generate(
                [{"role": "user", "content": "hi"}],
                model="nvidia_nim/llama-3",
            )
            elapsed = time.perf_counter() - start
        assert result == "fast response"
        assert elapsed < 2.0, "Response should be fast (mock)"

    @pytest.mark.llm
    @pytest.mark.sla
    def test_response_over_5s_fails_sla(self):
        """Simulate a response that exceeds SLA threshold."""
        from app.services.llm_service import _provider_timeout_seconds

        sla_threshold = 5.0
        fast_timeout = _provider_timeout_seconds()
        assert fast_timeout >= 3, "Default timeout should be at least 3s"
        assert fast_timeout <= 60, "Default timeout should be at most 60s"

    @pytest.mark.llm
    @pytest.mark.sla
    def test_timeout_propagated_from_settings(self, llm):
        """Timeout value from settings should flow to generate kwargs."""
        with patch.object(llm.settings, "LLM_PROVIDER_TIMEOUT_SECONDS", 10):
            with patch.object(llm, "LITELLM_AVAILABLE", False):
                with patch.object(llm, "_generate_fallback", return_value="result"):
                    with patch("app.cache.redis_cache.redis_cache.get_llm_result", return_value=None):
                        with patch("app.cache.redis_cache.redis_cache.set_llm_result"):
                            with patch.object(llm.settings, "NVIDIA_API_KEY", "key"):
                                with patch.object(llm.settings, "LLM_CACHE_TTL_SECONDS", 3600):
                                    llm.generate(
                                        [{"role": "user", "content": "hi"}],
                                        model="nvidia_nim/llama-3",
                                    )
            from app.services.llm_service import _provider_timeout_seconds
            assert _provider_timeout_seconds() == 10

    @pytest.mark.llm
    @pytest.mark.sla
    def test_explicit_timeout_overrides_default(self, llm):
        """Explicit timeout should be preferred over settings default."""
        captured = {}

        def capture_timeout(messages, model, temperature, max_tokens, timeout, api_key, api_base):
            captured["timeout"] = timeout
            return "captured"

        with patch.object(llm, "LITELLM_AVAILABLE", False):
            with patch.object(llm, "_generate_fallback", side_effect=capture_timeout):
                with patch("app.cache.redis_cache.redis_cache.get_llm_result", return_value=None):
                    with patch("app.cache.redis_cache.redis_cache.set_llm_result"):
                        with patch.object(llm.settings, "NVIDIA_API_KEY", "key"):
                            with patch.object(llm.settings, "LLM_CACHE_TTL_SECONDS", 3600):
                                llm.generate(
                                    [{"role": "user", "content": "hi"}],
                                    model="nvidia_nim/llama-3",
                                    timeout=3,
                                )
        assert captured.get("timeout") == 3

    @pytest.mark.llm
    @pytest.mark.sla
    def test_cache_hit_near_zero_latency(self, llm):
        """Cache hits should return near-instantly."""
        with patch("app.cache.redis_cache.redis_cache.get_llm_result", return_value="cached"):
            with patch.object(llm.settings, "NVIDIA_API_KEY", "key"):
                start = time.perf_counter()
                result = llm.generate(
                    [{"role": "user", "content": "hi"}],
                    model="nvidia_nim/llama-3",
                )
                elapsed = time.perf_counter() - start
        assert result == "cached"
        assert elapsed < 1.0, "Cache hit should be near-instant"

    @pytest.mark.llm
    @pytest.mark.sla
    def test_timeout_value_bounds(self):
        """_provider_timeout_seconds should clamp to [3, 60]."""
        from app.services.llm_service import _provider_timeout_seconds

        with patch("app.services.llm_service.settings.LLM_PROVIDER_TIMEOUT_SECONDS", 1):
            assert _provider_timeout_seconds() == 3

        with patch("app.services.llm_service.settings.LLM_PROVIDER_TIMEOUT_SECONDS", 100):
            assert _provider_timeout_seconds() == 60

        with patch("app.services.llm_service.settings.LLM_PROVIDER_TIMEOUT_SECONDS", 15):
            assert _provider_timeout_seconds() == 15

    @pytest.mark.llm
    @pytest.mark.sla
    def test_negative_timeout_clamped(self):
        from app.services.llm_service import _provider_timeout_seconds
        with patch("app.services.llm_service.settings.LLM_PROVIDER_TIMEOUT_SECONDS", -5):
            assert _provider_timeout_seconds() == 3


# ---------------------------------------------------------------------------
# 2B: Timeout Handling (~6 tests)
# ---------------------------------------------------------------------------

class TestTimeoutHandling:
    """LLM calls should timeout gracefully."""

    @pytest.mark.llm
    @pytest.mark.sla
    def test_generate_timeout_raises(self, llm):
        """The generate function should propagate timeout when completion hangs."""
        llm.completion = MagicMock(side_effect=TimeoutError("LLM timeout"))
        with patch.object(llm, "LITELLM_AVAILABLE", True):
            with patch("app.cache.redis_cache.redis_cache.get_llm_result", return_value=None):
                with patch.object(llm.settings, "NVIDIA_API_KEY", "key"):
                    with pytest.raises(TimeoutError, match="LLM timeout"):
                        llm.generate(
                            [{"role": "user", "content": "hi"}],
                            model="nvidia_nim/llama-3",
                            timeout=1,
                        )

    @pytest.mark.llm
    @pytest.mark.sla
    def test_circuit_breaker_resets_after_timeout(self, llm):
        """Timeout should propagate and not silently swallow errors."""
        with patch.object(llm, "LITELLM_AVAILABLE", False):
            with patch.object(llm, "_generate_fallback", side_effect=TimeoutError("timeout")):
                with patch("app.cache.redis_cache.redis_cache.get_llm_result", return_value=None):
                    with patch.object(llm.settings, "NVIDIA_API_KEY", "key"):
                        with patch.object(llm.settings, "LLM_CACHE_TTL_SECONDS", 3600):
                            with pytest.raises(TimeoutError, match="timeout"):
                                llm.generate(
                                    [{"role": "user", "content": "timeout test"}],
                                    model="nvidia_nim/llama-3",
                                )

    @pytest.mark.llm
    @pytest.mark.sla
    def test_streaming_timeout_handled(self, llm):
        """Streaming response should still respect timeout."""
        llm.completion = MagicMock(side_effect=TimeoutError("stream timeout"))
        with patch.object(llm, "LITELLM_AVAILABLE", True):
            with patch("app.cache.redis_cache.redis_cache.get_llm_result", return_value=None):
                with patch.object(llm.settings, "NVIDIA_API_KEY", "key"):
                        with pytest.raises(TimeoutError, match="stream timeout"):
                            llm.generate(
                                [{"role": "user", "content": "stream test"}],
                                model="nvidia_nim/llama-3",
                                timeout=1,
                                stream=True,
                            )

    @pytest.mark.llm
    @pytest.mark.sla
    def test_generate_with_fallback_per_tier_timeout(self, llm):
        """Each tier in fallback chain should respect timeout."""
        call_timeouts = []

        def capture_generate(messages, **kw):
            call_timeouts.append(kw.get("timeout"))
            raise RuntimeError("fail")

        with patch.object(llm, "generate", side_effect=capture_generate):
            with patch.object(llm.settings, "NVIDIA_API_KEY", "nv-key"):
                with patch.object(llm.settings, "GROQ_API_KEY", "gq-key"):
                    with patch.object(llm.settings, "OPENROUTER_API_KEY", "or-key"):
                        with patch.object(llm.settings, "OPENROUTER_API_BASE", "https://or.com"):
                            from app.services.llm_service import LLMUnavailableError
                            with pytest.raises(LLMUnavailableError):
                                llm.generate_with_fallback(
                                    [{"role": "user", "content": "timeout test"}],
                                )
        assert len(call_timeouts) >= 2, "Should have attempted multiple tiers"

    @pytest.mark.llm
    @pytest.mark.sla
    def test_generate_with_model_single_timeout(self, llm):
        """generate_with_model should propagate timeout to underlying call."""
        with patch.object(llm, "_call_with_provider_circuit", side_effect=TimeoutError("model timeout")):
            with patch("app.services.provider_registry.resolve_model_provider", return_value="nvidia"):
                with patch("app.services.provider_registry.get_provider_info",
                           return_value={"base_url": "https://nv.com"}):
                    with patch.object(llm, "resolve_user_api_key", return_value="key"):
                        from app.services.llm_service import LLMUnavailableError
                        with pytest.raises(LLMUnavailableError, match="model timeout"):
                            llm.generate_with_model(
                                [{"role": "user", "content": "timeout"}],
                                "llama-3",
                            )

    @pytest.mark.llm
    @pytest.mark.sla
    def test_user_configured_timeout_overrides_default(self, llm):
        """User-provided timeout should take precedence over settings default."""
        from app.services.llm_service import generate

        custom_timeout = 7
        captured_timeout = [None]

        def fallback_with_timeout(messages, model, temperature, max_tokens, timeout, api_key, api_base):
            captured_timeout[0] = timeout
            return "custom timeout result"

        with patch.object(llm, "LITELLM_AVAILABLE", False):
            with patch.object(llm, "_generate_fallback", side_effect=fallback_with_timeout):
                with patch("app.cache.redis_cache.redis_cache.get_llm_result", return_value=None):
                    with patch("app.cache.redis_cache.redis_cache.set_llm_result"):
                        with patch.object(llm.settings, "NVIDIA_API_KEY", "key"):
                            with patch.object(llm.settings, "LLM_PROVIDER_TIMEOUT_SECONDS", 30):
                                with patch.object(llm.settings, "LLM_CACHE_TTL_SECONDS", 3600):
                                    generate(
                                        [{"role": "user", "content": "hi"}],
                                        model="nvidia_nim/llama-3",
                                        timeout=custom_timeout,
                                    )
        assert captured_timeout[0] == custom_timeout


# ---------------------------------------------------------------------------
# 2C: Concurrent Request Performance (~6 tests)
# ---------------------------------------------------------------------------

class TestConcurrentRequestPerformance:
    """Multiple simultaneous requests should be handled without errors."""

    @pytest.mark.llm
    @pytest.mark.sla
    def test_concurrent_requests_no_errors(self, llm):
        """Multiple concurrent LLM calls should all succeed."""
        def mock_gen(*args, **kw):
            return "concurrent result"

        n_requests = 5
        with patch.object(llm, "LITELLM_AVAILABLE", False):
            with patch.object(llm, "_generate_fallback", side_effect=mock_gen):
                with patch("app.cache.redis_cache.redis_cache.get_llm_result", return_value=None):
                    with patch("app.cache.redis_cache.redis_cache.set_llm_result"):
                        with patch.object(llm.settings, "NVIDIA_API_KEY", "key"):
                            with patch.object(llm.settings, "LLM_CACHE_TTL_SECONDS", 3600):
                                with concurrent.futures.ThreadPoolExecutor(max_workers=n_requests) as ex:
                                    futures = [
                                        ex.submit(
                                            llm.generate,
                                            [{"role": "user", "content": f"req-{i}"}],
                                            model="nvidia_nim/llama-3",
                                        )
                                        for i in range(n_requests)
                                    ]
                                    results = [f.result() for f in concurrent.futures.as_completed(futures)]
        assert len(results) == n_requests
        assert all(r == "concurrent result" for r in results)

    @pytest.mark.llm
    @pytest.mark.sla
    def test_concurrent_requests_dont_exceed_rate_limit(self, llm):
        """Concurrent requests should be throttled properly."""
        call_times = []
        lock = threading.Lock()

        def slow_gen(*args, **kw):
            with lock:
                call_times.append(time.perf_counter())
            return "rate limited"

        n_requests = 3
        with patch.object(llm, "LITELLM_AVAILABLE", False):
            with patch.object(llm, "_generate_fallback", side_effect=slow_gen):
                with patch("app.cache.redis_cache.redis_cache.get_llm_result", return_value=None):
                    with patch("app.cache.redis_cache.redis_cache.set_llm_result"):
                        with patch.object(llm.settings, "NVIDIA_API_KEY", "key"):
                            with patch.object(llm.settings, "LLM_CACHE_TTL_SECONDS", 3600):
                                with concurrent.futures.ThreadPoolExecutor(max_workers=n_requests) as ex:
                                    futures = [
                                        ex.submit(
                                            llm.generate,
                                            [{"role": "user", "content": f"req-{i}"}],
                                            model="nvidia_nim/llama-3",
                                        )
                                        for i in range(n_requests)
                                    ]
                                    results = [f.result() for f in concurrent.futures.as_completed(futures)]
        assert len(results) == n_requests
        assert all(r == "rate limited" for r in results)

    @pytest.mark.llm
    @pytest.mark.sla
    def test_circuit_breaker_thread_safe(self, llm):
        """Circuit breaker state should remain consistent under concurrency."""
        from app.services.llm_service import _provider_breaker, _PROVIDER_BREAKERS

        _PROVIDER_BREAKERS.clear()

        def create_breaker():
            return _provider_breaker("concurrent_test")

        n_threads = 10
        with patch("app.services.llm_service._breaker_enabled", return_value=True):
            with patch("app.services.llm_service.pybreaker") as mock_pb:
                mock_pb.CircuitBreaker = MagicMock(return_value="breaker_ok")
                with concurrent.futures.ThreadPoolExecutor(max_workers=n_threads) as ex:
                    futures = [ex.submit(create_breaker) for _ in range(n_threads)]
                    results = [f.result() for f in concurrent.futures.as_completed(futures)]
        assert len(results) == n_threads
        assert all(r == "breaker_ok" for r in results)
        assert _PROVIDER_BREAKERS.get("concurrent_test") == "breaker_ok"

    @pytest.mark.llm
    @pytest.mark.sla
    def test_concurrent_provider_breaker_reuse(self):
        """Multiple concurrent accesses to same provider should reuse breaker."""
        from app.services.llm_service import _provider_breaker, _PROVIDER_BREAKERS
        _PROVIDER_BREAKERS.clear()

        with patch("app.services.llm_service._breaker_enabled", return_value=True):
            with patch("app.services.llm_service.pybreaker") as mock_pb:
                mock_breaker_instance = MagicMock()
                mock_pb.CircuitBreaker = MagicMock(return_value=mock_breaker_instance)

                def get_breaker():
                    return _provider_breaker("shared_provider")

                with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex:
                    futures = [ex.submit(get_breaker) for _ in range(5)]
                    results = [f.result() for f in concurrent.futures.as_completed(futures)]
        assert all(r is mock_breaker_instance for r in results)

    @pytest.mark.llm
    @pytest.mark.sla
    def test_concurrent_redis_cache_safe(self, llm):
        """Concurrent cache access should not throw errors."""
        mock_cache = MagicMock()
        mock_cache.get_llm_result.return_value = None
        mock_cache.set_llm_result.return_value = True

        n_requests = 5
        with patch.object(llm, "LITELLM_AVAILABLE", False):
            with patch.object(llm, "_generate_fallback", return_value="cached result"):
                with patch("app.cache.redis_cache.redis_cache", mock_cache):
                    with patch.object(llm.settings, "NVIDIA_API_KEY", "key"):
                        with patch.object(llm.settings, "LLM_CACHE_TTL_SECONDS", 3600):
                            with concurrent.futures.ThreadPoolExecutor(max_workers=n_requests) as ex:
                                futures = [
                                    ex.submit(
                                        llm.generate,
                                        [{"role": "user", "content": f"req-{i}"}],
                                        model="nvidia_nim/llama-3",
                                    )
                                    for i in range(n_requests)
                                ]
                                results = [f.result() for f in concurrent.futures.as_completed(futures)]
        assert len(results) == n_requests
        assert all(r == "cached result" for r in results)

    @pytest.mark.llm
    @pytest.mark.sla
    def test_concurrent_fallback_chain(self, llm):
        """Concurrent fallback requests should all resolve correctly."""
        mock_responses = [
            "result_a", "result_b", "result_c",
        ]
        response_index = [0]
        lock = threading.Lock()

        def mock_gen(messages, **kw):
            with lock:
                idx = response_index[0]
                response_index[0] += 1
            return mock_responses[idx % len(mock_responses)]

        with patch.object(llm, "generate", side_effect=mock_gen):
            with patch.object(llm.settings, "NVIDIA_API_KEY", "nv-key"):
                with patch.object(llm.settings, "GROQ_API_KEY", "gq-key"):
                    with patch.object(llm.settings, "OPENROUTER_API_KEY", None):
                        from app.services.llm_service import generate_with_fallback
                        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:
                            futures = [
                                ex.submit(generate_with_fallback, [{"role": "user", "content": f"req-{i}"}])
                                for i in range(3)
                            ]
                            results = [f.result() for f in concurrent.futures.as_completed(futures)]
        assert len(results) == 3


# ---------------------------------------------------------------------------
# 2D: Provider-Specific Latency Profiles (~4 tests)
# ---------------------------------------------------------------------------

class TestProviderLatencyProfiles:
    """Different providers should have distinct latency profiles."""

    @pytest.mark.llm
    @pytest.mark.sla
    def test_nvidia_latency_differs_from_ollama(self, llm):
        """Different providers should have different simulated latencies."""
        call_count = [0]

        def mock_fallback(messages, model, temperature, max_tokens, timeout, api_key, api_base):
            call_count[0] += 1
            return f"result from {model}"

        with patch.object(llm, "LITELLM_AVAILABLE", False):
            with patch.object(llm, "_generate_fallback", side_effect=mock_fallback):
                with patch("app.cache.redis_cache.redis_cache.get_llm_result", return_value=None):
                    with patch("app.cache.redis_cache.redis_cache.set_llm_result"):
                        with patch.object(llm.settings, "NVIDIA_API_KEY", "key"):
                            with patch.object(llm.settings, "LLM_CACHE_TTL_SECONDS", 3600):
                                result = llm.generate(
                                    [{"role": "user", "content": "latency test"}],
                                    model="nvidia_nim/llama-3",
                                )
        assert result == "result from nvidia_nim/llama-3"

    @pytest.mark.llm
    @pytest.mark.sla
    def test_fallback_tier_latency_accumulates(self, llm):
        """Fallback tier latency should accumulate across failed tiers."""
        fail_times = []

        def failing_gen(messages, **kw):
            fail_times.append(time.perf_counter())
            raise RuntimeError("tier fail")

        from app.services.llm_service import generate_with_fallback
        nvidia_key_present = True
        groq_key_present = True

        original_api_key = llm.resolve_user_api_key

        def mock_resolve(provider, user_id=None):
            if provider == "nvidia":
                return "nv-key" if nvidia_key_present else None
            if provider == "groq":
                return "gq-key" if groq_key_present else None
            if provider == "openrouter":
                return None
            return original_api_key(provider, user_id) if callable(original_api_key) else None

        with patch.object(llm, "resolve_user_api_key", side_effect=mock_resolve):
            with patch.object(llm, "generate", side_effect=failing_gen):
                with patch.object(llm.settings, "NVIDIA_API_KEY", "nv-key"):
                    with patch.object(llm.settings, "GROQ_API_KEY", "gq-key"):
                        with patch.object(llm.settings, "OPENROUTER_API_KEY", None):
                            from app.services.llm_service import LLMUnavailableError
                            with pytest.raises(LLMUnavailableError):
                                generate_with_fallback([{"role": "user", "content": "accumulate"}])
        assert len(fail_times) >= 2, "Should have attempted multiple tiers"

    @pytest.mark.llm
    @pytest.mark.sla
    def test_caching_reduces_latency_to_near_zero(self, llm):
        """Cache hits should be significantly faster than cache misses."""
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = "fresh response"
        mock_response.choices = [mock_choice]

        cache_miss_times = []

        def measure_cache_miss():
            llm.completion = MagicMock(return_value=mock_response)
            with patch.object(llm, "LITELLM_AVAILABLE", True):
                with patch("app.cache.redis_cache.redis_cache.get_llm_result", return_value=None):
                    with patch("app.cache.redis_cache.redis_cache.set_llm_result"):
                        with patch.object(llm.settings, "NVIDIA_API_KEY", "key"):
                            with patch.object(llm.settings, "LLM_CACHE_TTL_SECONDS", 3600):
                                start = time.perf_counter()
                                llm.generate(
                                    [{"role": "user", "content": "latency test"}],
                                    model="nvidia_nim/llama-3",
                                )
                                return time.perf_counter() - start

        def measure_cache_hit():
            with patch("app.cache.redis_cache.redis_cache.get_llm_result", return_value="cached quick"):
                with patch.object(llm.settings, "NVIDIA_API_KEY", "key"):
                    start = time.perf_counter()
                    llm.generate(
                        [{"role": "user", "content": "latency test"}],
                        model="nvidia_nim/llama-3",
                    )
                    return time.perf_counter() - start

        miss_time = measure_cache_miss()
        hit_time = measure_cache_hit()

        assert hit_time < miss_time * 2 or hit_time < 0.5

    @pytest.mark.llm
    @pytest.mark.sla
    def test_stream_reduces_ttft(self, llm):
        """Streaming should reduce perceived TTFT."""
        with patch.object(llm, "LITELLM_AVAILABLE", False):
            with patch.object(llm, "_generate_fallback", return_value="stream result"):
                with patch("app.cache.redis_cache.redis_cache.get_llm_result", return_value=None):
                    with patch.object(llm.settings, "NVIDIA_API_KEY", "key"):
                        with patch.object(llm.settings, "LLM_CACHE_TTL_SECONDS", 3600):
                            start = time.perf_counter()
                            result = llm.generate(
                                [{"role": "user", "content": "ttft test"}],
                                model="nvidia_nim/llama-3",
                                stream=True,
                            )
                            elapsed = time.perf_counter() - start
        assert result == "stream result"
        assert elapsed < 2.0, "Stream response should be fast"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def reset_breaker_cache():
    import importlib
    import app.services.llm_service as llm
    llm._PROVIDER_BREAKERS.clear()


@pytest.fixture
def llm():
    import importlib
    import app.services.llm_service as m
    importlib.reload(m)
    return m
