"""
Comprehensive logging configuration for Cookie Licking Detector.
Production-ready structured logging with multiple handlers and formatters.
"""

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Any, Dict, Optional

import structlog
from pythonjsonlogger import jsonlogger

from app.core.config import get_settings

settings = get_settings()

# Ensure logs directory exists
LOGS_DIR = Path("logs")
LOGS_DIR.mkdir(exist_ok=True)


class ContextualFilter(logging.Filter):
    """Add contextual information to log records."""
    
    def filter(self, record: logging.LogRecord) -> bool:
        # Add hostname and service info
        record.hostname = getattr(settings, 'HOSTNAME', 'unknown')
        record.service = 'cookie-licking-detector'
        record.environment = settings.ENVIRONMENT
        return True


class SensitiveDataFilter(logging.Filter):
    """Filter out sensitive data from logs."""
    
    SENSITIVE_KEYS = {
        'password', 'token', 'key', 'secret', 'auth', 'authorization',
        'api_key', 'github_token', 'sendgrid_api_key', 'jwt'
    }
    
    def filter(self, record: logging.LogRecord) -> bool:
        if hasattr(record, 'msg') and isinstance(record.msg, str):
            # Basic sensitive data masking
            for key in self.SENSITIVE_KEYS:
                if key in record.msg.lower():
                    record.msg = self._mask_sensitive_data(record.msg, key)
        return True
    
    def _mask_sensitive_data(self, message: str, key: str) -> str:
        """Mask sensitive data in log messages."""
        import re
        # Simple pattern to mask values after sensitive keys
        pattern = rf'({key}[\'"]?\s*[:=]\s*[\'"]?)([^\'"\s,}}]+)'
        return re.sub(pattern, r'\1****', message, flags=re.IGNORECASE)


def configure_structlog() -> None:
    """Configure structlog for structured logging."""
    
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="ISO"),
            structlog.processors.CallsiteParameterAdder(
                parameters={
                    structlog.processors.CallsiteParameter.FILENAME,
                    structlog.processors.CallsiteParameter.FUNC_NAME,
                    structlog.processors.CallsiteParameter.LINENO,
                }
            ),
            structlog.processors.dict_tracebacks,
            structlog.dev.ConsoleRenderer() if settings.ENVIRONMENT == "development" 
            else structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            min_level=logging.getLevelName(settings.LOG_LEVEL.upper())
        ),
        logger_factory=structlog.WriteLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_json_formatter() -> jsonlogger.JsonFormatter:
    """Get JSON formatter for structured logging."""
    
    format_string = ' '.join([
        '%(asctime)s',
        '%(name)s',
        '%(levelname)s',
        '%(hostname)s', 
        '%(service)s',
        '%(environment)s',
        '%(filename)s:%(lineno)d',
        '%(funcName)s',
        '%(message)s'
    ])
    
    return jsonlogger.JsonFormatter(
        format_string,
        timestamp=True,
        rename_fields={
            'asctime': '@timestamp',
            'levelname': 'level',
            'name': 'logger',
            'filename': 'file',
            'lineno': 'line',
            'funcName': 'function'
        }
    )


