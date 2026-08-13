# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

import os
import logging
from fastapi import FastAPI

try:
    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.instrumentation.celery import CeleryInstrumentor
    OTEL_INSTALLED = True
except ImportError:
    OTEL_INSTALLED = False

logger = logging.getLogger(__name__)

def init_telemetry(app: FastAPI | None = None, service_name: str = "scholarform-backend"):
    "\""Initialize OpenTelemetry tracing."\""
    if not OTEL_INSTALLED:
        logger.warning("OpenTelemetry packages not found. Tracing disabled.")
        return

    # Check if tracing is explicitly disabled
    if os.getenv("ENABLE_TRACING", "false").lower() != "true":
        logger.info("OpenTelemetry tracing is disabled via ENABLE_TRACING.")
        return

    endpoint = os.getenv("OTLP_ENDPOINT", "http://localhost:4318/v1/traces")
    
    resource = Resource.create(attributes={
        "service.name": service_name,
        "environment": os.getenv("ENVIRONMENT", "development")
    })
    
    provider = TracerProvider(resource=resource)
    processor = BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint))
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)
    
    if app:
        FastAPIInstrumentor.instrument_app(app)
        logger.info(f"OpenTelemetry FastAPI tracing initialized (endpoint: {endpoint})")
    
    # Try instrumenting Celery
    try:
        CeleryInstrumentor().instrument()
        logger.info("OpenTelemetry Celery tracing initialized.")
    except Exception as e:
        logger.warning(f"Failed to instrument Celery: {e}")

