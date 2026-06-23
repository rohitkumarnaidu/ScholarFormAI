# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from typing import Any, Optional
from threading import Lock

class ModelStore:
    """
    Thread-safe global registry for heavy AI models.
    Load once at startup, reuse across all requests.
    """
    _instance = None
    _lock = Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(ModelStore, cls).__new__(cls)
                cls._instance._models = {}
            return cls._instance

    def set_model(self, key: str, model: Any):
        """Register a pre-loaded model."""
        self._models[key] = model

    def get_model(self, key: str) -> Optional[Any]:
        """Retrieve a registered model."""
        return self._models.get(key)

    def is_loaded(self, key: str) -> bool:
        """Check if a model is registered."""
        return key in self._models

# Global singleton
model_store = ModelStore()
