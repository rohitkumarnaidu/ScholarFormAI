# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations
import pytest


class TestModelStore:
    def _fresh_store(self):
        from app.services.model_store import ModelStore
        import threading
        s = object.__new__(ModelStore)
        s._models = {}
        ModelStore._instance = s
        return s

    def test_get_model_returns_none_for_missing(self):
        store = self._fresh_store()
        assert store.get_model("fresh_key") is None

    def test_set_and_get_model(self):
        store = self._fresh_store()
        store.set_model("foo", {"a": 1})
        assert store.get_model("foo") == {"a": 1}

    def test_overwrite_model(self):
        store = self._fresh_store()
        store.set_model("x", 1)
        store.set_model("x", 2)
        assert store.get_model("x") == 2

    def test_is_loaded(self):
        store = self._fresh_store()
        assert store.is_loaded("y") is False
        store.set_model("y", 100)
        assert store.is_loaded("y") is True
