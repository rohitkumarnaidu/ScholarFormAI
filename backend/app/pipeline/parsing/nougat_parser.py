# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""Compatibility stub for NougatParser (deprecated/removed)."""

from typing import Any


class NougatParser:
    """Stub class for backward compatibility with tests patching NougatParser."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        pass

    def parse(self, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedError("NougatParser is deprecated.")


NOUGAT_AVAILABLE = False
