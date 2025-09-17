"""
Professional Logging System for Le Maître Mot Backend
Supports DEV/PROD environments with structured logging and sensitive data protection
"""

import logging
import json
import time
import os
import sys
from datetime import datetime
from typing import Any, Dict, Optional, Union
from functools import wraps
import re
from logging.handlers import RotatingFileHandler

class SensitiveDataFilter:
    """Filter to remove sensitive data from logs"""
    
    # Patterns to redact sensitive information
    SENSITIVE_PATTERNS = {
        'email': r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
        'token': r'(token["\']?\s*[:=]\s*["\']?)([a-zA-Z0-9._-]{10,})',
        'key': r'((?:api_?key|secret|password)["\']?\s*[:=]\s*["\']?)([a-zA-Z0-9._-]{8,})',
        'stripe': r'(sk_[a-zA-Z0-9_]{20,}|pk_[a-zA-Z0-9_]{20,})',
        'session': r'(session["\']?\s*[:=]\s*["\']?)([a-zA-Z0-9._-]{20,})'
    }
    
    @classmethod
    def redact_sensitive_data(cls, text: str) -> str:
        """Redact sensitive information from log messages"""
        if not isinstance(text, str):
            text = str(text)
            
        # Redact email addresses (keep domain for debugging)
        text = re.sub(cls.SENSITIVE_PATTERNS['email'], 
                     lambda m: f"{m.group(1)[:3]}***@{m.group(1).split('@')[1]}", text)
        
        # Redact tokens and keys
        for pattern_name, pattern in cls.SENSITIVE_PATTERNS.items():
            if pattern_name != 'email':
                text = re.sub(pattern, r'\1***REDACTED***', text, flags=re.IGNORECASE)
        
        return text

