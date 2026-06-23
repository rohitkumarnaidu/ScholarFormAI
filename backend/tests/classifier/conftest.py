# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""Override slow autouse fixtures from parent conftest for classifier tests."""

import pytest


@pytest.fixture(autouse=True)
def skip_integration_when_services_unavailable():
    """No-op override: classifier tests don't need external services."""
    return


@pytest.fixture(autouse=True)
def mock_redis():
    """No-op override: classifier doesn't use Redis."""
    return


@pytest.fixture(autouse=True)
def reset_rate_limit_state():
    """No-op override: classifier doesn't hit rate limits."""
    return


@pytest.fixture(autouse=True)
def reset_health_check_caches():
    """No-op override: classifier doesn't use health caches."""
    return
