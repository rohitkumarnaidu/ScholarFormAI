# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

import asyncio
import logging
import sys
import warnings
from pydantic import BaseModel
from typing import Callable, Any, Type, Optional
from app.utils.serialization import safe_model_dump

logger = logging.getLogger(__name__)

# --- Optional Guardrails Import ---
if sys.version_info >= (3, 14):
    HAS_GUARDRAILS = False
    logger.info("Guardrails AI disabled on Python >= 3.14. Falling back to native Pydantic validation.")
else:
    try:
        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore",
                message="The 'is_flag' and 'flag_value' parameters are not supported by Typer.*",
                category=DeprecationWarning,
            )
            from guardrails import Guard
        HAS_GUARDRAILS = True
        logger.info("Guardrails AI loaded for robust LLM validation.")
    except ImportError:
        HAS_GUARDRAILS = False
        logger.info("Guardrails AI unavailable. Falling back to native Pydantic validation (validator_guard.py).")

# Gracefully import the old wrapper as a fallback
try:
    from app.pipeline.safety.validator_guard import validate_output as fallback_validate_output
except ImportError:
    # Extreme fallback if not found
    def fallback_validate_output(schema: Any, error_return_value: Any = None):
        def decorator(func: Callable) -> Callable:
            def wrapper(*args, **kwargs) -> Any:
                try:
                    res = func(*args, **kwargs)
                    return res
                except Exception:
                    return error_return_value or {}

            return wrapper

        return decorator


def guard_llm_output(schema: Type[BaseModel], error_return_value: Optional[Any] = None) -> Callable:
    """
    Advanced LLM Output Validator.
    Uses Guardrails AI (guardrails-ai) if available to guarantee Pydantic schema compliance.
    If unavailable, structurally falls back to `validator_guard.validate_output` which relies on native Pydantic wrappers.
    """

    # 1. Fallback Mode: Guardrails not installed or schema is not a BaseModel
    if not HAS_GUARDRAILS or not (isinstance(schema, type) and issubclass(schema, BaseModel)):
        return fallback_validate_output(schema, error_return_value=error_return_value)

    # 2. Guardrails AI Mode:
    def decorator(func: Callable) -> Callable:
        # Create the Guard instance strictly bound to the expected Pydantic schema
        guard = Guard.for_pydantic(output_class=schema)

        def _parse_with_guardrails(raw_result_str: str):
            """
            Parse guardrails output while ensuring an event loop exists.
            Some environments (especially test runners/worker threads) do not
            have a current loop and Guardrails otherwise emits warning noise.
            """
            try:
                asyncio.get_running_loop()
                return guard.parse(raw_result_str)
            except RuntimeError:
                loop = asyncio.new_event_loop()
                try:
                    asyncio.set_event_loop(loop)
                    return guard.parse(raw_result_str)
                finally:
                    asyncio.set_event_loop(None)
                    loop.close()

        def wrapper(*args, **kwargs) -> Any:
            try:
                # Execute the original LLM calling function. Note: Often returns a JSON string or dict.
                raw_result = func(*args, **kwargs)

                # If the function already returned the Pydantic model natively
                if isinstance(raw_result, schema):
                    return safe_model_dump(raw_result)

                # Format to JSON string for Guardrails
                if isinstance(raw_result, dict):
                    import json

                    raw_result_str = json.dumps(raw_result)
                elif isinstance(raw_result, str):
                    raw_result_str = raw_result
                else:
                    return raw_result

                # Guardrails validation execution
                # .parse() raises an error or returns a ValidationOutcome
                validated_output = _parse_with_guardrails(raw_result_str)

                if validated_output and validated_output.validated_output:
                    val = validated_output.validated_output
                    if hasattr(val, "model_dump") or hasattr(val, "dict") or isinstance(val, dict):
                        return safe_model_dump(val)
                    return val

                # If Guardrails returned None (failed validation severely)
                logger.warning("[GUARDRAILS] Schema rejected JSON payload for %s", func.__name__)
                return error_return_value or {}

            except Exception as e:
                # Catch Guardrails specific parsing errors securely
                logger.warning("[GUARDRAILS] Exception in %s: %s", func.__name__, e)
                import traceback

                traceback.print_exc()
                # Provide graceful degradation via error_return_value instead of crashing pipeline
                return error_return_value or {}

        return wrapper

    return decorator