class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging in production"""
    
    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'module': getattr(record, 'module_name', record.name),
            'function': getattr(record, 'func_name', ''),
            'message': record.getMessage(),
        }
        
        # Add custom fields
        for key, value in record.__dict__.items():
            if key.startswith('log_'):
                clean_key = key[4:]  # Remove 'log_' prefix
                log_entry[clean_key] = value
            elif key in ['doc_id', 'exercise_id', 'user_type', 'duration_ms', 'status', 'schema_type']:
                log_entry[key] = value
        
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        # Redact sensitive data
        json_str = json.dumps(log_entry, ensure_ascii=False)
        return SensitiveDataFilter.redact_sensitive_data(json_str)

class DevFormatter(logging.Formatter):
    """Detailed formatter for development environment"""
    
    def format(self, record: logging.LogRecord) -> str:
        # Get custom fields
        module_name = getattr(record, 'module_name', record.name)
        func_name = getattr(record, 'func_name', '')
        doc_id = getattr(record, 'doc_id', '')
        exercise_id = getattr(record, 'exercise_id', '')
        
        # Build context string
        context_parts = []
        if doc_id:
            context_parts.append(f"doc_id={doc_id}")
        if exercise_id:
            context_parts.append(f"ex_id={exercise_id}")
        
        context = " ".join(context_parts)
        context_str = f" {context}" if context else ""
        
        # Format: [LEVEL][module][function] context message
        formatted = f"[{record.levelname}][{module_name}][{func_name}]{context_str} {record.getMessage()}"
        
        # Add exception info if present
        if record.exc_info:
            formatted += f"\n{self.formatException(record.exc_info)}"
        
        return SensitiveDataFilter.redact_sensitive_data(formatted)

class AppLogger:
    """Main application logger with environment-specific configuration"""
    
    def __init__(self):
        self.app_env = os.getenv('APP_ENV', 'prod').lower()
        self.log_format = os.getenv('APP_LOG_FORMAT', 'text').lower()
        self.logger = self._setup_logger()
    
    def _setup_logger(self) -> logging.Logger:
        """Setup logger based on environment"""
        logger = logging.getLogger('lemaitremot')
        logger.handlers.clear()  # Clear existing handlers
        
        # Set level based on environment
        if self.app_env == 'dev':
            logger.setLevel(logging.DEBUG)
            formatter = DevFormatter()
        else:
            logger.setLevel(logging.INFO)
            if self.log_format == 'json':
                formatter = JSONFormatter()
            else:
                formatter = DevFormatter()  # Use dev format for text in prod too
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # File handler with rotation
        log_dir = "logs"
        os.makedirs(log_dir, exist_ok=True)

        file_handler = RotatingFileHandler(
            os.path.join(log_dir, "app.log"),
            maxBytes=10_000_000,  # 10 MB
            backupCount=5,
            encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        # Prevent propagation to avoid duplicate logs
        logger.propagate = False

        return logger
    
    def _create_log_record(self, level: str, message: str, **kwargs) -> None:
        """Create a log record with custom fields"""
        extra = {}
        
        # Handle exc_info separately (it's a special logging parameter)
        exc_info = kwargs.pop('exc_info', False)
        
        # Add custom fields
        for key, value in kwargs.items():
            if key in ['module_name', 'func_name', 'doc_id', 'exercise_id', 'user_type', 
                      'duration_ms', 'status', 'schema_type']:
                extra[key] = value
            else:
                extra[f'log_{key}'] = value
        
        # Log the message with exc_info as a parameter, not in extra
        getattr(self.logger, level.lower())(message, extra=extra, exc_info=exc_info)
    
    def debug(self, message: str, **kwargs):
        """Debug level logging"""
        self._create_log_record('DEBUG', message, **kwargs)
    
    def info(self, message: str, **kwargs):
        """Info level logging"""
        self._create_log_record('INFO', message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Warning level logging"""
        self._create_log_record('WARNING', message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """Error level logging"""
        self._create_log_record('ERROR', message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        """Critical level logging"""
        self._create_log_record('CRITICAL', message, **kwargs)

# Global logger instance
app_logger = AppLogger()

def get_logger(module_name: str = None) -> AppLogger:
    """Get logger instance for a specific module"""
    return app_logger

def log_execution_time(func_name: str = None):
    """Decorator to log function execution time"""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            func_name_final = func_name or func.__name__
            module_name = func.__module__.split('.')[-1] if func.__module__ else 'unknown'
            
            logger = get_logger()
            
            try:
                logger.debug(
                    f"Starting {func_name_final}",
                    module_name=module_name,
                    func_name=func_name_final
                )
                
                result = await func(*args, **kwargs)
                
                duration_ms = int((time.time() - start_time) * 1000)
                logger.info(
                    f"Completed {func_name_final} successfully",
                    module_name=module_name,
                    func_name=func_name_final,
                    duration_ms=duration_ms,
                    status="success"
                )
                
                return result
                
            except Exception as e:
                duration_ms = int((time.time() - start_time) * 1000)
                logger.error(
                    f"Failed {func_name_final}: {str(e)}",
                    module_name=module_name,
                    func_name=func_name_final,
                    duration_ms=duration_ms,
                    status="error",
                    exc_info=True
                )
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            func_name_final = func_name or func.__name__
            module_name = func.__module__.split('.')[-1] if func.__module__ else 'unknown'
            
            logger = get_logger()
            
            try:
                logger.debug(
                    f"Starting {func_name_final}",
                    module_name=module_name,
                    func_name=func_name_final
                )
                
                result = func(*args, **kwargs)
                
                duration_ms = int((time.time() - start_time) * 1000)
                logger.info(
                    f"Completed {func_name_final} successfully",
                    module_name=module_name,
                    func_name=func_name_final,
                    duration_ms=duration_ms,
                    status="success"
                )
                
                return result
                
            except Exception as e:
                duration_ms = int((time.time() - start_time) * 1000)
                logger.error(
                    f"Failed {func_name_final}: {str(e)}",
                    module_name=module_name,
                    func_name=func_name_final,
                    duration_ms=duration_ms,
                    status="error",
                    exc_info=True
                )
                raise
        
        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator

# Convenience functions for common logging patterns
def log_user_context(user_type: str, doc_id: str = None, **kwargs):
    """Log user context information"""
    logger = get_logger()
    context_info = {
        'user_type': user_type,
        'doc_id': doc_id,
        **kwargs
    }
    logger.info("User context established", **context_info)

def log_quota_check(user_type: str, current_count: int, limit: int, **kwargs):
    """Log quota checking"""
    logger = get_logger()
    status = "within_limit" if current_count < limit else "exceeded"
    logger.info(
        f"Quota check: {current_count}/{limit}",
        module_name="quota",
        func_name="check",
        user_type=user_type,
        current_count=current_count,
        limit=limit,
        status=status,
        **kwargs
    )

def log_schema_processing(schema_type: str, success: bool, doc_id: str = None, exercise_id: str = None, **kwargs):
    """Log schema processing results"""
    logger = get_logger()
    status = "success" if success else "failed"
    logger.info(
        f"Schema processing {status}: {schema_type}",
        module_name="schema",
        func_name="process",
        schema_type=schema_type,
        status=status,
        doc_id=doc_id,
        exercise_id=exercise_id,
        **kwargs
    )

def log_ai_generation(stage: str, success: bool, doc_id: str = None, **kwargs):
    """Log AI generation stages"""
    logger = get_logger()
    status = "success" if success else "failed"
    logger.info(
        f"AI generation {stage} {status}",
        module_name="ai_generation",
        func_name=stage,
        status=status,
        doc_id=doc_id,
        **kwargs
    )