def setup_logging() -> None:
    """Set up comprehensive logging configuration."""
    
    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.getLevelName(settings.LOG_LEVEL.upper()))
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    if settings.LOG_FORMAT.lower() == 'json':
        console_handler.setFormatter(get_json_formatter())
    else:
        console_formatter = logging.Formatter(
            fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
    
    # Add filters
    console_handler.addFilter(ContextualFilter())
    console_handler.addFilter(SensitiveDataFilter())
    root_logger.addHandler(console_handler)
    
    # File handler for application logs
    app_file_handler = logging.handlers.RotatingFileHandler(
        LOGS_DIR / "app.log",
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=10
    )
    app_file_handler.setFormatter(get_json_formatter())
    app_file_handler.addFilter(ContextualFilter())
    app_file_handler.addFilter(SensitiveDataFilter())
    root_logger.addHandler(app_file_handler)
    
    # Error file handler
    error_file_handler = logging.handlers.RotatingFileHandler(
        LOGS_DIR / "errors.log",
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5
    )
    error_file_handler.setLevel(logging.ERROR)
    error_file_handler.setFormatter(get_json_formatter())
    error_file_handler.addFilter(ContextualFilter())
    error_file_handler.addFilter(SensitiveDataFilter())
    root_logger.addHandler(error_file_handler)
    
    # Celery logs
    celery_file_handler = logging.handlers.RotatingFileHandler(
        LOGS_DIR / "celery.log",
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5
    )
    celery_file_handler.setFormatter(get_json_formatter())
    celery_file_handler.addFilter(ContextualFilter())
    
    celery_logger = logging.getLogger('celery')
    celery_logger.addHandler(celery_file_handler)
    celery_logger.setLevel(logging.INFO)
    
    # Third-party loggers (reduce noise)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
    
    # Configure structlog
    if settings.STRUCTURED_LOGGING:
        configure_structlog()


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with proper configuration."""
    return logging.getLogger(name)


def get_structlog_logger(name: str) -> structlog.BoundLogger:
    """Get a structlog logger instance."""
    return structlog.get_logger(name)


class LoggerMixin:
    """Mixin to add logging capabilities to classes."""
    
    @property
    def logger(self) -> logging.Logger:
        """Get logger for this class."""
        return get_logger(f"{self.__class__.__module__}.{self.__class__.__name__}")
    
    @property
    def struct_logger(self) -> structlog.BoundLogger:
        """Get structlog logger for this class."""
        return get_structlog_logger(f"{self.__class__.__module__}.{self.__class__.__name__}")


# Performance logging utilities
class PerformanceTimer:
    """Context manager for performance timing."""
    
    def __init__(self, operation_name: str, logger: Optional[logging.Logger] = None):
        self.operation_name = operation_name
        self.logger = logger or get_logger(__name__)
        self.start_time = None
    
    def __enter__(self):
        import time
        self.start_time = time.perf_counter()
        self.logger.debug(f"Starting operation: {self.operation_name}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        import time
        end_time = time.perf_counter()
        duration = end_time - self.start_time
        
        if exc_type is not None:
            self.logger.error(
                f"Operation failed: {self.operation_name}",
                extra={
                    'operation': self.operation_name,
                    'duration_seconds': duration,
                    'error': str(exc_val)
                }
            )
        else:
            self.logger.info(
                f"Operation completed: {self.operation_name}",
                extra={
                    'operation': self.operation_name,
                    'duration_seconds': duration
                }
            )


def log_api_call(method: str, url: str, status_code: int, 
                response_time: float, request_id: Optional[str] = None) -> None:
    """Log API call details."""
    logger = get_logger('api_calls')
    
    log_data = {
        'method': method,
        'url': url,
        'status_code': status_code,
        'response_time_ms': response_time * 1000,
        'request_id': request_id
    }
    
    if status_code >= 500:
        logger.error("API call failed", extra=log_data)
    elif status_code >= 400:
        logger.warning("API call client error", extra=log_data)
    else:
        logger.info("API call successful", extra=log_data)


def log_database_query(query: str, params: Dict[str, Any], 
                      execution_time: float, row_count: Optional[int] = None) -> None:
    """Log database query performance."""
    logger = get_logger('database')
    
    # Sanitize query for logging (remove sensitive data)
    sanitized_query = query[:500] + "..." if len(query) > 500 else query
    
    log_data = {
        'query_preview': sanitized_query,
        'execution_time_ms': execution_time * 1000,
        'row_count': row_count,
        'param_count': len(params) if params else 0
    }
    
    if execution_time > 1.0:  # Log slow queries
        logger.warning("Slow database query detected", extra=log_data)
    else:
        logger.debug("Database query executed", extra=log_data)


def log_task_execution(task_name: str, task_id: str, execution_time: float, 
                      status: str, result: Optional[Dict[str, Any]] = None) -> None:
    """Log Celery task execution."""
    logger = get_logger('tasks')
    
    log_data = {
        'task_name': task_name,
        'task_id': task_id,
        'execution_time_ms': execution_time * 1000,
        'status': status,
        'result_preview': str(result)[:200] if result else None
    }
    
    if status == 'SUCCESS':
        logger.info("Task completed successfully", extra=log_data)
    elif status == 'FAILURE':
        logger.error("Task failed", extra=log_data)
    else:
        logger.info(f"Task status: {status}", extra=log_data)


# Initialize logging on module import
setup_logging()