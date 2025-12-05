"""Structured logging configuration for FluxoDeCaixa application.

Provides JSON-formatted logs for production debugging with:
- Request ID tracking
- Performance timing
- Contextual metadata
"""
from __future__ import annotations

import json
import logging
import os
import sys
import time
import uuid
from contextvars import ContextVar
from datetime import datetime
from functools import wraps
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

# Context variable for request tracking
request_id_var: ContextVar[str] = ContextVar('request_id', default='')
request_start_time_var: ContextVar[float] = ContextVar('request_start_time', default=0.0)


class StructuredLogFormatter(logging.Formatter):
    """JSON formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data: dict[str, Any] = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
        }

        # Add request context if available
        request_id = request_id_var.get()
        if request_id:
            log_data['request_id'] = request_id

        # Add source location
        log_data['source'] = {
            'file': record.filename,
            'line': record.lineno,
            'function': record.funcName,
        }

        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)

        # Add any extra fields passed to the log call
        extra_fields = ['user_id', 'operation', 'entity', 'entity_id', 
                        'duration_ms', 'status_code', 'path', 'method']
        for field in extra_fields:
            if hasattr(record, field):
                log_data[field] = getattr(record, field)

        return json.dumps(log_data, ensure_ascii=False, default=str)


class ConsoleFormatter(logging.Formatter):
    """Human-readable formatter for console output during development."""

    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[35m',  # Magenta
    }
    RESET = '\033[0m'

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with colors for console."""
        color = self.COLORS.get(record.levelname, '')
        reset = self.RESET if color else ''
        
        request_id = request_id_var.get()
        request_prefix = f'[{request_id[:8]}] ' if request_id else ''
        
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        message = f'{timestamp} {color}{record.levelname:8}{reset} {request_prefix}{record.name}: {record.getMessage()}'
        
        if record.exc_info:
            message += '\n' + self.formatException(record.exc_info)
            
        return message


def configure_logging(
    log_level: str = 'INFO',
    json_format: bool | None = None,
    log_file: str | None = None,
) -> None:
    """Configure application logging.

    Args:
        log_level: Minimum log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_format: Use JSON format (auto-detects production if None)
        log_file: Optional file path for log output
    """
    # Auto-detect production environment
    if json_format is None:
        json_format = os.getenv('ENVIRONMENT', '').lower() in ('production', 'prod')

    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Clear existing handlers
    root_logger.handlers.clear()

    # Create formatter based on environment
    if json_format:
        formatter = StructuredLogFormatter()
    else:
        formatter = ConsoleFormatter()

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # File handler (always JSON for easier parsing)
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(StructuredLogFormatter())
        root_logger.addHandler(file_handler)

    # Configure specific loggers
    # Reduce noise from libraries
    logging.getLogger('uvicorn.access').setLevel(logging.WARNING)
    logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the given name.
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)


def log_operation(
    operation: str,
    entity: str | None = None,
    entity_id: int | str | None = None,
) -> Callable:
    """Decorator to log function calls with timing.
    
    Args:
        operation: Name of the operation being performed
        entity: Type of entity being operated on
        entity_id: ID of the specific entity
        
    Example:
        @log_operation('create', 'Lancamento')
        def create_lancamento(data):
            ...
    """
    def decorator(func: Callable) -> Callable:
        logger = logging.getLogger(func.__module__)

        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.perf_counter()
            
            # Try to get entity_id from args/kwargs if not provided
            eid = entity_id
            if eid is None and 'ident' in kwargs:
                eid = kwargs['ident']
            elif eid is None and len(args) > 0 and isinstance(args[0], (int, str)):
                eid = args[0]

            extra = {
                'operation': operation,
                'entity': entity,
                'entity_id': eid,
            }
            
            logger.info(
                f"Starting {operation} on {entity or 'unknown'}" + (f" #{eid}" if eid else ""),
                extra=extra,
            )

            try:
                result = func(*args, **kwargs)
                duration_ms = (time.perf_counter() - start_time) * 1000
                extra['duration_ms'] = round(duration_ms, 2)
                
                logger.info(
                    f"Completed {operation} on {entity or 'unknown'}" + (f" #{eid}" if eid else "") + f" in {duration_ms:.2f}ms",
                    extra=extra,
                )
                return result
            except Exception as e:
                duration_ms = (time.perf_counter() - start_time) * 1000
                extra['duration_ms'] = round(duration_ms, 2)
                
                logger.error(
                    f"Failed {operation} on {entity or 'unknown'}" + (f" #{eid}" if eid else "") + f": {e}",
                    extra=extra,
                    exc_info=True,
                )
                raise

        return wrapper
    return decorator


def log_request_middleware(request, call_next):
    """Middleware to add request tracking to logs.
    
    Usage with FastAPI:
        @app.middleware("http")
        async def logging_middleware(request, call_next):
            return await log_request_middleware(request, call_next)
    """
    import asyncio

    async def _async_middleware():
        # Generate unique request ID
        req_id = str(uuid.uuid4())
        request_id_var.set(req_id)
        request_start_time_var.set(time.perf_counter())

        logger = logging.getLogger('fluxocaixa.web')
        
        # Log request start
        logger.info(
            f"Request started: {request.method} {request.url.path}",
            extra={
                'method': request.method,
                'path': str(request.url.path),
                'request_id': req_id,
            }
        )

        try:
            response = await call_next(request)
            
            # Calculate duration
            duration_ms = (time.perf_counter() - request_start_time_var.get()) * 1000
            
            # Log request completion
            logger.info(
                f"Request completed: {request.method} {request.url.path} -> {response.status_code}",
                extra={
                    'method': request.method,
                    'path': str(request.url.path),
                    'status_code': response.status_code,
                    'duration_ms': round(duration_ms, 2),
                    'request_id': req_id,
                }
            )
            
            # Add request ID to response headers
            response.headers['X-Request-ID'] = req_id
            
            return response
        except Exception as e:
            duration_ms = (time.perf_counter() - request_start_time_var.get()) * 1000
            
            logger.error(
                f"Request failed: {request.method} {request.url.path}",
                extra={
                    'method': request.method,
                    'path': str(request.url.path),
                    'duration_ms': round(duration_ms, 2),
                    'request_id': req_id,
                },
                exc_info=True,
            )
            raise

    return _async_middleware()


# Default logger for the application
logger = get_logger('fluxocaixa')
