"""Utilities for safer route registration with automatic exception handling."""
from __future__ import annotations

import inspect
import logging
from functools import wraps
from typing import TYPE_CHECKING

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse

if TYPE_CHECKING:
    from collections.abc import Callable

logger = logging.getLogger(__name__)


def _rollback_session() -> None:
    """Rollback the database session to recover from errors."""
    try:
        from ..models.base import db
        db.session.rollback()
    except Exception as e:
        logger.warning("Failed to rollback session: %s", e)


def _render_error_page(request: Request | None, status_code: int, message: str) -> HTMLResponse:
    """Render a user-friendly error page."""
    error_titles = {
        400: "Requisição Inválida",
        401: "Não Autorizado",
        403: "Acesso Proibido",
        404: "Página Não Encontrada",
        500: "Erro Interno do Servidor",
    }
    error_descriptions = {
        400: "Os dados enviados são inválidos ou estão incompletos.",
        401: "Você precisa fazer login para acessar esta página.",
        403: "Você não tem permissão para acessar este recurso.",
        404: "A página que você está procurando não existe ou foi movida.",
        500: "Ocorreu um erro inesperado. Nossa equipe foi notificada.",
    }
    
    title = error_titles.get(status_code, "Erro")
    description = error_descriptions.get(status_code, message)
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{title} - Fluxo de Caixa</title>
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{
                font-family: system-ui, -apple-system, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 1rem;
            }}
            .error-container {{
                background: white;
                border-radius: 1rem;
                padding: 3rem;
                max-width: 500px;
                text-align: center;
                box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
            }}
            .error-code {{
                font-size: 6rem;
                font-weight: 700;
                color: #667eea;
                line-height: 1;
                margin-bottom: 1rem;
            }}
            .error-title {{
                font-size: 1.5rem;
                color: #1f2937;
                margin-bottom: 1rem;
            }}
            .error-description {{
                color: #6b7280;
                margin-bottom: 2rem;
                line-height: 1.6;
            }}
            .back-button {{
                display: inline-block;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 0.75rem 2rem;
                border-radius: 0.5rem;
                text-decoration: none;
                font-weight: 500;
                transition: transform 0.2s, box-shadow 0.2s;
            }}
            .back-button:hover {{
                transform: translateY(-2px);
                box-shadow: 0 10px 20px -10px rgba(102, 126, 234, 0.5);
            }}
        </style>
    </head>
    <body>
        <div class="error-container">
            <div class="error-code">{status_code}</div>
            <h1 class="error-title">{title}</h1>
            <p class="error-description">{description}</p>
            <a href="/" class="back-button">Voltar ao Início</a>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content, status_code=status_code)


def handle_exceptions(func: Callable) -> Callable:
    """Wrap endpoint functions to provide basic exception handling with user-friendly error pages."""

    if inspect.iscoroutinefunction(func):

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except HTTPException:
                raise
            except Exception as exc:  # pragma: no cover - defensive
                logger.exception("Unhandled exception in endpoint: %s", exc)
                # Rollback session to recover from database errors
                _rollback_session()
                
                # Try to get request from args/kwargs for better error page
                request = None
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break
                if not request:
                    request = kwargs.get('request')
                
                # Return user-friendly error page
                return _render_error_page(request, 500, str(exc))

        return async_wrapper

    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except HTTPException:
            raise
        except Exception as exc:  # pragma: no cover - defensive
            logger.exception("Unhandled exception in endpoint: %s", exc)
            # Rollback session to recover from database errors
            _rollback_session()
            
            # Try to get request from args/kwargs for better error page
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            if not request:
                request = kwargs.get('request')
            
            # Return user-friendly error page
            return _render_error_page(request, 500, str(exc))

    return sync_wrapper


class SafeAPIRouter(APIRouter):
    """APIRouter that automatically wraps endpoints with exception handling."""

    def add_api_route(self, path: str, endpoint, **kwargs):  # type: ignore[override]
        endpoint = handle_exceptions(endpoint)
        return super().add_api_route(path, endpoint, **kwargs)
