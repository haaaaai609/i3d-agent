"""
OpenTelemetry setup and utilities for i3d-agent-system.

This module provides OpenTelemetry initialization, auto-instrumentation
for FastAPI and HTTPX, and tracer retrieval.
"""

from typing import Optional

from i3d_agent.config.settings import get_settings

settings = get_settings()

# Telemetry state
_telemetry_initialized = False
_tracer_provider = None


def setup_telemetry(service_name: Optional[str] = None) -> bool:
    """
    Initialize OpenTelemetry tracing.

    Sets up the OTLP trace exporter and configures the tracer provider.
    Only initializes if settings.ENABLE_TRACING is True and not already initialized.

    Args:
        service_name: Optional service name (defaults to settings.SERVICE_NAME)

    Returns:
        True if telemetry was initialized, False if disabled or already initialized
    """
    global _telemetry_initialized, _tracer_provider

    if not settings.ENABLE_TRACING:
        return False

    if _telemetry_initialized:
        return True

    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
            OTLPSpanExporter,
        )
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        # Create resource with service name
        resource = Resource.create(
            {
                "service.name": service_name or settings.SERVICE_NAME,
                "service.version": settings.APP_VERSION,
                "deployment.environment": settings.ENVIRONMENT,
            }
        )

        # Configure tracer provider
        _tracer_provider = TracerProvider(resource=resource)

        # Add OTLP exporter
        otlp_endpoint = settings.OTEL_EXPORTER_OTLP_ENDPOINT
        otlp_exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)

        span_processor = BatchSpanProcessor(otlp_exporter)
        _tracer_provider.add_span_processor(span_processor)

        # Set global tracer provider
        trace.set_tracer_provider(_tracer_provider)

        _telemetry_initialized = True
        return True

    except ImportError:
        # OpenTelemetry packages not installed
        return False
    except Exception:
        # Initialization failed (e.g., connection error)
        return False


def instrument_fastapi(app: object) -> bool:
    """
    Auto-instrument FastAPI application with OpenTelemetry.

    Instruments routes, middleware, and HTTP requests.

    Args:
        app: FastAPI application instance

    Returns:
        True if instrumentation succeeded, False otherwise
    """
    if not settings.ENABLE_TRACING:
        return False

    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

        # Ensure telemetry is initialized
        setup_telemetry()

        FastAPIInstrumentor.instrument_app(app)
        return True

    except ImportError:
        return False
    except Exception:
        return False


def instrument_httpx() -> bool:
    """
    Auto-instrument HTTPX client with OpenTelemetry.

    Instruments outgoing HTTP requests made with HTTPX.

    Returns:
        True if instrumentation succeeded, False otherwise
    """
    if not settings.ENABLE_TRACING:
        return False

    try:
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

        # Ensure telemetry is initialized
        setup_telemetry()

        HTTPXClientInstrumentor().instrument()
        return True

    except ImportError:
        return False
    except Exception:
        return False


def get_tracer(name: Optional[str] = None) -> object:
    """
    Get a tracer instance for creating spans.

    Args:
        name: Optional tracer name (defaults to "i3d-agent-tracer")

    Returns:
        Tracer instance (returns None if telemetry not enabled/initialized)
    """
    if not settings.ENABLE_TRACING:
        return None

    # Initialize if not already done
    setup_telemetry()

    try:
        from opentelemetry import trace

        tracer_name = name or "i3d-agent-tracer"
        return trace.get_tracer(tracer_name)

    except Exception:
        return None
