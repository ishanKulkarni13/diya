import logging
import contextvars
from pythonjsonlogger import jsonlogger
from app.config.settings import settings

request_id_ctx: contextvars.ContextVar[str | None] = contextvars.ContextVar("request_id", default=None)
user_id_ctx: contextvars.ContextVar[str | None] = contextvars.ContextVar("user_id", default=None)

class ContextFilter(logging.Filter):
    def filter(self, record):
        record.request_id = request_id_ctx.get()
        record.user_id = user_id_ctx.get()
        return True

def setup_logging():
    logger = logging.getLogger()
    logger.setLevel(settings.observability.log_level)

    # Clear existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    handler = logging.StreamHandler()
    handler.addFilter(ContextFilter())

    if settings.observability.log_format == "json":
        formatter = jsonlogger.JsonFormatter(
            "%(asctime)s %(levelname)s %(name)s %(request_id)s %(user_id)s %(message)s"
        )
    else:
        formatter = logging.Formatter(
            "[%(asctime)s] %(levelname)s [%(name)s] [req:%(request_id)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)