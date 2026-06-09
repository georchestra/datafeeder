"""Optional Arize Phoenix tracing setup for LangChain.

If arize-phoenix-otel or openinference-instrumentation-langchain are not
installed, or if the Phoenix server is unreachable, this module is a no-op.
"""

import logging

from openinference.instrumentation.langchain import LangChainInstrumentor
from phoenix.otel import register as _phoenix_register

logger = logging.getLogger(__name__)


def setup_phoenix_tracing(
    endpoint: str = "http://localhost:6006/v1/traces",
    project_name: str = "datafeeder",
) -> None:
    """Instrument LangChain with Arize Phoenix OpenTelemetry tracing.

    Soft failure: logs a warning and returns silently if the required packages
    are missing or if the Phoenix server cannot be reached.

    Args:
        endpoint: URL of the Phoenix OTLP trace collector.
        project_name: Project name displayed in the Phoenix UI.
    """
    try:
        tracer_provider = _phoenix_register(
            project_name=project_name,
            endpoint=endpoint,
        )
        LangChainInstrumentor().instrument(tracer_provider=tracer_provider)
        logger.info(
            "Arize Phoenix tracing enabled — project=%s endpoint=%s",
            project_name,
            endpoint,
        )
    except Exception as e:
        logger.warning(
            "Failed to connect to Arize Phoenix at %s — tracing disabled: %s",
            endpoint,
            e,
        )
