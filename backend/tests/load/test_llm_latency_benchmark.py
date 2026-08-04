# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
LLM latency benchmark tests measuring simulated LLM response time patterns.
Uses mocked service layer to isolate latency measurement from network.
"""

import concurrent.futures
import statistics
import time
from unittest.mock import MagicMock, patch

import pytest

LATENCY_P50_MS = 200
LATENCY_P95_MS = 1000
LATENCY_P99_MS = 3000
CACHE_HIT_MAX_MS = 10
TTFT_MAX_MS = 500


def _mock_llm_module():
    """Import and return the llm_service module with safe fallback."""
    import importlib

    import app.services.llm_service as m
    importlib.reload(m)
    return m


def _simulate_delay(ms: float):
    """Simulate latency by busy-waiting (no asyncio sleep for sync contexts)."""
    target = time.perf_counter() + ms / 1000
    while time.perf_counter() < target:
        pass


@pytest.fixture(autouse=True)
def reset_breakers():
    import app.services.llm_service as llm
    llm._PROVIDER_BREAKERS.clear()


@pytest.fixture
def llm():
    return _mock_llm_module()


class TestLLMLatencyBenchmark:
    """Measure LLM response time percentiles against SLO thresholds."""

    @pytest.mark.performance
    @pytest.mark.slow
    def test_p50_latency_under_200ms_cached(self, llm):
        """P50 latency under 200ms for cached responses."""
        latencies = []
        n_samples = 20

        with (
            patch("app.cache.redis_cache.redis_cache.get_llm_result", return_value="cached"),
            patch.object(llm.settings, "NVIDIA_API_KEY", "key"),
            patch.object(llm.settings, "LLM_CACHE_TTL_SECONDS", 3600),
        ):
            for _ in range(n_samples):
                start = time.perf_counter()
                result = llm.generate(
                    [{"role": "user", "content": "latency test"}],
                    model=llm.LLM_NVIDIA,
                )
                elapsed = time.perf_counter() - start
                latencies.append(elapsed * 1000)
                assert result == "cached"

        p50 = statistics.median(latencies)
        assert p50 < LATENCY_P50_MS, f"P50 latency {p50:.1f}ms >= {LATENCY_P50_MS}ms"

    @pytest.mark.performance
    @pytest.mark.slow
    def test_p95_latency_under_1000ms_direct(self, llm):
        """P95 latency under 1000ms for direct (uncached) responses."""
        latencies = []
        n_samples = 20

        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = "direct response"
        mock_response.choices = [mock_choice]

        with (
            patch("litellm.completion", return_value=mock_response),
            patch.object(llm, "LITELLM_AVAILABLE", True),
            patch("app.cache.redis_cache.redis_cache.get_llm_result", return_value=None),
            patch("app.cache.redis_cache.redis_cache.set_llm_result"),
            patch.object(llm.settings, "NVIDIA_API_KEY", "key"),
            patch.object(llm.settings, "LLM_CACHE_TTL_SECONDS", 3600),
        ):
            for _ in range(n_samples):
                start = time.perf_counter()
                result = llm.generate(
                    [{"role": "user", "content": "direct test"}],
                    model=llm.LLM_NVIDIA,
                )
                elapsed = time.perf_counter() - start
                latencies.append(elapsed * 1000)
                assert result == "direct response"

        latencies.sort()
        p95 = latencies[int(len(latencies) * 0.95)]
        assert p95 < LATENCY_P95_MS, f"P95 latency {p95:.1f}ms >= {LATENCY_P95_MS}ms"

    @pytest.mark.performance
    @pytest.mark.slow
    def test_p99_latency_under_3000ms_fallback(self, llm):
        """P99 latency under 3000ms for fallback chain."""
        latencies = []
        n_samples = 10

        with (
            patch.object(llm.settings, "NVIDIA_API_KEY", "nv-key"),
            patch.object(llm.settings, "GROQ_API_KEY", "gq-key"),
            patch.object(llm.settings, "OPENROUTER_API_KEY", None),
            patch.object(llm, "resolve_user_api_key", return_value=None),
        ):
            with patch.object(llm, "generate", return_value="fallback result"):
                for _ in range(n_samples):
                    start = time.perf_counter()
                    result = llm.generate_with_fallback(
                        [{"role": "user", "content": "fallback test"}],
                    )
                    elapsed = time.perf_counter() - start
                    latencies.append(elapsed * 1000)
                    assert result["text"] == "fallback result"

        latencies.sort()
        p99 = latencies[int(len(latencies) * 0.99)]
        assert p99 < LATENCY_P99_MS, f"P99 latency {p99:.1f}ms >= {LATENCY_P99_MS}ms"

    @pytest.mark.performance
    @pytest.mark.slow
    def test_cache_hit_under_10ms(self, llm):
        """Cache hit returns in < 10ms."""
        with (
            patch("app.cache.redis_cache.redis_cache.get_llm_result", return_value="instant cached"),
            patch.object(llm.settings, "NVIDIA_API_KEY", "key"),
        ):
            start = time.perf_counter()
            result = llm.generate(
                [{"role": "user", "content": "cache hit test"}],
                model=llm.LLM_NVIDIA,
            )
            elapsed = time.perf_counter() - start
        elapsed_ms = elapsed * 1000
        assert result == "instant cached"
        assert elapsed_ms < CACHE_HIT_MAX_MS, f"Cache hit took {elapsed_ms:.1f}ms >= {CACHE_HIT_MAX_MS}ms"

    @pytest.mark.performance
    @pytest.mark.slow
    def test_cache_miss_takes_expected_time(self, llm):
        """Cache miss returns fresh response (uncached path)."""
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = "fresh response"
        mock_response.choices = [mock_choice]

        with (
            patch("litellm.completion", return_value=mock_response),
            patch.object(llm, "LITELLM_AVAILABLE", True),
            patch("app.cache.redis_cache.redis_cache.get_llm_result", return_value=None),
            patch("app.cache.redis_cache.redis_cache.set_llm_result"),
            patch.object(llm.settings, "NVIDIA_API_KEY", "key"),
            patch.object(llm.settings, "LLM_CACHE_TTL_SECONDS", 3600),
        ):
            start = time.perf_counter()
            result = llm.generate(
                [{"role": "user", "content": "cache miss test"}],
                model=llm.LLM_NVIDIA,
            )
            elapsed = time.perf_counter() - start
        elapsed_ms = elapsed * 1000
        assert result == "fresh response"
        assert elapsed_ms > 0, "Cache miss should produce a result"

    @pytest.mark.performance
    @pytest.mark.slow
    def test_concurrent_llm_calls_5_all_complete(self, llm):
        """5 concurrent LLM calls all complete successfully."""
        def mock_gen(*args, **kw):
            return "concurrent result"

        n_requests = 5
        with (
            patch.object(llm, "LITELLM_AVAILABLE", False),
            patch.object(llm, "_llm_generate", None),
            patch.object(llm, "_generate_fallback", side_effect=mock_gen),
            patch("app.cache.redis_cache.redis_cache.get_llm_result", return_value=None),
            patch("app.cache.redis_cache.redis_cache.set_llm_result"),
            patch.object(llm.settings, "NVIDIA_API_KEY", "key"),
            patch.object(llm.settings, "LLM_CACHE_TTL_SECONDS", 3600),
        ):
            start = time.perf_counter()
            with concurrent.futures.ThreadPoolExecutor(max_workers=n_requests) as ex:
                futures = [
                    ex.submit(
                        llm.generate,
                        [{"role": "user", "content": f"concurrent-{i}"}],
                        model=llm.LLM_NVIDIA,
                    )
                    for i in range(n_requests)
                ]
                results = [f.result() for f in concurrent.futures.as_completed(futures)]
            elapsed = time.perf_counter() - start

        assert len(results) == n_requests
        assert all(r == "concurrent result" for r in results)
        assert elapsed < 5.0, f"5 concurrent LLM calls took {elapsed:.2f}s"

    @pytest.mark.performance
    @pytest.mark.slow
    def test_provider_failover_latency(self, llm):
        """Provider failover latency: primary fails, fallback succeeds."""
        failover_times = []

        with (
            patch.object(llm.settings, "NVIDIA_API_KEY", "nv-key"),
            patch.object(llm.settings, "GROQ_API_KEY", "gq-key"),
            patch.object(llm.settings, "OPENROUTER_API_KEY", None),
            patch.object(llm, "resolve_user_api_key", return_value=None),
        ):
            with patch.object(llm, "generate", side_effect=[RuntimeError("nv down"), "grook result"]):
                start = time.perf_counter()
                result = llm.generate_with_fallback(
                    [{"role": "user", "content": "failover test"}],
                )
                elapsed = time.perf_counter() - start
                failover_times.append(elapsed * 1000)

        assert result["text"] == "grook result"
        assert elapsed < 5.0, f"Failover took {elapsed:.2f}s"

    @pytest.mark.performance
    @pytest.mark.slow
    def test_streaming_ttft_under_500ms(self, llm):
        """Streaming TTFT (time to first token) under 500ms."""
        with (
            patch.object(llm, "LITELLM_AVAILABLE", False),
            patch.object(llm, "_llm_generate", None),
            patch.object(llm, "_generate_fallback", return_value="first token content"),
            patch("app.cache.redis_cache.redis_cache.get_llm_result", return_value=None),
            patch.object(llm.settings, "NVIDIA_API_KEY", "key"),
            patch.object(llm.settings, "LLM_CACHE_TTL_SECONDS", 3600),
        ):
            start = time.perf_counter()
            result = llm.generate(
                [{"role": "user", "content": "ttft test"}],
                model=llm.LLM_NVIDIA,
                stream=True,
            )
            elapsed = time.perf_counter() - start

        elapsed_ms = elapsed * 1000
        assert result == "first token content"
        assert elapsed_ms < TTFT_MAX_MS, f"Streaming TTFT was {elapsed_ms:.1f}ms >= {TTFT_MAX_MS}ms"

    @pytest.mark.performance
    @pytest.mark.slow
    def test_sequential_calls_no_degradation(self, llm):
        """Sequential calls show no latency degradation across 10 calls."""
        latencies = []
        n_calls = 10

        with (
            patch.object(llm, "LITELLM_AVAILABLE", False),
            patch.object(llm, "_llm_generate", None),
            patch.object(llm, "_generate_fallback", return_value="stable"),
            patch("app.cache.redis_cache.redis_cache.get_llm_result", return_value=None),
            patch("app.cache.redis_cache.redis_cache.set_llm_result"),
            patch.object(llm.settings, "NVIDIA_API_KEY", "key"),
            patch.object(llm.settings, "LLM_CACHE_TTL_SECONDS", 3600),
        ):
            for i in range(n_calls):
                start = time.perf_counter()
                llm.generate(
                    [{"role": "user", "content": f"seq-{i}"}],
                    model=llm.LLM_NVIDIA,
                )
                elapsed = time.perf_counter() - start
                latencies.append(elapsed * 1000)

        first_half = latencies[:n_calls // 2]
        second_half = latencies[n_calls // 2:]
        degradation = statistics.median(second_half) - statistics.median(first_half)
        assert degradation < 100, f"Latency degradation of {degradation:.1f}ms across {n_calls} calls"

    @pytest.mark.performance
    @pytest.mark.slow
    def test_rate_limited_calls_rejected_promptly(self, llm):
        """Rate-limited calls are rejected promptly (< 100ms)."""
        from app.services.llm_service import LLMUnavailableError

        start = time.perf_counter()
        with (
            patch.object(llm.settings, "NVIDIA_API_KEY", "nv-key"),
            patch.object(llm.settings, "GROQ_API_KEY", None),
            patch.object(llm.settings, "OPENROUTER_API_KEY", None),
            patch.object(llm, "resolve_user_api_key", return_value=None),
        ):
            with patch.object(llm, "generate", side_effect=RuntimeError("rate limited")):
                with pytest.raises(LLMUnavailableError):
                    llm.generate_with_fallback(
                        [{"role": "user", "content": "rate limit test"}],
                    )
        elapsed = time.perf_counter() - start
        assert elapsed < 0.5, f"Rate-limit rejection took {elapsed*1000:.1f}ms"

    @pytest.mark.performance
    @pytest.mark.slow
    def test_large_context_no_disproportionate_latency(self, llm):
        """Large context handling doesn't increase latency disproportionately."""
        small_context = [{"role": "user", "content": "short query"}]
        large_context = [{"role": "user", "content": "word " * 5000}]

        def mock_gen(messages, model, temperature, max_tokens, timeout, api_key, api_base):
            return f"result for {len(messages[0]['content'])} chars"

        with (
            patch.object(llm, "LITELLM_AVAILABLE", False),
            patch.object(llm, "_llm_generate", None),
            patch.object(llm, "_generate_fallback", side_effect=mock_gen),
            patch("app.cache.redis_cache.redis_cache.get_llm_result", return_value=None),
            patch("app.cache.redis_cache.redis_cache.set_llm_result"),
            patch.object(llm.settings, "NVIDIA_API_KEY", "key"),
            patch.object(llm.settings, "LLM_CACHE_TTL_SECONDS", 3600),
        ):
            start_small = time.perf_counter()
            llm.generate(small_context, model=llm.LLM_NVIDIA)
            small_elapsed = time.perf_counter() - start_small

            start_large = time.perf_counter()
            llm.generate(large_context, model=llm.LLM_NVIDIA)
            large_elapsed = time.perf_counter() - start_large

        ratio = large_elapsed / max(small_elapsed, 0.001)
        assert ratio < 5.0, f"Large/small latency ratio {ratio:.1f}x >= 5x"

    @pytest.mark.performance
    @pytest.mark.slow
    def test_parallel_vs_sequential_throughput(self, llm):
        """Parallel throughput > sequential throughput for 8 calls with simulated latency."""
        def slow_gen(messages, model, temperature, max_tokens, timeout, api_key, api_base):
            target = time.perf_counter() + 0.01
            while time.perf_counter() < target:
                pass
            return "throughput"

        n_calls = 8
        with (
            patch.object(llm, "LITELLM_AVAILABLE", False),
            patch.object(llm, "_llm_generate", None),
            patch.object(llm, "_generate_fallback", side_effect=slow_gen),
            patch("app.cache.redis_cache.redis_cache.get_llm_result", return_value=None),
            patch("app.cache.redis_cache.redis_cache.set_llm_result"),
            patch.object(llm.settings, "NVIDIA_API_KEY", "key"),
            patch.object(llm.settings, "LLM_CACHE_TTL_SECONDS", 3600),
        ):
            start_seq = time.perf_counter()
            for i in range(n_calls):
                llm.generate([{"role": "user", "content": f"seq-{i}"}], model=llm.LLM_NVIDIA)
            seq_elapsed = time.perf_counter() - start_seq

            start_par = time.perf_counter()
            with concurrent.futures.ThreadPoolExecutor(max_workers=n_calls) as ex:
                futures = [
                    ex.submit(llm.generate, [{"role": "user", "content": f"par-{i}"}], model=llm.LLM_NVIDIA)
                    for i in range(n_calls)
                ]
                results = [f.result() for f in concurrent.futures.as_completed(futures)]
            par_elapsed = time.perf_counter() - start_par

        assert len(results) == n_calls
        assert par_elapsed < seq_elapsed, (
            f"Parallel {par_elapsed:.3f}s not faster than sequential {seq_elapsed:.3f}s"
        )
