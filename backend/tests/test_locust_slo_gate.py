# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

import importlib.util
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace


def _load_locustfile_with_stubbed_locust():
    module_path = Path(__file__).resolve().parent / "load" / "locustfile.py"
    spec = importlib.util.spec_from_file_location("locustfile_under_test", module_path)
    assert spec is not None and spec.loader is not None

    fake_locust = ModuleType("locust")

    class _User:
        pass

    class _HttpUser(_User):
        pass

    def _task(fn=None, *args, **kwargs):
        if callable(fn):
            return fn

        def decorator(func):
            return func

        return decorator

    def _between(*args, **kwargs):
        return lambda: None

    class _Quitting:
        def add_listener(self, fn):
            return fn

    fake_locust.User = _User
    fake_locust.HttpUser = _HttpUser
    fake_locust.task = _task
    fake_locust.between = _between
    fake_locust.events = SimpleNamespace(quitting=_Quitting())

    previous = sys.modules.get("locust")
    sys.modules["locust"] = fake_locust
    try:
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    finally:
        if previous is None:
            sys.modules.pop("locust", None)
        else:
            sys.modules["locust"] = previous

    return module


locustfile = _load_locustfile_with_stubbed_locust()


def _environment(*, num_requests: int, p95_ms: float, fail_ratio: float, total_rps: float):
    total = SimpleNamespace(
        num_requests=num_requests,
        fail_ratio=fail_ratio,
        total_rps=total_rps,
        get_response_time_percentile=lambda _: p95_ms,
    )
    return SimpleNamespace(stats=SimpleNamespace(total=total), process_exit_code=None)


def test_locust_slo_gate_sets_nonzero_exit_on_violation(monkeypatch):
    monkeypatch.setattr(locustfile, "TARGET_P95_MS", 500.0)
    monkeypatch.setattr(locustfile, "TARGET_RPS", 100.0)
    monkeypatch.setattr(locustfile, "MAX_FAIL_RATIO", 0.0)
    env = _environment(num_requests=1000, p95_ms=650.0, fail_ratio=0.0, total_rps=110.0)

    locustfile.enforce_slo_thresholds(env)

    assert env.process_exit_code == 1


def test_locust_slo_gate_sets_zero_exit_when_targets_met(monkeypatch):
    monkeypatch.setattr(locustfile, "TARGET_P95_MS", 500.0)
    monkeypatch.setattr(locustfile, "TARGET_RPS", 100.0)
    monkeypatch.setattr(locustfile, "MAX_FAIL_RATIO", 0.0)
    env = _environment(num_requests=1000, p95_ms=300.0, fail_ratio=0.0, total_rps=120.0)

    locustfile.enforce_slo_thresholds(env)

    assert env.process_exit_code == 0
