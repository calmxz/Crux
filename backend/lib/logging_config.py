"""Production logging config (audit G-05).

PII rule: log identifiers (user_id, session_id, document_id, request_id)
freely; never log message content, document content, or chunk text.
"""

import logging
import logging.config

from config import settings


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        from lib.request_id import request_id_var

        record.request_id = request_id_var.get()
        return True


def configure_logging() -> None:
    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "filters": {"request_id": {"()": "lib.logging_config.RequestIdFilter"}},
            "formatters": {
                "default": {
                    "format": ("%(asctime)s %(levelname)s %(name)s [%(request_id)s] %(message)s"),
                }
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "default",
                    "filters": ["request_id"],
                    "stream": "ext://sys.stdout",
                }
            },
            "root": {"level": settings.log_level, "handlers": ["console"]},
            "loggers": {
                "uvicorn": {"level": "INFO", "propagate": True, "handlers": []},
                "uvicorn.access": {
                    "level": "INFO",
                    "propagate": True,
                    "handlers": [],
                },
                "uvicorn.error": {
                    "level": "INFO",
                    "propagate": True,
                    "handlers": [],
                },
            },
        }
    )
