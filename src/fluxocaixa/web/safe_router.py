"""Utilities for safer route registration with automatic exception handling."""

import inspect
import logging
from functools import wraps

from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)


def handle_exceptions(func):
    """Wrap endpoint functions to provide basic exception handling."""

    if inspect.iscoroutinefunction(func):

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except HTTPException:
                raise
            except Exception as exc:  # pragma: no cover - defensive
                logger.exception("Unhandled exception in endpoint: %s", exc)
                raise HTTPException(status_code=500, detail="Internal server error")

        return async_wrapper

    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except HTTPException:
            raise
        except Exception as exc:  # pragma: no cover - defensive
            logger.exception("Unhandled exception in endpoint: %s", exc)
            raise HTTPException(status_code=500, detail="Internal server error")

    return sync_wrapper


class SafeAPIRouter(APIRouter):
    """APIRouter that automatically wraps endpoints with exception handling."""

    def add_api_route(self, path: str, endpoint, **kwargs):  # type: ignore[override]
        endpoint = handle_exceptions(endpoint)
        return super().add_api_route(path, endpoint, **kwargs)
