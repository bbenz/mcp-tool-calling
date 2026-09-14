"""Telemetry wiring.

Correlated evidence is required on stage, but cloud ingestion can lag by
minutes. So the local structured audit log in :mod:`refund_demo.audit` is the
primary, immediate evidence surface, and OpenTelemetry/Application Insights is
the correlated cloud view that uses the same trace id.

Azure Monitor export is optional. If the connection string is absent, tracing
degrades to local-only and says so, rather than failing the service.
"""

from __future__ import annotations

import logging
import uuid
from contextlib import contextmanager
from typing import Any, Iterator

from .config import get_settings

logger = logging.getLogger("refund_demo")

_CONFIGURED = False
_AZURE_MONITOR_ACTIVE = False
_SERVICE_NAME = "unknown"


def service_name() -> str:
    """The name this process registered at configure() time."""
    return _SERVICE_NAME


def configure(service_name: str) -> bool:
    """Configure exporters once per process. Returns True if cloud export is on."""
    global _CONFIGURED, _AZURE_MONITOR_ACTIVE, _SERVICE_NAME
    if _CONFIGURED:
        return _AZURE_MONITOR_ACTIVE

    _CONFIGURED = True
    _SERVICE_NAME = service_name
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [" + service_name + "] %(message)s",
    )

    connection_string = get_settings().applicationinsights_connection_string
    if not connection_string:
        logger.info("telemetry: local only (no Application Insights connection string configured)")
        return False

    try:
        from azure.monitor.opentelemetry import configure_azure_monitor

        configure_azure_monitor(
            connection_string=connection_string,
            logger_name="refund_demo",
        )
        _AZURE_MONITOR_ACTIVE = True
        logger.info("telemetry: exporting to Application Insights")
    except Exception as exc:
        logger.warning("telemetry: Application Insights export unavailable (%s); continuing local only", exc)
    return _AZURE_MONITOR_ACTIVE


def new_trace_id() -> str:
    return uuid.uuid4().hex


def _tracer():
    try:
        from opentelemetry import trace

        return trace.get_tracer("refund_demo")
    except Exception:
        return None


@contextmanager
def span(name: str, **attributes: Any) -> Iterator[None]:
    """Start a span when OpenTelemetry is present; otherwise do nothing."""
    tracer = _tracer()
    if tracer is None:
        yield
        return
    with tracer.start_as_current_span(name) as current:
        for key, value in attributes.items():
            if value is not None:
                current.set_attribute(key, value)
        yield


def current_trace_id() -> str | None:
    try:
        from opentelemetry import trace

        context = trace.get_current_span().get_span_context()
        if context and context.trace_id:
            return format(context.trace_id, "032x")
    except Exception:
        pass
    return None
