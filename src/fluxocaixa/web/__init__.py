from fastapi import APIRouter
from fastapi.templating import Jinja2Templates
import os

from ..utils import format_currency

from ..config import BASE_DIR

# Shared router and templates object used by the route modules
router = APIRouter()
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, 'templates'))
templates.env.filters['format_currency'] = format_currency

# Import routes so they register themselves with the router
from . import base, pagamentos, mapeamentos, relatorios, alertas  # noqa: E402,F401

__all__ = ['router', 'templates']
