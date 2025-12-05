import os
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles

from .config import Config
from .models import db
from .models.alerta import ensure_alerta_schema
from .services.seed import seed_data
from .utils.formatters import format_currency
from .utils.logging import configure_logging, log_request_middleware
from .web import router, templates


def create_app(config_class: type[Config] = Config) -> FastAPI:
    """Create and configure the FastAPI application."""
    # Configure structured logging first
    log_level = os.getenv('LOG_LEVEL', 'INFO')
    json_logs = os.getenv('JSON_LOGS', '').lower() in ('true', '1', 'yes')
    configure_logging(log_level=log_level, json_format=json_logs)

    static_folder = os.path.join(os.path.dirname(__file__), "static")

    app = FastAPI()

    # Add request logging middleware
    @app.middleware("http")
    async def logging_middleware(request: Request, call_next):
        return await log_request_middleware(request, call_next)

    # Ensure database tables exist and populate basic data
    db.create_all()
    ensure_alerta_schema()
    seed_data()

    # Register Jinja2 filters
    templates.env.filters["format_currency"] = format_currency

    # Include application routes
    app.include_router(router)

    # Mount static files
    app.mount("/static", StaticFiles(directory=static_folder), name="static")

    return app
