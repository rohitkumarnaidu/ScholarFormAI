# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

import functools
import json
import logging
from typing import Callable, Any, Dict
from pydantic import BaseModel, ValidationError
from app.utils.serialization import safe_model_dump

logger = logging.getLogger(__name__)

def validate_output(
    schema: Any, # Pydantic Model or expected structure
    error_return_value: Any = None
):
    """
    Decorator to enforce strict output validation for Agent/AI functions.
    Prevents 'hallucinations' or malformed JSON from crashing downstream logic.
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            try:
                result = func(*args, **kwargs)
                
                # Check Pydantic validation
                if isinstance(schema, type) and issubclass(schema, BaseModel):
                    if isinstance(result, dict):
                        # Attempt to parse
                        try:
                            valid_obj = schema(**result)
                            return safe_model_dump(valid_obj)
                        except ValidationError as ve:
                            logger.warning("Validator Guard: Schema mismatch in %s: %s", func.__name__, ve)
                            # Attempt to repair or fall back
                            return error_return_value or {}
                    elif isinstance(result, schema):
                        return safe_model_dump(result)
                
                # Check specific keys if schema is a dict of types (simple mode)
                if isinstance(schema, dict) and isinstance(result, dict):
                    missing = [k for k in schema.keys() if k not in result]
                    if missing:
                        logger.warning("Validator Guard: Missing keys in %s: %s", func.__name__, missing)
                        return error_return_value or {}
                
                return result
            except Exception as e:
                logger.warning("Validator Guard: Exception in %s: %s", func.__name__, e)
                return error_return_value or {}
        return wrapper
    return decorator
