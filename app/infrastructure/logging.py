import logging

import structlog


def configure_logging(environment: str) -> None:
    dev = environment == "dev"
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,  # request_id bound by the API middleware
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer() if dev else structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.DEBUG if dev else logging.INFO),
    )
