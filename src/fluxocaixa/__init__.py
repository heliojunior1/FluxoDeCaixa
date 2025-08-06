import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .config import Config
from .models import db
from .models.alerta import ensure_alerta_schema
from .models.cenario import ensure_cenario_schema
from .services.seed import seed_data
from .utils.formatters import format_currency
from .web import router, templates


def create_app(config_class: type[Config] = Config) -> FastAPI:
    """Create and configure the FastAPI application."""
    static_folder = os.path.join(os.path.dirname(__file__), "static")

    app = FastAPI()

    # Ensure database tables exist and populate basic data
    db.create_all()
    ensure_alerta_schema()
    ensure_cenario_schema()
    seed_data()

    # Register Jinja2 filters
    templates.env.filters["format_currency"] = format_currency

    # Include application routes
    app.include_router(router)

    # Mount static files
    app.mount("/static", StaticFiles(directory=static_folder), name="static")

    return app
